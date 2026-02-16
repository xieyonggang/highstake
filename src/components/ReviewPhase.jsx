import React, { useState } from 'react';
import { AGENTS } from '../utils/constants';

const SCORES = {
  overall: 78,
  clarity: 82,
  confidence: 71,
  dataSupport: 85,
  handling: 68,
  structure: 80,
};

const IMPROVEMENTS = [
  {
    area: 'Q&A Handling',
    priority: 'High',
    detail:
      'When the Skeptic challenged your revenue projections, you hesitated and repeated the same figures. Prepare 2-3 alternative data points to support contested claims.',
  },
  {
    area: 'Pacing',
    priority: 'Medium',
    detail:
      'You spent 40% of your time on the first two slides. Consider timing yourself — aim for roughly equal time per section.',
  },
  {
    area: 'Defensive Responses',
    priority: 'High',
    detail:
      'When the Contrarian pushed on worst-case scenarios, your body language shifted. Practice acknowledging risks confidently before redirecting to mitigations.',
  },
  {
    area: 'Data Visualization',
    priority: 'Low',
    detail:
      'Your financial model slide was text-heavy. Consider replacing bullet points with a clear chart showing the growth trajectory.',
  },
];

const STRENGTHS = [
  'Strong opening — you established credibility quickly with the market data.',
  'Excellent use of competitive framing on slide 3.',
  'Your closing ask was clear and well-justified.',
  "Good rapport with the Analyst's detailed questions.",
];

