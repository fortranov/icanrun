/**
 * Small dismissible banner shown on portrait mobile after login.
 * Prompts the user to rotate the device for the full calendar view.
 *
 * Behaviour:
 *  - Shows only once per session (sessionStorage flag set on first render).
 *  - Can be closed with the × button.
 *  - Navigating away and coming back keeps it hidden (flag already set).
 */
"use client";

import { useEffect, useState } from "react";

const SESSION_KEY = "rotatePromptSeen";

export function MobileRotatePrompt() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (sessionStorage.getItem(SESSION_KEY)) return;
    const isNarrow = window.innerWidth < 768;
    const isPortrait = window.innerHeight > window.innerWidth;
    if (isNarrow && isPortrait) {
      setVisible(true);
      // Mark as seen immediately — navigating away and back won't re-show it
      sessionStorage.setItem(SESSION_KEY, "1");
    }
  }, []);

  if (!visible) return null;

  return (
    <div className="md:hidden landscape:hidden mb-3">
      <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 flex items-center gap-3 shadow-sm">
        {/* Rotate phone icon */}
        <svg
          className="w-5 h-5 text-blue-500 flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3"
          />
        </svg>
        <p className="text-sm text-blue-700 flex-1">
          Поверните устройство горизонтально для просмотра полного календаря
        </p>
        <button
          type="button"
          onClick={() => setVisible(false)}
          className="text-blue-400 hover:text-blue-600 p-1 rounded transition-colors"
          aria-label="Закрыть"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
