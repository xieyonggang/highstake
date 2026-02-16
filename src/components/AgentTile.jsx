import React from 'react';

export default function AgentTile({ agent, isActive, isSpeaking, hasHandRaised }) {
  return (
    <div
      className={`relative rounded-2xl overflow-hidden aspect-video transition-all duration-500 ${
        isActive ? 'ring-2 ring-offset-2 ring-offset-gray-950' : ''
      }`}
      style={{
        background: `linear-gradient(135deg, ${agent.color}22, ${agent.color}08)`,
        borderColor: isActive ? agent.color : 'transparent',
        boxShadow: isSpeaking ? `0 0 30px ${agent.color}40` : 'none',
      }}
    >
      <div className="absolute inset-0 flex flex-col items-center justify-center p-4">
        <div
          className={`relative w-16 h-16 rounded-full flex items-center justify-center text-white font-bold text-xl mb-3 transition-transform duration-300 ${
            isSpeaking ? 'scale-110' : ''
          }`}
          style={{ background: `linear-gradient(135deg, ${agent.color}, ${agent.color}cc)` }}
        >
          {agent.avatar}
          {isSpeaking && (
            <div
              className="absolute inset-0 rounded-full animate-ping opacity-30"
              style={{ background: agent.color }}
            />
          )}
        </div>
        <div className="text-white font-semibold text-sm">{agent.name}</div>
        <div className="text-gray-400 text-xs">{agent.title}</div>
        <div
          className="mt-1 px-2 py-0.5 rounded-full text-xs font-medium"
          style={{ background: `${agent.color}30`, color: agent.color }}
        >
          {agent.role}
        </div>
      </div>

      {hasHandRaised && (
        <div className="absolute top-3 right-3 text-2xl animate-bounce">✋</div>
      )}

      {isSpeaking && (
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1">
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="w-1 rounded-full animate-pulse"
              style={{
                background: agent.color,
                height: `${8 + Math.random() * 16}px`,
                animationDelay: `${i * 0.15}s`,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