export default function ReviewPhase({ sessionData, onRestart }) {
  const [activeTab, setActiveTab] = useState('summary');

  const tabs = [
    { id: 'summary', label: 'Summary' },
    { id: 'transcript', label: 'Transcript' },
    { id: 'scores', label: 'Scores' },
    { id: 'advice', label: 'Coaching' },
  ];

  return (
    <div className="min-h-screen bg-gray-950 p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-4">
            <span className="text-emerald-400 text-xs font-semibold tracking-wider">
              SESSION COMPLETE
            </span>
          </div>
          <h1 className="text-4xl font-black text-white mb-2 font-display">Post-Session Debrief</h1>
          <p className="text-gray-400">
            Duration: {Math.floor((sessionData?.duration || 0) / 60)}m{' '}
            {(sessionData?.duration || 0) % 60}s · Slides: {sessionData?.slideCount || 6} ·
            Questions:{' '}
            {(sessionData?.messages || []).filter((m) => m.agent.id !== 'moderator').length}
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-gray-900/50 p-1 rounded-xl mb-8 max-w-md mx-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-indigo-600 text-white shadow-lg'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Summary Tab */}
        {activeTab === 'summary' && (
          <div className="grid grid-cols-2 gap-6">
            <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-8 text-center">
              <div className="text-6xl font-black text-white mb-2 font-display">
                {SCORES.overall}
                <span className="text-2xl text-gray-500">/100</span>
              </div>
              <div className="text-gray-400 text-sm mb-6">Overall Presentation Score</div>
              <div className="space-y-3">
                {Object.entries(SCORES)
                  .filter(([k]) => k !== 'overall')
                  .map(([key, val]) => (
                    <div key={key} className="flex items-center gap-3">
                      <span className="text-gray-400 text-xs w-24 text-right capitalize">
                        {key.replace(/([A-Z])/g, ' $1')}
                      </span>
                      <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-1000"
                          style={{
                            width: `${val}%`,
                            background:
                              val >= 80 ? '#10b981' : val >= 70 ? '#f59e0b' : '#ef4444',
                          }}
                        />
                      </div>
                      <span className="text-white text-xs font-mono w-8">{val}</span>
                    </div>
                  ))}
              </div>
            </div>

            <div className="bg-gray-900/80 border border-gray-800 rounded-2xl p-6">
              <h3 className="text-emerald-400 font-semibold text-sm mb-4">Strengths</h3>
              <div className="space-y-3">
                {STRENGTHS.map((s, i) => (
                  <div key={i} className="flex gap-3">
                    <span className="text-emerald-500 mt-0.5">✓</span>
                    <span className="text-gray-300 text-sm leading-relaxed">{s}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="col-span-2 bg-gray-900/80 border border-gray-800 rounded-2xl p-6">
              <div className="flex gap-4">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold flex-shrink-0"
                  style={{ background: AGENTS[0].color }}
                >
                  {AGENTS[0].avatar}
                </div>
                <div>
                  <div className="text-indigo-400 text-xs font-semibold mb-1">
                    {AGENTS[0].name} · Moderator's Summary
                  </div>
                  <p className="text-gray-300 text-sm leading-relaxed">
                    Overall, this was a solid presentation with clear structure and a compelling
                    market narrative. Your biggest area for growth is handling adversarial pushback —
                    when Marcus challenged your projections, the momentum stalled. I'd recommend
                    preparing a "challenge response playbook" with pre-built answers for the 5 most
                    likely objections. Your data-driven slides were your strongest moments. Consider
                    leading with those next time to establish credibility earlier. One more session
                    at this intensity level and you'll be ready for the real boardroom.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Transcript Tab */}
        {activeTab === 'transcript' && (
          <div className="bg-gray-900/80 border border-gray-800 rounded-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800 flex justify-between items-center">
              <h3 className="text-white font-semibold">Full Transcript</h3>
              <button className="px-3 py-1.5 rounded-lg text-xs bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors">
                📋 Copy All
              </button>
            </div>
            <div className="max-h-[500px] overflow-y-auto p-4 space-y-3">
              {(sessionData?.transcript || []).map((entry, i) => (
                <div key={i} className="flex gap-3 py-2">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                    style={{
                      background:
                        AGENTS.find((a) => a.name === entry.speaker)?.color || '#666',
                    }}
                  >
                    {entry.speaker
                      .split(' ')
                      .map((n) => n[0])
                      .join('')}
                  </div>
                  <div>
                    <div className="flex items-baseline gap-2">
                      <span
                        className="text-sm font-semibold"
                        style={{
                          color:
                            AGENTS.find((a) => a.name === entry.speaker)?.color || '#999',
                        }}
                      >
                        {entry.speaker}
                      </span>
                      <span className="text-gray-600 text-xs">
                        {entry.role} · {entry.time}
                      </span>
                    </div>
                    <p className="text-gray-300 text-sm mt-0.5">{entry.text}</p>
                  </div>
                </div>
              ))}
              {(sessionData?.transcript || []).length === 0 && (
                <div className="text-gray-500 text-sm text-center py-8">
                  Transcript from your session will appear here.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Scores Tab */}
        {activeTab === 'scores' && (
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(SCORES).map(([key, val]) => (
              <div
                key={key}
                className="bg-gray-900/80 border border-gray-800 rounded-2xl p-6 text-center"
              >
                <div className="text-4xl font-black text-white mb-1 font-display">{val}</div>
                <div className="text-gray-400 text-sm capitalize">
                  {key.replace(/([A-Z])/g, ' $1')}
                </div>
                <div className="mt-4 h-2 bg-gray-800 rounded-full overflow-hidden">
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
            {IMPROVEMENTS.map((item, i) => (
              <div
                key={i}
                className="bg-gray-900/80 border border-gray-800 rounded-2xl p-6"
              >
                <div className="flex items-center gap-3 mb-3">
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                      item.priority === 'High'
                        ? 'bg-red-500/20 text-red-400'
                        : item.priority === 'Medium'
                        ? 'bg-amber-500/20 text-amber-400'
                        : 'bg-blue-500/20 text-blue-400'
                    }`}
                  >
                    {item.priority}
                  </span>
                  <span className="text-white font-semibold text-sm">{item.area}</span>
                </div>
                <p className="text-gray-300 text-sm leading-relaxed">{item.detail}</p>
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-center gap-4 mt-10">
          <button
            onClick={onRestart}
            className="px-6 py-3 rounded-xl text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-500 transition-all shadow-lg shadow-indigo-500/20"
          >
            Run Another Session
          </button>
          <button className="px-6 py-3 rounded-xl text-sm font-medium bg-gray-800 text-gray-300 hover:bg-gray-700 transition-all">
            Export Report (PDF)
          </button>
          <button className="px-6 py-3 rounded-xl text-sm font-medium bg-gray-800 text-gray-300 hover:bg-gray-700 transition-all">
            Download Recording
          </button>
        </div>
      </div>
    </div>
  );
}
