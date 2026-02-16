import React from 'react';
import { DEMO_SLIDES } from '../utils/constants';

export default function SlideViewer({ currentSlide, totalSlides, onNext, onPrev }) {
  const slide = DEMO_SLIDES[currentSlide] || DEMO_SLIDES[0];

  return (
    <div className="bg-gray-900/80 backdrop-blur rounded-2xl border border-gray-700/50 overflow-hidden">
      <div className="bg-gradient-to-r from-gray-800 to-gray-850 px-4 py-2 flex items-center justify-between border-b border-gray-700/50">
        <span className="text-gray-400 text-xs font-medium">SLIDES</span>
        <span className="text-gray-500 text-xs">
          {currentSlide + 1} / {totalSlides}
        </span>
      </div>
      <div className="p-6 min-h-[200px] bg-gradient-to-br from-gray-900 via-gray-900 to-blue-950/30">
        <div className="text-blue-400 text-xs font-semibold tracking-wider mb-2">
          {slide.subtitle}
        </div>
        <h3 className="text-white text-xl font-bold mb-4 font-display">{slide.title}</h3>
        {slide.bullets.map((b, i) => (
          <div key={i} className="flex items-start gap-2 mb-2">
            <span className="text-blue-400 mt-1">›</span>
            <span className="text-gray-300 text-sm">{b}</span>
          </div>
        ))}
      </div>
      <div className="px-4 py-3 flex justify-between border-t border-gray-700/50">
        <button
          onClick={onPrev}
          disabled={currentSlide === 0}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-300 hover:bg-gray-700 disabled:opacity-30 transition-all"
        >
          ← Previous
        </button>
        <button
          onClick={onNext}
          disabled={currentSlide >= totalSlides - 1}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-30 transition-all"
        >
          Next →
        </button>
      </div>
    </div>
  );
}
