import React from 'react';

export default function ChatMessage({ agent, message, timestamp }) {
  return (
    <div className="flex gap-3 py-3 px-4 hover:bg-white/5 rounded-xl transition-colors">
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
        style={{ background: agent.color }}
      >
        {agent.avatar}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold" style={{ color: agent.color }}>
            {agent.name}
          </span>
          <span className="text-gray-600 text-xs">{timestamp}</span>
        </div>
        <p className="text-gray-300 text-sm mt-0.5 leading-relaxed">{message}</p>
      </div>
    </div>
  );
}
