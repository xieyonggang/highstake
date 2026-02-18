import React from 'react';

export default function AgentTile({ agent, isActive, isSpeaking, hasHandRaised, isInExchange, isThinking, exchangeTurnInfo, compact }) {
  if (compact) {
    return (
      <div
        className={`relative flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-300 ${
          isActive ? 'ring-1 ring-offset-1 ring-offset-white' : ''
        }`}
        style={{
          background: `linear-gradient(135deg, ${agent.color}12, ${agent.color}06)`,
          borderColor: isActive ? agent.color : 'transparent',
          boxShadow: isSpeaking ? `0 0 20px ${agent.color}20` : 'none',
        }}
      >
        <div
          className={`relative w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0 transition-transform duration-300 ${
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
        <div className="flex-1 min-w-0">
          <div className="text-gray-800 font-semibold text-sm truncate">{agent.name}</div>
          <div className="text-gray-500 text-xs truncate">{agent.role}</div>
        </div>
        {isThinking && !isSpeaking && (
          <div className="flex gap-1 flex-shrink-0">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-1.5 h-1.5 rounded-full animate-bounce"
                style={{
                  background: agent.color,
                  animationDelay: `${i * 0.2}s`,
                }}
              />
            ))}
          </div>
        )}
        {isInExchange && !isSpeaking && !isThinking && (
          <span
            className="flex-shrink-0 px-1.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider animate-pulse"
            style={{ background: `${agent.color}20`, color: agent.color }}
          >
            {exchangeTurnInfo
              ? `${exchangeTurnInfo.turnNumber}/${exchangeTurnInfo.maxTurns}`
              : 'Q&A'}
          </span>
        )}
        {hasHandRaised && (
          <span className="text-lg animate-bounce flex-shrink-0">&#9995;</span>
        )}
        {isSpeaking && (
          <div className="flex gap-0.5 flex-shrink-0">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-0.5 rounded-full animate-pulse"
                style={{
                  background: agent.color,
                  height: `${6 + Math.random() * 10}px`,
                  animationDelay: `${i * 0.15}s`,
                }}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className={`relative rounded-2xl overflow-hidden aspect-video transition-all duration-500 ${
        isActive ? 'ring-2 ring-offset-2 ring-offset-white' : ''
      }`}
      style={{
        background: `linear-gradient(135deg, ${agent.color}15, ${agent.color}08)`,
        borderColor: isActive ? agent.color : 'transparent',
        boxShadow: isSpeaking ? `0 0 30px ${agent.color}30` : 'none',
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
        <div className="text-gray-800 font-semibold text-sm">{agent.name}</div>
        <div className="text-gray-500 text-xs">{agent.title}</div>
        <div
          className="mt-1 px-2 py-0.5 rounded-full text-xs font-medium"
          style={{ background: `${agent.color}20`, color: agent.color }}
        >
          {agent.role}
        </div>
      </div>

      {isThinking && !isSpeaking && (
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-2 h-2 rounded-full animate-bounce"
              style={{
                background: agent.color,
                animationDelay: `${i * 0.2}s`,
              }}
            />
          ))}
        </div>
      )}

      {hasHandRaised && (
        <div className="absolute top-3 right-3 text-2xl animate-bounce">&#9995;</div>
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
