import React from 'react';
import { DEMO_SLIDES } from '../utils/constants';

export default function SlideViewer({ currentSlide, totalSlides, onNext, onPrev, slides, deckId, captionText }) {
  // Use real slides from deck manifest if available, otherwise fallback to demo
  const slideData = slides && slides.length > 0 ? slides[currentSlide] : DEMO_SLIDES[currentSlide];
  const hasThumbnail = slideData && deckId && slideData.thumbnail_url;

  return (
    <div className="bg-white border border-blue-200/60 overflow-hidden flex flex-col h-full">
      <div className="flex-1 bg-gradient-to-br from-white via-white to-blue-50/50 overflow-hidden flex items-center justify-center p-2">
        {hasThumbnail ? (
          <img
            src={slideData.thumbnail_url}
            alt={slideData.title || `Slide ${currentSlide + 1}`}
            className="max-w-full max-h-full object-contain rounded-lg"
          />
        ) : slideData ? (
          <div className="w-full h-full flex flex-col justify-center px-4">
            <div className="text-blue-500 text-xs font-semibold tracking-wider mb-2">
              {slideData.subtitle}
            </div>
            <h3 className="text-gray-900 text-xl font-bold mb-4 font-display">
              {slideData.title}
            </h3>
            {slideData.bullets
              ? slideData.bullets.map((b, i) => (
                  <div key={i} className="flex items-start gap-2 mb-2">
                    <span className="text-blue-400 mt-1">›</span>
                    <span className="text-gray-600 text-sm">{b}</span>
                  </div>
                ))
              : slideData.body_text && (
                  <div className="text-gray-600 text-sm whitespace-pre-line">
                    {slideData.body_text}
                  </div>
                )}
          </div>
        ) : (
          <div className="text-gray-400 text-sm text-center">No slide content</div>
        )}
      </div>
      <div className="px-4 py-3 flex items-center gap-3 border-t border-blue-200/60 flex-shrink-0">
        <button
          onClick={onPrev}
          disabled={currentSlide === 0}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 text-gray-600 hover:bg-blue-100 disabled:opacity-30 transition-all flex-shrink-0"
        >
          ← Previous
        </button>
        <div className="flex-1 min-w-0 h-8 flex items-center">
          {captionText ? (
            <p className="text-gray-800 text-xs text-center w-full line-clamp-2 leading-4" title={captionText}>
              {captionText}
            </p>
          ) : (
            <p className="text-gray-400 text-xs text-center w-full">
              {currentSlide + 1} / {totalSlides}
            </p>
          )}
        </div>
        <button
          onClick={onNext}
          disabled={currentSlide >= totalSlides - 1}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-30 transition-all flex-shrink-0"
        >
          Next →
        </button>
      </div>
    </div>
  );
}
