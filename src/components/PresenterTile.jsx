import React from 'react';

export default function PresenterTile({ isRecording, isMuted }) {
  return (
    <div className="relative rounded-2xl overflow-hidden aspect-video bg-gradient-to-br from-gray-800 to-gray-900 ring-2 ring-blue-500 ring-offset-2 ring-offset-gray-950">
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-2xl font-bold mb-3">
          YOU
        </div>
        <div className="text-white font-semibold">Presenter</div>
        <div className="flex gap-2 mt-3">
          {isRecording && (
            <span className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-red-500/20 text-red-400 text-xs">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              REC
            </span>
          )}
          {isMuted && (
            <span className="px-2 py-1 rounded-full bg-gray-700 text-gray-400 text-xs">
              🔇 Muted
            </span>
          )}
        </div>
      </div>

      {isRecording && (
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1">
          {[0, 1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="w-1 bg-blue-400 rounded-full animate-pulse"
              style={{
                height: `${6 + Math.random() * 20}px`,
                animationDelay: `${i * 0.1}s`,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
