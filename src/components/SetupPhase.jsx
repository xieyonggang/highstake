import React, { useState, useRef } from 'react';
import { AGENTS, INTERACTION_MODES, INTENSITY_LEVELS } from '../utils/constants';
import { useSessionStore } from '../stores/sessionStore';
import { uploadDeck, createSession } from '../services/api';

const CORE_AGENTS = AGENTS.filter((a) => !a.optional);
const OPTIONAL_AGENTS = AGENTS.filter((a) => a.optional);

export default function SetupPhase() {
  const { config, setConfig, setDeckManifest, setSessionId, setPhase } = useSessionStore();
  const [uploadedFile, setUploadedFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [deckId, setDeckId] = useState(null);
  const [isStarting, setIsStarting] = useState(false);
  const [showInvitePopup, setShowInvitePopup] = useState(false);
  const fileInputRef = useRef(null);

  const selectedAgents = AGENTS.filter(
    (a) => a.id === 'moderator' || config.agents.includes(a.id)
  );

  const handleFileSelect = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Please upload a PDF file.');
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setUploadError('File size exceeds 50MB limit.');
      return;
    }

    setUploadedFile(file);
    setUploadError(null);
    setIsUploading(true);

    try {
      const manifest = await uploadDeck(file);
      setDeckManifest(manifest);
      setDeckId(manifest.id);
      setIsUploading(false);
    } catch (err) {
      setUploadError(err.message || 'Failed to upload deck.');
      setIsUploading(false);
    }
  };

  const toggleOptionalAgent = (agentId) => {
    const isSelected = config.agents.includes(agentId);
    const agents = isSelected
      ? config.agents.filter((id) => id !== agentId)
      : [...config.agents, agentId];
    setConfig({ ...config, agents });
  };

  const handleStart = async () => {
    setIsStarting(true);
    try {
      const session = await createSession({
        interaction: config.interaction,
        intensity: config.intensity,
        agents: config.agents,
        deckId: deckId,
      });
      setSessionId(session.id);
      setPhase('meeting');
    } catch (err) {
      setUploadError(err.message || 'Failed to create session.');
      setIsStarting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-sky-50 flex items-center justify-center p-6">
      <div className="w-full max-w-xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-100 border border-blue-200 mb-4">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-blue-600 text-xs font-semibold tracking-wider">HIGHSTAKE</span>
          </div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight font-display">
            Session Setup
          </h1>
          <p className="text-gray-500 text-sm mt-2">Configure your boardroom session and jump in.</p>
        </div>

        {/* Interaction Mode */}
        <div className="mb-5">
          <label className="text-gray-500 text-xs font-semibold tracking-wider uppercase mb-2 block">
            Interaction Mode
          </label>
          <div className="flex gap-2">
            {INTERACTION_MODES.map((mode) => (
              <button
                key={mode.id}
                onClick={() => setConfig({ ...config, interaction: mode.id })}
                className={`flex-1 px-3 py-2.5 rounded-xl border text-center transition-all ${
                  config.interaction === mode.id
                    ? 'bg-blue-50 border-blue-400 shadow-md shadow-blue-100'
                    : 'bg-white border-gray-200 hover:border-blue-300 hover:bg-blue-50/50'
                }`}
              >
                <div className="text-lg mb-0.5">{mode.icon}</div>
                <div className="text-gray-800 text-xs font-semibold">{mode.label}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Intensity */}
        <div className="mb-5">
          <label className="text-gray-500 text-xs font-semibold tracking-wider uppercase mb-2 block">
            Intensity
          </label>
          <div className="flex gap-2">
            {INTENSITY_LEVELS.map((level) => (
              <button
                key={level.id}
                onClick={() => setConfig({ ...config, intensity: level.id })}
                className={`flex-1 px-3 py-2.5 rounded-xl border text-center transition-all ${
                  config.intensity === level.id
                    ? 'bg-blue-50 border-blue-400 shadow-md shadow-blue-100'
                    : 'bg-white border-gray-200 hover:border-blue-300 hover:bg-blue-50/50'
                }`}
              >
                <div className="text-lg mb-0.5">{level.emoji}</div>
                <div className="text-gray-800 text-xs font-semibold">{level.label}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Deck Upload (optional) */}
        <div className="mb-6">
          <label className="text-gray-500 text-xs font-semibold tracking-wider uppercase mb-2 block">
            Presentation Deck <span className="text-gray-400 normal-case">(optional)</span>
          </label>
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const file = e.dataTransfer.files[0];
              if (file) handleFileSelect(file);
            }}
            className={`border-2 border-dashed rounded-xl px-6 py-5 text-center transition-all cursor-pointer ${
              dragOver
                ? 'border-blue-400 bg-blue-50'
                : uploadedFile
                ? 'border-emerald-400 bg-emerald-50'
                : 'border-gray-300 hover:border-blue-300 bg-white'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => handleFileSelect(e.target.files[0])}
            />
            {uploadedFile ? (
              <div className="flex items-center justify-center gap-3">
                <span className="text-2xl">📊</span>
                <div className="text-left">
                  <div className="text-gray-800 text-sm font-semibold">{uploadedFile.name}</div>
                  <div className="text-gray-500 text-xs">
                    {isUploading ? (
                      <span className="text-blue-500">Parsing slides...</span>
                    ) : (
                      `${(uploadedFile.size / 1024).toFixed(1)} KB`
                    )}
                  </div>
                </div>
                {!isUploading && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setUploadedFile(null);
                      setDeckId(null);
                      setUploadError(null);
                    }}
                    className="text-xs text-red-400 hover:text-red-500 ml-2"
                  >
                    Remove
                  </button>
                )}
              </div>
            ) : (
              <div>
                <span className="text-gray-400 text-sm">Drop PDF here or click to browse</span>
              </div>
            )}
          </div>
          {uploadError && (
            <div className="mt-1.5 text-red-500 text-xs text-center">{uploadError}</div>
          )}
        </div>

        {/* Panel Preview */}
        <div className="mb-6">
          <label className="text-gray-500 text-xs font-semibold tracking-wider uppercase mb-2 block">
            Your Panel
          </label>
          <div className="flex gap-3 justify-center items-start flex-wrap">
            {selectedAgents.map((agent) => (
              <div key={agent.id} className="text-center relative group w-14">
                <div
                  className="w-11 h-11 rounded-full flex items-center justify-center text-white font-bold text-sm mx-auto mb-1"
                  style={{ background: agent.color }}
                >
                  {agent.avatar}
                </div>
                <div className="text-gray-700 text-[10px] font-medium leading-tight">{agent.name.split(' ')[0]}</div>
                <div className="text-[9px] leading-tight mt-0.5" style={{ color: agent.color }}>{agent.role}</div>
                {/* Remove button for optional agents */}
                {agent.optional && (
                  <button
                    onClick={() => toggleOptionalAgent(agent.id)}
                    className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-400 text-white text-[10px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500"
                    title={`Remove ${agent.name}`}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            {/* Add panelist button */}
            <div className="text-center w-14">
              <button
                onClick={() => setShowInvitePopup(true)}
                className="w-11 h-11 rounded-full border-2 border-dashed border-blue-300 flex items-center justify-center mx-auto mb-1 text-blue-400 hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50 transition-all"
                title="Invite more panelists"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
              </button>
              <div className="text-blue-400 text-[10px]">Invite</div>
            </div>
          </div>
        </div>

        {/* Start Button */}
        <button
          onClick={handleStart}
          disabled={!config.interaction || !config.intensity || isUploading || isStarting}
          className="w-full py-3.5 rounded-xl text-sm font-bold bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-30 transition-all shadow-lg shadow-blue-200"
        >
          {isStarting ? 'Starting...' : 'Enter the Boardroom'}
        </button>
      </div>

      {/* Invite Panelist Popup */}
      {showInvitePopup && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm"
          onClick={() => setShowInvitePopup(false)}
        >
          <div
            className="bg-white rounded-2xl shadow-xl border border-blue-200 w-full max-w-sm mx-4 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-5 py-4 border-b border-blue-100">
              <h3 className="text-gray-900 font-bold text-base">Invite Panelists</h3>
              <p className="text-gray-400 text-xs mt-0.5">Select additional experts for your session.</p>
            </div>
            <div className="p-3 space-y-1 max-h-80 overflow-y-auto">
              {OPTIONAL_AGENTS.map((agent) => {
                const isSelected = config.agents.includes(agent.id);
                return (
                  <button
                    key={agent.id}
                    onClick={() => toggleOptionalAgent(agent.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${
                      isSelected
                        ? 'bg-blue-50 border border-blue-300'
                        : 'hover:bg-gray-50 border border-transparent'
                    }`}
                  >
                    <div
                      className="w-9 h-9 rounded-full flex items-center justify-center text-white font-bold text-xs flex-shrink-0"
                      style={{ background: agent.color }}
                    >
                      {agent.avatar}
                    </div>
                    <div className="flex-1 text-left min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-800 font-semibold text-sm">{agent.name}</span>
                        <span
                          className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                          style={{ background: `${agent.color}15`, color: agent.color }}
                        >
                          {agent.role}
                        </span>
                      </div>
                      <div className="text-gray-400 text-xs truncate">{agent.title}</div>
                    </div>
                    <div className="flex-shrink-0">
                      <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all ${
                        isSelected
                          ? 'bg-blue-500 border-blue-500'
                          : 'border-gray-300'
                      }`}>
                        {isSelected && (
                          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                          </svg>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
            <div className="px-5 py-3 border-t border-blue-100 flex justify-end">
              <button
                onClick={() => setShowInvitePopup(false)}
                className="px-4 py-2 rounded-lg text-sm font-semibold bg-blue-500 text-white hover:bg-blue-600 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
