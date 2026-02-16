import React, { useState, useEffect, useRef, useCallback } from 'react';
import { AGENTS, INTERACTION_MODES, DEMO_SLIDES } from '../utils/constants';
import { useSessionStore } from '../stores/sessionStore';
import { useMeetingStore } from '../stores/meetingStore';
import { connectSocket, disconnectSocket } from '../services/socket';
import { AudioCaptureService } from '../services/audioCapture';
import { VideoCaptureService } from '../services/videoCapture';
import { TTSPlaybackService } from '../services/ttsPlayback';
import { uploadRecording, updateSession } from '../services/api';
import AgentTile from './AgentTile';
import PresenterTile from './PresenterTile';
import SlideViewer from './SlideViewer';
import ChatMessage from './ChatMessage';

export default function MeetingPhase() {
  const { sessionId, config, deckManifest, setPhase } = useSessionStore();
  const {
    currentSlide, messages, activeSpeaker, handsRaised,
    elapsedTime, isRecording, isMuted, isCameraOn,
    setCurrentSlide, addMessage, setActiveSpeaker, clearActiveSpeaker,
    addHandRaised, removeHandRaised, setElapsedTime, incrementTime,
    setIsRecording, setIsMuted, setIsCameraOn, reset: resetMeeting,
  } = useMeetingStore();

  const [started, setStarted] = useState(false);
  const [showStartModal, setShowStartModal] = useState(false);
  const [videoStream, setVideoStream] = useState(null);
  const [chatInput, setChatInput] = useState('');
  const [sidebarTab, setSidebarTab] = useState('participants');
  const [captionsOn, setCaptionsOn] = useState(true);
  const [captionText, setCaptionText] = useState('');
  const captionTimerRef = useRef(null);
  const chatRef = useRef(null);
  const timerRef = useRef(null);
  const socketRef = useRef(null);
  const audioRef = useRef(null);
  const videoRef = useRef(null);
  const ttsRef = useRef(null);

  const slides = deckManifest?.slides || DEMO_SLIDES;
  const totalSlides = slides.length;
  const deckId = deckManifest?.id;
  const selectedAgents = AGENTS.filter(
    (a) => a.id === 'moderator' || config.agents?.includes(a.id)
  );

  // Auto-scroll chat
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (captionTimerRef.current) clearTimeout(captionTimerRef.current);
      audioRef.current?.stop();
      videoRef.current?.stopCamera();
      ttsRef.current?.stop();
      disconnectSocket();
    };
  }, []);

  const findAgent = useCallback((agentId) => {
    return AGENTS.find((a) => a.id === agentId) || AGENTS[0];
  }, []);

  const showCaption = useCallback((text, durationMs = 0) => {
    if (captionTimerRef.current) clearTimeout(captionTimerRef.current);
    setCaptionText(text);
    if (durationMs > 0) {
      captionTimerRef.current = setTimeout(() => setCaptionText(''), durationMs);
    }
  }, []);

  const startSession = async () => {
    setStarted(true);
    setShowStartModal(true);
    setIsRecording(true);

    // Start timer
    timerRef.current = setInterval(() => incrementTime(), 1000);

    // Initialize TTS playback
    ttsRef.current = new TTSPlaybackService();

    // Start webcam
    try {
      videoRef.current = new VideoCaptureService();
      const stream = await videoRef.current.startCamera();
      setVideoStream(stream);
      videoRef.current.startRecording();
    } catch (err) {
      console.warn('Webcam not available:', err.message);
    }

    // Connect Socket.IO
    const socket = connectSocket(sessionId);
    socketRef.current = socket;

    // Start audio capture
    try {
      audioRef.current = new AudioCaptureService(socket);
      await audioRef.current.start();
    } catch (err) {
      console.warn('Microphone not available:', err.message);
    }

    // Socket event listeners
    socket.on('transcript_segment', (segment) => {
      showCaption(segment.text || '', segment.is_final ? 5000 : 0);
    });

    socket.on('agent_question', (data) => {
      const agent = findAgent(data.agentId);
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      addMessage({ agent, text: data.text, time, audioUrl: data.audioUrl });
      removeHandRaised(data.agentId);
      showCaption(`${agent.name}: ${data.text}`, 10000);

      // Play TTS if available
      if (data.audioUrl && ttsRef.current) {
        ttsRef.current.enqueue(
          data.agentId,
          data.audioUrl,
          (id) => setActiveSpeaker(id),
          () => { clearActiveSpeaker(); setCaptionText(''); },
        );
      } else {
        setActiveSpeaker(data.agentId);
        setTimeout(() => clearActiveSpeaker(), 3000);
      }
    });

    socket.on('moderator_message', (data) => {
      const agent = findAgent('moderator');
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      addMessage({ agent, text: data.text, time, audioUrl: data.audioUrl });
      showCaption(`Diana Chen: ${data.text}`, 10000);

      if (data.audioUrl && ttsRef.current) {
        ttsRef.current.enqueue(
          'moderator',
          data.audioUrl,
          (id) => setActiveSpeaker(id),
          () => { clearActiveSpeaker(); setCaptionText(''); setShowStartModal(false); },
        );
      } else {
        setActiveSpeaker('moderator');
        setTimeout(() => {
          clearActiveSpeaker();
          setShowStartModal(false);
        }, 3000);
      }
    });

    socket.on('agent_hand_raise', (data) => {
      addHandRaised(data.agentId);
    });

    socket.on('session_state', (data) => {
      // Could update UI state (presenting, q_and_a, ending)
    });

    // Note: STT runs in browser via Web Speech API — no server-side STT errors

    socket.on('session_ended', async (data) => {
      await handleSessionEnded(data);
    });

    // Tell backend to initialize agent engine and send moderator greeting with TTS
    socket.emit('start_session', {});

    // Update session status on backend
    try {
      await updateSession(sessionId, {
        status: 'presenting',
        started_at: new Date().toISOString(),
      });
    } catch (err) {
      console.warn('Failed to update session status:', err.message);
    }
  };

  const handleSlideChange = (newSlide) => {
    setCurrentSlide(newSlide);
    socketRef.current?.emit('slide_change', { slideIndex: newSlide });
  };

  const handleSendChat = () => {
    if (!chatInput.trim()) return;
    socketRef.current?.emit('presenter_response', { text: chatInput.trim() });
    setChatInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendChat();
    }
  };

  const handleMuteToggle = () => {
    const newMuted = !isMuted;
    setIsMuted(newMuted);
    if (newMuted) {
      audioRef.current?.mute();
    } else {
      audioRef.current?.unmute();
    }
  };

  const handleCameraToggle = () => {
    const newState = !isCameraOn;
    setIsCameraOn(newState);
    videoRef.current?.toggleCamera(newState);
  };

  const endSession = async () => {
    clearInterval(timerRef.current);
    setIsRecording(false);
    ttsRef.current?.stop();

    // Notify server
    socketRef.current?.emit('end_session', {});

    // Update session
    try {
      await updateSession(sessionId, {
        status: 'ending',
        ended_at: new Date().toISOString(),
        duration_secs: elapsedTime,
      });
    } catch (err) {
      console.warn('Failed to update session:', err.message);
    }

    // Upload recording
    if (videoRef.current) {
      try {
        const blob = await videoRef.current.stopRecording();
        if (blob && sessionId) {
          await uploadRecording(sessionId, blob);
        }
      } catch (err) {
        console.warn('Failed to upload recording:', err.message);
      }
    }

    // Cleanup
    audioRef.current?.stop();
    videoRef.current?.stopCamera();
    disconnectSocket();

    setPhase('review');
  };

  const handleSessionEnded = async (data) => {
    // Server-initiated session end
    clearInterval(timerRef.current);
    setIsRecording(false);
    ttsRef.current?.stop();
    audioRef.current?.stop();

    if (videoRef.current) {
      try {
        const blob = await videoRef.current.stopRecording();
        if (blob && sessionId) {
          await uploadRecording(sessionId, blob);
        }
      } catch (err) {
        console.warn('Failed to upload recording:', err.message);
      }
      videoRef.current.stopCamera();
    }

    disconnectSocket();
    setPhase('review');
  };

  const formatTime = (s) =>
    `${Math.floor(s / 60)
      .toString()
      .padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;

  // Pre-session ready screen
  if (!started) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="mb-8">
            <div className="w-24 h-24 mx-auto rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center mb-6">
              <span className="text-4xl">🎙</span>
            </div>
            <h2 className="text-3xl font-black text-white mb-2 font-display">Ready to Present</h2>
            <p className="text-gray-400 max-w-md mx-auto">
              Your panel is assembled. The Moderator will open the session. Mode:{' '}
              <span className="text-indigo-400 font-medium">
                {INTERACTION_MODES.find((m) => m.id === config.interaction)?.label}
              </span>{' '}
              · Intensity:{' '}
              <span className="text-indigo-400 font-medium">
                {config.intensity.charAt(0).toUpperCase() + config.intensity.slice(1)}
              </span>
            </p>
          </div>
          <div className="flex gap-4 justify-center mb-10">
            {selectedAgents.map((agent) => (
              <div key={agent.id} className="text-center">
                <div
                  className="w-14 h-14 rounded-full flex items-center justify-center text-white font-bold mx-auto mb-2"
                  style={{ background: agent.color }}
                >
                  {agent.avatar}
                </div>
                <div className="text-gray-400 text-xs">{agent.name}</div>
                <div className="text-xs font-medium" style={{ color: agent.color }}>
                  {agent.role}
                </div>
              </div>
            ))}
          </div>
          <button
            onClick={startSession}
            className="px-8 py-4 rounded-2xl text-lg font-bold bg-gradient-to-r from-indigo-600 to-violet-600 text-white hover:from-indigo-500 hover:to-violet-500 transition-all shadow-2xl shadow-indigo-500/30"
          >
            Begin Session
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-950 flex flex-col overflow-hidden">
      {/* Session Starting Modal */}
      {showStartModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl px-10 py-8 text-center shadow-2xl max-w-sm">
            <div className="w-16 h-16 mx-auto mb-5 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center animate-pulse">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Session Starting...</h3>
            <p className="text-gray-400 text-sm">The moderator is introducing the session.</p>
          </div>
        </div>
      )}

      {/* Top Bar */}
      <div className="bg-gray-900/80 backdrop-blur border-b border-gray-800 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-red-400 text-xs font-bold tracking-wider">LIVE SESSION</span>
          </div>
          <span className="text-gray-500 text-xs">|</span>
          <span className="text-gray-300 text-sm font-mono">{formatTime(elapsedTime)}</span>
          <span className="text-gray-500 text-xs">|</span>
          <button
            onClick={() => setCaptionsOn((v) => !v)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
              captionsOn
                ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/40'
                : 'bg-gray-800 text-gray-500 hover:text-gray-300 border border-gray-700'
            }`}
          >
            CC
          </button>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-gray-500 text-xs">
            {INTERACTION_MODES.find((m) => m.id === config.interaction)?.icon}{' '}
            {INTERACTION_MODES.find((m) => m.id === config.interaction)?.label}
          </span>
          <button
            onClick={endSession}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-red-600 text-white hover:bg-red-500 transition-colors"
          >
            End Session
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Presentation Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Slide Display */}
          <div className="flex-1 p-4 overflow-y-auto">
            <SlideViewer
              currentSlide={currentSlide}
              totalSlides={totalSlides}
              onNext={() => handleSlideChange(Math.min(totalSlides - 1, currentSlide + 1))}
              onPrev={() => handleSlideChange(Math.max(0, currentSlide - 1))}
              slides={slides}
              deckId={deckId}
              captionText={captionsOn ? captionText : ''}
            />
          </div>
          {/* Bottom Controls */}
          <div className="flex-shrink-0 px-4 py-3 border-t border-gray-800 bg-gray-900/50 flex items-center justify-center gap-3">
            <button
              onClick={handleMuteToggle}
              className={`w-10 h-10 rounded-full flex items-center justify-center text-base transition-all ${
                isMuted
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {isMuted ? '🔇' : '🎤'}
            </button>
            <button
              onClick={handleCameraToggle}
              className={`w-10 h-10 rounded-full flex items-center justify-center text-base transition-all ${
                !isCameraOn
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              📹
            </button>
          </div>
        </div>

        {/* Right: Tabbed Sidebar */}
        <div className="w-72 bg-gray-900/50 border-l border-gray-800 flex flex-col flex-shrink-0">
          {/* Tab Row */}
          <div className="flex border-b border-gray-800 flex-shrink-0">
            <button
              onClick={() => setSidebarTab('participants')}
              className={`flex-1 px-3 py-3 text-xs font-semibold transition-colors ${
                sidebarTab === 'participants'
                  ? 'text-white border-b-2 border-indigo-500'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              Participants
            </button>
            <button
              onClick={() => setSidebarTab('chat')}
              className={`flex-1 px-3 py-3 text-xs font-semibold transition-colors relative ${
                sidebarTab === 'chat'
                  ? 'text-white border-b-2 border-indigo-500'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              Chat
              {messages.length > 0 && sidebarTab !== 'chat' && (
                <span className="absolute top-2 right-3 w-4 h-4 rounded-full bg-indigo-500 text-white text-[10px] flex items-center justify-center">
                  {messages.length > 9 ? '9+' : messages.length}
                </span>
              )}
            </button>
          </div>

          {/* Tab Content */}
          {sidebarTab === 'participants' ? (
            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              {/* Presenter Tile */}
              <PresenterTile isRecording={isRecording} isMuted={isMuted} videoStream={videoStream} />
              {/* Agent Tiles */}
              {selectedAgents.map((agent) => (
                <AgentTile
                  key={agent.id}
                  agent={agent}
                  isActive={activeSpeaker === agent.id}
                  isSpeaking={activeSpeaker === agent.id}
                  hasHandRaised={handsRaised.includes(agent.id)}
                  compact
                />
              ))}
            </div>
          ) : (
            <>
              <div ref={chatRef} className="flex-1 overflow-y-auto py-2 space-y-1">
                {messages.length === 0 ? (
                  <div className="text-gray-600 text-sm text-center py-8">
                    Waiting for session to begin...
                  </div>
                ) : (
                  messages.map((msg, i) => (
                    <ChatMessage
                      key={i}
                      agent={msg.agent}
                      message={msg.text}
                      timestamp={msg.time}
                      audioUrl={msg.audioUrl}
                    />
                  ))
                )}
              </div>
              <div className="p-3 border-t border-gray-800 flex-shrink-0">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type a response..."
                    className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                  <button
                    onClick={handleSendChat}
                    className="px-3 py-2 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-500 transition-colors"
                  >
                    Send
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
