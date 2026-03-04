/**
 * Overlay shown on mobile portrait orientation asking user to rotate device.
 * The calendar requires landscape orientation for optimal viewing.
 */
"use client";

export function MobileRotatePrompt() {
  return (
    <div className="fixed inset-0 bg-white z-50 flex flex-col items-center justify-center p-8 md:hidden landscape:hidden">
      <svg
        className="w-16 h-16 text-blue-500 mb-4 animate-spin-slow"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
        />
      </svg>
      <h2 className="text-xl font-bold text-gray-900 mb-2">
        Поверните устройство
      </h2>
      <p className="text-gray-500 text-center">
        Для удобного просмотра календаря тренировок переведите устройство в
        горизонтальный режим.
      </p>
    </div>
  );
}
