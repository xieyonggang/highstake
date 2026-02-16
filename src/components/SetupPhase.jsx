import React, { useState, useRef } from 'react';
import { AGENTS, INTERACTION_MODES, INTENSITY_LEVELS, FOCUS_AREAS } from '../utils/constants';
import { useSessionStore } from '../stores/sessionStore';
import { uploadDeck, createSession } from '../services/api';

export default function SetupPhase() {
  const { config, setConfig, setDeckManifest, setSessionId, setPhase } = useSessionStore();
  const [step, setStep] = useState(0);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [deckId, setDeckId] = useState(null);
  const [isStarting, setIsStarting] = useState(false);
  const fileInputRef = useRef(null);

  const moderator = AGENTS[0];

  const moderatorMessages = [
    "Welcome to the Boardroom. I'm Diana Chen, and I'll be moderating your session today. Let's get you set up. First — how would you like the panel to engage with you?",
    'Got it. Now, how intense should we make this session?',
    "Perfect. Are there specific areas you'd like the panel to focus on?",
    "Almost ready. Upload your presentation deck and we'll begin.",
  ];

  const handleFileSelect = async (file) => {
    if (!file) return;
    const name = file.name.toLowerCase();
    if (!name.endsWith('.pdf')) {
      setUploadError('Please upload a PDF file. Export your PPTX to PDF first for best slide rendering.');
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
      setUploadError(err.message || 'Failed to upload deck. You can still use the demo deck.');
      setIsUploading(false);
    }
  };

  const handleUseDemoDeck = () => {
    setUploadedFile({ name: 'Q4_Strategy_Deck.pptx', size: 2450000 });
    setDeckId(null);
    setUploadError(null);
  };

  const handleStart = async () => {
    setIsStarting(true);
    try {
      const session = await createSession({
        interaction: config.interaction,
        intensity: config.intensity,
        focuses: config.focuses,
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
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 mb-6">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
            <span className="text-indigo-400 text-xs font-semibold tracking-wider">HIGHSTAKE</span>
          </div>
          <h1 className="text-4xl font-black text-white tracking-tight font-display">
            Pre-Session Setup
          </h1>
        </div>

        {/* Moderator Bubble */}
        <div className="flex gap-4 mb-8">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold flex-shrink-0"
            style={{ background: `linear-gradient(135deg, ${moderator.color}, ${moderator.color}cc)` }}
          >
            {moderator.avatar}
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-2xl rounded-tl-md px-5 py-4 flex-1">
            <div className="text-indigo-400 text-xs font-semibold mb-1">
              {moderator.name} · {moderator.role}
            </div>
            <p className="text-gray-300 text-sm leading-relaxed">{moderatorMessages[step]}</p>
          </div>
        </div>

        {/* Step Content */}
        <div className="space-y-3 mb-8">
          {step === 0 &&
            INTERACTION_MODES.map((mode) => (
              <button
                key={mode.id}
                onClick={() => setConfig({ ...config, interaction: mode.id })}
                className={`w-full text-left px-5 py-4 rounded-xl border transition-all duration-300 ${
                  config.interaction === mode.id
                    ? 'bg-indigo-500/10 border-indigo-500/50 shadow-lg shadow-indigo-500/10'
                    : 'bg-gray-900/50 border-gray-800 hover:border-gray-700'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{mode.icon}</span>
                  <div>
                    <div className="text-white font-semibold text-sm">{mode.label}</div>
                    <div className="text-gray-500 text-xs mt-0.5">{mode.desc}</div>
                  </div>
                </div>
              </button>
            ))}

          {step === 1 &&
            INTENSITY_LEVELS.map((level) => (
              <button
                key={level.id}
                onClick={() => setConfig({ ...config, intensity: level.id })}
                className={`w-full text-left px-5 py-4 rounded-xl border transition-all duration-300 ${
                  config.intensity === level.id
                    ? 'bg-indigo-500/10 border-indigo-500/50 shadow-lg shadow-indigo-500/10'
                    : 'bg-gray-900/50 border-gray-800 hover:border-gray-700'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{level.emoji}</span>
                  <div>
                    <div className="text-white font-semibold text-sm">{level.label}</div>
                    <div className="text-gray-500 text-xs mt-0.5">{level.desc}</div>
                  </div>
                </div>
              </button>
            ))}

          {step === 2 && (
            <div className="grid grid-cols-2 gap-2">
              {FOCUS_AREAS.map((area) => (
                <button
                  key={area}
                  onClick={() => {
                    const focuses = config.focuses.includes(area)
                      ? config.focuses.filter((f) => f !== area)
                      : [...config.focuses, area];
                    setConfig({ ...config, focuses });
                  }}
                  className={`px-4 py-3 rounded-xl border text-sm font-medium transition-all ${
                    config.focuses.includes(area)
                      ? 'bg-indigo-500/15 border-indigo-500/50 text-indigo-300'
                      : 'bg-gray-900/50 border-gray-800 text-gray-400 hover:border-gray-700'
                  }`}
                >
                  {config.focuses.includes(area) ? '✓ ' : ''}
                  {area}
                </button>
              ))}
            </div>
          )}

          {step === 3 && (
            <>
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  const file = e.dataTransfer.files[0];
                  if (file) handleFileSelect(file);
                }}
                className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer ${
                  dragOver
                    ? 'border-indigo-500 bg-indigo-500/5'
                    : uploadedFile
                    ? 'border-emerald-500/50 bg-emerald-500/5'
                    : 'border-gray-700 hover:border-gray-600'
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
                  <div>
                    <div className="text-4xl mb-3">📊</div>
                    <div className="text-white font-semibold">{uploadedFile.name}</div>
                    <div className="text-gray-500 text-sm mt-1">
                      {isUploading ? (
                        <span className="text-indigo-400">Parsing slides...</span>
                      ) : (
                        `${(uploadedFile.size / 1024).toFixed(1)} KB`
                      )}
                    </div>
                    {!isUploading && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setUploadedFile(null);
                          setDeckId(null);
                          setUploadError(null);
                        }}
                        className="mt-3 text-xs text-red-400 hover:text-red-300"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ) : (
                  <div>
                    <div className="text-4xl mb-3 opacity-50">📎</div>
                    <div className="text-gray-400 font-medium">Drop your PDF here</div>
                    <div className="text-gray-600 text-sm mt-1">or click to browse</div>
                  </div>
                )}
              </div>
              {!uploadedFile && (
                <button
                  onClick={handleUseDemoDeck}
                  className="w-full mt-2 px-4 py-2 rounded-lg bg-gray-800 text-gray-300 text-xs hover:bg-gray-700 transition-colors"
                >
                  Use Demo Deck
                </button>
              )}
              {uploadError && (
                <div className="mt-2 text-red-400 text-sm text-center">{uploadError}</div>
              )}
            </>
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between">
          <button
            onClick={() => setStep(Math.max(0, step - 1))}
            disabled={step === 0}
            className="px-5 py-2.5 rounded-xl text-sm font-medium bg-gray-800 text-gray-300 hover:bg-gray-700 disabled:opacity-0 transition-all"
          >
            ← Back
          </button>
          {step < 3 ? (
            <button
              onClick={() => setStep(step + 1)}
              disabled={
                (step === 0 && !config.interaction) || (step === 1 && !config.intensity)
              }
              className="px-6 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-30 transition-all"
            >
              Continue →
            </button>
          ) : (
            <button
              onClick={handleStart}
              disabled={!uploadedFile || isUploading || isStarting}
              className="px-6 py-2.5 rounded-xl text-sm font-bold bg-gradient-to-r from-indigo-600 to-violet-600 text-white hover:from-indigo-500 hover:to-violet-500 disabled:opacity-30 transition-all shadow-lg shadow-indigo-500/25"
            >
              {isStarting ? 'Starting...' : 'Enter the Boardroom →'}
            </button>
          )}
        </div>

        {/* Progress */}
        <div className="flex justify-center gap-2 mt-8">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className={`h-1 rounded-full transition-all duration-500 ${
                i <= step ? 'w-8 bg-indigo-500' : 'w-4 bg-gray-800'
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
