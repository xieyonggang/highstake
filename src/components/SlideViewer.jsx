import React from 'react';
import { DEMO_SLIDES } from '../utils/constants';

export default function SlideViewer({ currentSlide, totalSlides, onNext, onPrev, slides, deckId, captionText }) {
  // Use real slides from deck manifest if available, otherwise fallback to demo
  const slideData = slides && slides.length > 0 ? slides[currentSlide] : DEMO_SLIDES[currentSlide];
  const hasThumbnail = slideData && deckId && slideData.thumbnail_url;

  return (
    <div className="bg-gray-900/80 backdrop-blur rounded-2xl border border-gray-700/50 overflow-hidden flex flex-col h-full">
      <div className="bg-gradient-to-r from-gray-800 to-gray-850 px-4 py-2 flex items-center justify-between border-b border-gray-700/50 flex-shrink-0">
        <span className="text-gray-400 text-xs font-medium">SLIDES</span>
        <span className="text-gray-500 text-xs">
          {currentSlide + 1} / {totalSlides}
        </span>
      </div>
      <div className="p-6 flex-1 bg-gradient-to-br from-gray-900 via-gray-900 to-blue-950/30 overflow-y-auto">
        {hasThumbnail ? (
          <img
            src={slideData.thumbnail_url}
            alt={slideData.title || `Slide ${currentSlide + 1}`}
            className="w-full rounded-lg"
          />
        ) : slideData ? (
          <>
            <div className="text-blue-400 text-xs font-semibold tracking-wider mb-2">
              {slideData.subtitle}
            </div>
            <h3 className="text-white text-xl font-bold mb-4 font-display">
              {slideData.title}
            </h3>
            {/* Render bullets for demo slides or body_text for parsed slides */}
            {slideData.bullets
              ? slideData.bullets.map((b, i) => (
                  <div key={i} className="flex items-start gap-2 mb-2">
                    <span className="text-blue-400 mt-1">›</span>
                    <span className="text-gray-300 text-sm">{b}</span>
                  </div>
                ))
              : slideData.body_text && (
                  <div className="text-gray-300 text-sm whitespace-pre-line">
                    {slideData.body_text}
                  </div>
                )}
          </>
        ) : (
          <div className="text-gray-500 text-sm text-center py-8">No slide content</div>
        )}
      </div>
      <div className="px-4 py-3 flex items-center gap-3 border-t border-gray-700/50 flex-shrink-0">
        <button
          onClick={onPrev}
          disabled={currentSlide === 0}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-300 hover:bg-gray-700 disabled:opacity-30 transition-all flex-shrink-0"
        >
          ← Previous
        </button>
        <div className="flex-1 min-w-0">
          {captionText ? (
            <p className="text-white text-xs text-center leading-relaxed line-clamp-2" title={captionText}>
              {captionText.split(/\s+/).slice(-40).join(' ')}
            </p>
          ) : (
            <p className="text-gray-600 text-xs text-center">
              {currentSlide + 1} / {totalSlides}
            </p>
          )}
        </div>
        <button
          onClick={onNext}
          disabled={currentSlide >= totalSlides - 1}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-30 transition-all flex-shrink-0"
        >
          Next →
        </button>
      </div>
    </div>
  );
}
