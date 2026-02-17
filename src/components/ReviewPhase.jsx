import React, { useState, useEffect } from 'react';
import { AGENTS } from '../utils/constants';
import { useSessionStore } from '../stores/sessionStore';
import { useMeetingStore } from '../stores/meetingStore';
import { getDebrief, getTranscript, getRecordingUrl } from '../services/api';

export default function ReviewPhase() {
  const { sessionId, reset: resetSession } = useSessionStore();
  const { elapsedTime, messages, currentSlide, reset: resetMeeting } = useMeetingStore();

  const [activeTab, setActiveTab] = useState('summary');
  const [debrief, setDebrief] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!sessionId) return;

    let cancelled = false;

    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        const [debriefData, transcriptData] = await Promise.all([
          getDebrief(sessionId),
          getTranscript(sessionId),
        ]);

        if (cancelled) return;

        setDebrief(debriefData);
        setTranscript(transcriptData);
      } catch (err) {
        if (cancelled) return;
        setError(err.message || 'Failed to load debrief data.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const handleRestart = () => {
    resetMeeting();
    resetSession();
  };

  const handleDownloadRecording = async () => {
    try {
      const data = await getRecordingUrl(sessionId);
      if (data?.url) {
        window.open(data.url, '_blank');
      }
    } catch {
      // Recording may not be available
    }
  };

  const handleExportReport = async () => {
    if (!debrief) return;
    const blob = new Blob([JSON.stringify(debrief, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `highstake-debrief-${sessionId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const scores = debrief?.scores;
  const strengths = debrief?.strengths || [];
  const coachingItems = debrief?.coaching_items || [];
  const moderatorSummary = debrief?.moderator_summary;

  const questionCount = messages.filter((m) => m.agent?.id !== 'moderator').length;

  const tabs = [
    { id: 'summary', label: 'Summary' },
    { id: 'transcript', label: 'Transcript' },
    { id: 'scores', label: 'Scores' },
    { id: 'advice', label: 'Coaching' },
  ];

  const scoreEntries = scores
    ? [
        ['clarity', scores.clarity],
        ['confidence', scores.confidence],
        ['data support', scores.data_support],
        ['handling', scores.handling],
        ['structure', scores.structure],
      ]
    : [];

  const allScoreEntries = scores
    ? [
        ['overall', scores.overall],
        ...scoreEntries,
      ]
    : [];

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-sky-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-blue-100 flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2 font-display">Generating Your Debrief</h2>
          <p className="text-gray-500 text-sm max-w-md">
            The moderator is reviewing your performance and preparing personalized coaching feedback...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-sky-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-lg mb-4">Failed to load debrief</div>
          <p className="text-gray-500 text-sm mb-6">{error}</p>
          <button
            onClick={handleRestart}
            className="px-6 py-3 rounded-xl text-sm font-semibold bg-blue-500 text-white hover:bg-blue-600 transition-all"
          >
            Start Over
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-sky-50 p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-100 border border-emerald-200 mb-4">
            <span className="text-emerald-600 text-xs font-semibold tracking-wider">
              SESSION COMPLETE
            </span>
          </div>
          <h1 className="text-4xl font-black text-gray-900 mb-2 font-display">Post-Session Debrief</h1>
          <p className="text-gray-500">
            Duration: {Math.floor(elapsedTime / 60)}m {elapsedTime % 60}s · Slides:{' '}
            {currentSlide + 1} · Questions: {questionCount}
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-blue-50/80 p-1 rounded-xl mb-8 max-w-md mx-auto border border-blue-100">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-blue-500 text-white shadow-md'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Summary Tab */}
        {activeTab === 'summary' && (
          <div className="grid grid-cols-2 gap-6">
            <div className="bg-white border border-blue-200/60 rounded-2xl p-8 text-center shadow-sm">
              <div className="text-6xl font-black text-gray-900 mb-2 font-display">
                {scores?.overall ?? '--'}
                <span className="text-2xl text-gray-400">/100</span>
              </div>
              <div className="text-gray-500 text-sm mb-6">Overall Presentation Score</div>
              <div className="space-y-3">
                {scoreEntries.map(([key, val]) => (
                  <div key={key} className="flex items-center gap-3">
                    <span className="text-gray-500 text-xs w-24 text-right capitalize">{key}</span>
                    <div className="flex-1 h-2 bg-blue-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-1000"
                        style={{
                          width: `${val}%`,
                          background:
                            val >= 80 ? '#10b981' : val >= 70 ? '#f59e0b' : '#ef4444',
                        }}
                      />
                    </div>
                    <span className="text-gray-700 text-xs font-mono w-8">{val}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white border border-blue-200/60 rounded-2xl p-6 shadow-sm">
              <h3 className="text-emerald-600 font-semibold text-sm mb-4">Strengths</h3>
              <div className="space-y-3">
                {strengths.length > 0 ? (
                  strengths.map((s, i) => (
                    <div key={i} className="flex gap-3">
                      <span className="text-emerald-500 mt-0.5">✓</span>
                      <span className="text-gray-600 text-sm leading-relaxed">{s}</span>
                    </div>
                  ))
                ) : (
                  <div className="text-gray-400 text-sm">No strengths data available.</div>
                )}
              </div>
            </div>

            <div className="col-span-2 bg-white border border-blue-200/60 rounded-2xl p-6 shadow-sm">
              <div className="flex gap-4">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold flex-shrink-0"
                  style={{ background: AGENTS[0].color }}
                >
                  {AGENTS[0].avatar}
                </div>
                <div>
                  <div className="text-blue-600 text-xs font-semibold mb-1">
                    {AGENTS[0].name} · Moderator's Summary
                  </div>
                  <p className="text-gray-600 text-sm leading-relaxed">
                    {moderatorSummary || 'Moderator summary is being generated...'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Transcript Tab */}
        {activeTab === 'transcript' && (
          <div className="bg-white border border-blue-200/60 rounded-2xl overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-blue-200/60 flex justify-between items-center">
              <h3 className="text-gray-800 font-semibold">Full Transcript</h3>
              <button
                onClick={() => {
                  const text = transcript
                    .map((e) => `[${e.speaker_name}] ${e.text}`)
                    .join('\n');
                  navigator.clipboard.writeText(text).catch(() => {});
                }}
                className="px-3 py-1.5 rounded-lg text-xs bg-gray-100 text-gray-600 hover:bg-blue-100 transition-colors"
              >
                Copy All
              </button>
            </div>
            <div className="max-h-[500px] overflow-y-auto p-4 space-y-3">
              {transcript.length > 0 ? (
                transcript.map((entry, i) => {
                  const agent = AGENTS.find((a) => a.id === entry.speaker);
                  const color = agent?.color || '#666';
                  const initials = (entry.speaker_name || entry.speaker || '')
                    .split(' ')
                    .map((n) => n[0])
                    .join('');

                  return (
                    <div key={i} className="flex gap-3 py-2">
                      <div
                        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                        style={{ background: color }}
                      >
                        {agent?.avatar || initials}
                      </div>
                      <div>
                        <div className="flex items-baseline gap-2">
                          <span className="text-sm font-semibold" style={{ color }}>
                            {entry.speaker_name || entry.speaker}
                          </span>
                          <span className="text-gray-400 text-xs">
                            {entry.agent_role ? `${entry.agent_role} · ` : ''}
                            {formatTimestamp(entry.start_time)}
                          </span>
                        </div>
                        <p className="text-gray-600 text-sm mt-0.5">{entry.text}</p>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-gray-400 text-sm text-center py-8">
                  No transcript entries recorded.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Scores Tab */}
        {activeTab === 'scores' && (
          <div className="grid grid-cols-3 gap-4">
            {allScoreEntries.map(([key, val]) => (
              <div
                key={key}
                className="bg-white border border-blue-200/60 rounded-2xl p-6 text-center shadow-sm"
              >
                <div className="text-4xl font-black text-gray-900 mb-1 font-display">{val}</div>
                <div className="text-gray-500 text-sm capitalize">{key}</div>
                <div className="mt-4 h-2 bg-blue-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${val}%`,
                      background: val >= 80 ? '#10b981' : val >= 70 ? '#f59e0b' : '#ef4444',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Coaching Tab */}
        {activeTab === 'advice' && (
          <div className="space-y-4">
            {coachingItems.length > 0 ? (
              coachingItems.map((item, i) => (
                <div
                  key={i}
                  className="bg-white border border-blue-200/60 rounded-2xl p-6 shadow-sm"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                        item.priority === 'high'
                          ? 'bg-red-100 text-red-500'
                          : item.priority === 'medium'
                          ? 'bg-amber-100 text-amber-600'
                          : 'bg-blue-100 text-blue-500'
                      }`}
                    >
                      {item.priority.charAt(0).toUpperCase() + item.priority.slice(1)}
                    </span>
                    <span className="text-gray-800 font-semibold text-sm">{item.area}</span>
                  </div>
                  <p className="text-gray-600 text-sm leading-relaxed">{item.detail}</p>
                </div>
              ))
            ) : (
              <div className="text-gray-400 text-sm text-center py-8">
                No coaching items available.
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-center gap-4 mt-10">
          <button
            onClick={handleRestart}
            className="px-6 py-3 rounded-xl text-sm font-semibold bg-blue-500 text-white hover:bg-blue-600 transition-all shadow-md shadow-blue-200"
          >
            Run Another Session
          </button>
          <button
            onClick={handleExportReport}
            className="px-6 py-3 rounded-xl text-sm font-medium bg-white border border-blue-200 text-gray-600 hover:bg-blue-50 transition-all"
          >
            Export Report (JSON)
          </button>
          <button
            onClick={handleDownloadRecording}
            className="px-6 py-3 rounded-xl text-sm font-medium bg-white border border-blue-200 text-gray-600 hover:bg-blue-50 transition-all"
          >
            Download Recording
          </button>
        </div>
      </div>
    </div>
  );
}

function formatTimestamp(seconds) {
  if (seconds == null) return '';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
