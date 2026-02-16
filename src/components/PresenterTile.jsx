import React, { useRef, useEffect } from 'react';

export default function PresenterTile({ isRecording, isMuted, videoStream }) {
  const videoRef = useRef(null);

  useEffect(() => {
    if (videoRef.current && videoStream) {
      videoRef.current.srcObject = videoStream;
    }
  }, [videoStream]);

  return (
    <div className="relative rounded-2xl overflow-hidden aspect-video bg-gradient-to-br from-gray-800 to-gray-900 ring-2 ring-blue-500 ring-offset-2 ring-offset-gray-950">
      {videoStream ? (
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="absolute inset-0 w-full h-full object-cover"
        />
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-2xl font-bold mb-3">
            YOU
          </div>
          <div className="text-white font-semibold">Presenter</div>
        </div>
      )}

      <div className="absolute top-3 left-3 flex gap-2">
        {isRecording && (
          <span className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-red-500/20 backdrop-blur text-red-400 text-xs">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            REC
          </span>
        )}
        {isMuted && (
          <span className="px-2 py-1 rounded-full bg-gray-700/80 backdrop-blur text-gray-400 text-xs">
            🔇 Muted
          </span>
        )}
      </div>

      {isRecording && !videoStream && (
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
