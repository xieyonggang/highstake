import React, { useState, useEffect, useRef, useCallback } from 'react';
import { AGENTS, INTERACTION_MODES, SAMPLE_QUESTIONS } from '../utils/constants';
import AgentTile from './AgentTile';
import PresenterTile from './PresenterTile';
import SlideViewer from './SlideViewer';
import ChatMessage from './ChatMessage';

export default function MeetingPhase({ config, onEnd }) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [messages, setMessages] = useState([]);
  const [activeSpeaker, setActiveSpeaker] = useState(null);
  const [handsRaised, setHandsRaised] = useState([]);
  const [transcript, setTranscript] = useState([]);
  const [started, setStarted] = useState(false);
  const chatRef = useRef(null);
  const timerRef = useRef(null);

  const totalSlides = 6;

  const addMessage = useCallback((agentId, text) => {
    const agent = AGENTS.find((a) => a.id === agentId);
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages((prev) => [...prev, { agent, text, time }]);
    setActiveSpeaker(agentId);
    setTranscript((prev) => [...prev, { speaker: agent.name, role: agent.role, text, time }]);
    setTimeout(() => setActiveSpeaker(null), 3000);
  }, []);

  const startSession = () => {
    setStarted(true);
    setIsRecording(true);
    timerRef.current = setInterval(() => setElapsedTime((t) => t + 1), 1000);

    setTimeout(() => {
      addMessage(
        'moderator',
        "Good morning everyone. We're here today for a strategic presentation. Presenter, the floor is yours. We'll hold questions per the agreed format. Please begin when ready."
      );
    }, 1500);
  };

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Simulate agent questions when slides advance
  useEffect(() => {
    if (!started || currentSlide === 0) return;

    const agentPool = ['skeptic', 'analyst', 'contrarian'];
    const delay = config.interaction === 'interrupt' ? 2000 : 4000;

    const timeout1 = setTimeout(() => {
      if (config.interaction === 'hand-raise') {
        const raisedAgent = agentPool[Math.floor(Math.random() * agentPool.length)];
        setHandsRaised([raisedAgent]);
        addMessage(
          'moderator',
          `I see ${AGENTS.find((a) => a.id === raisedAgent).name} has a question. Go ahead.`
        );
        setTimeout(() => {
          const qs = SAMPLE_QUESTIONS[raisedAgent];
          addMessage(raisedAgent, qs[currentSlide % qs.length]);
          setHandsRaised([]);
        }, 2000);
      } else {
        const agent = agentPool[currentSlide % agentPool.length];
        const qs = SAMPLE_QUESTIONS[agent];
        if (config.interaction === 'section') {
          addMessage('moderator', "Let's pause for questions on this section.");
          setTimeout(() => addMessage(agent, qs[currentSlide % qs.length]), 2000);
        } else {
          addMessage(agent, qs[currentSlide % qs.length]);
        }
      }
    }, delay);

    const timeout2 = setTimeout(() => {
      const secondAgent = agentPool[(currentSlide + 1) % agentPool.length];
      const qs = SAMPLE_QUESTIONS[secondAgent];
      addMessage(secondAgent, qs[(currentSlide + 1) % qs.length]);
    }, delay + 6000);

    return () => {
      clearTimeout(timeout1);
      clearTimeout(timeout2);
    };
  }, [currentSlide, started, config.interaction, addMessage]);

  const formatTime = (s) =>
    `${Math.floor(s / 60)
      .toString()
      .padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;

  const endSession = () => {
    clearInterval(timerRef.current);
    setIsRecording(false);
    onEnd({ transcript, messages, duration: elapsedTime, slideCount: totalSlides });
  };

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
            {AGENTS.map((agent) => (
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
      {/* Top Bar */}
      <div className="bg-gray-900/80 backdrop-blur border-b border-gray-800 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-red-400 text-xs font-bold tracking-wider">LIVE SESSION</span>
          </div>
          <span className="text-gray-500 text-xs">|</span>
          <span className="text-gray-300 text-sm font-mono">{formatTime(elapsedTime)}</span>
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
        {/* Left: Video Grid + Slides */}
        <div className="flex-1 p-4 flex flex-col gap-4 overflow-y-auto">
          <div className="grid grid-cols-3 gap-3">
            <PresenterTile isRecording={isRecording} isMuted={isMuted} />
            {AGENTS.slice(0, 2).map((agent) => (
              <AgentTile
                key={agent.id}
                agent={agent}
                isActive={activeSpeaker === agent.id}
                isSpeaking={activeSpeaker === agent.id}
                hasHandRaised={handsRaised.includes(agent.id)}
              />
            ))}
          </div>
          <div className="grid grid-cols-3 gap-3">
            {AGENTS.slice(2).map((agent) => (
              <AgentTile
                key={agent.id}
                agent={agent}
                isActive={activeSpeaker === agent.id}
                isSpeaking={activeSpeaker === agent.id}
                hasHandRaised={handsRaised.includes(agent.id)}
              />
            ))}
            <div className="col-span-1 flex items-center justify-center gap-3">
              <button
                onClick={() => setIsMuted(!isMuted)}
                className={`w-12 h-12 rounded-full flex items-center justify-center text-lg transition-all ${
                  isMuted
                    ? 'bg-red-600 text-white'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
              >
                {isMuted ? '🔇' : '🎤'}
              </button>
              <button className="w-12 h-12 rounded-full bg-gray-800 text-gray-300 hover:bg-gray-700 flex items-center justify-center text-lg transition-all">
                📹
              </button>
              <button className="w-12 h-12 rounded-full bg-gray-800 text-gray-300 hover:bg-gray-700 flex items-center justify-center text-lg transition-all">
                🖥
              </button>
            </div>
          </div>

          <SlideViewer
            currentSlide={currentSlide}
            totalSlides={totalSlides}
            onNext={() => setCurrentSlide((s) => Math.min(totalSlides - 1, s + 1))}
            onPrev={() => setCurrentSlide((s) => Math.max(0, s - 1))}
          />
        </div>

        {/* Right: Chat Panel */}
        <div className="w-96 bg-gray-900/50 border-l border-gray-800 flex flex-col flex-shrink-0">
          <div className="px-4 py-3 border-b border-gray-800">
            <div className="text-white font-semibold text-sm">Meeting Chat</div>
            <div className="text-gray-500 text-xs">{messages.length} messages</div>
          </div>
          <div ref={chatRef} className="flex-1 overflow-y-auto py-2 space-y-1">
            {messages.length === 0 ? (
              <div className="text-gray-600 text-sm text-center py-8">
                Waiting for session to begin...
              </div>
            ) : (
              messages.map((msg, i) => (
                <ChatMessage key={i} agent={msg.agent} message={msg.text} timestamp={msg.time} />
              ))
            )}
          </div>
          <div className="p-3 border-t border-gray-800">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Type a response..."
                className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
              <button className="px-4 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-500 transition-colors">
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
