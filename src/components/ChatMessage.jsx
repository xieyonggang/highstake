import React, { useState } from 'react';

export default function ChatMessage({ agent, message, timestamp, audioUrl, slideRef, sessionTimestamp }) {
  const [isPlaying, setIsPlaying] = useState(false);

  const handlePlayAudio = () => {
    if (!audioUrl) return;
    const audio = new Audio(audioUrl);
    setIsPlaying(true);
    audio.onended = () => setIsPlaying(false);
    audio.onerror = () => setIsPlaying(false);
    audio.play().catch(() => setIsPlaying(false));
  };

  const slideLabel = slideRef != null ? `Slide ${slideRef + 1}` : null;

  return (
    <div className="flex gap-3 py-3 px-4 hover:bg-blue-50/50 rounded-xl transition-colors">
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
        style={{ background: agent.color }}
      >
        {agent.avatar}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className="text-sm font-semibold" style={{ color: agent.color }}>
            {agent.name}
          </span>
          <span className="text-gray-400 text-xs">{sessionTimestamp || timestamp}</span>
          {slideLabel && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-blue-50 text-blue-500 font-medium">
              {slideLabel}
            </span>
          )}
          {audioUrl && (
            <button
              onClick={handlePlayAudio}
              className="text-gray-400 hover:text-blue-500 text-xs transition-colors"
              title="Replay audio"
            >
              {isPlaying ? '⏸' : '🔊'}
            </button>
          )}
        </div>
        <p className="text-gray-700 text-sm mt-0.5 leading-relaxed">{message}</p>
      </div>
    </div>
  );
}
