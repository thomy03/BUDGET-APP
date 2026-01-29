'use client';

import { useEffect, useRef } from 'react';
import { formatTimeRemaining } from '../../hooks/useInactivityTimeout';

interface InactivityWarningModalProps {
  /** Whether the modal is visible */
  isOpen: boolean;
  /** Remaining time in seconds before automatic logout */
  remainingSeconds: number;
  /** Callback when user wants to continue the session */
  onContinue: () => void;
  /** Callback when user wants to logout now */
  onLogout: () => void;
}

export function InactivityWarningModal({
  isOpen,
  remainingSeconds,
  onContinue,
  onLogout,
}: InactivityWarningModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const continueButtonRef = useRef<HTMLButtonElement>(null);

  // Focus the continue button when modal opens
  useEffect(() => {
    if (isOpen && continueButtonRef.current) {
      continueButtonRef.current.focus();
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onContinue();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onContinue]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const isUrgent = remainingSeconds <= 30;
  const progressPercent = Math.min(100, (remainingSeconds / 120) * 100); // 120 seconds = warning time

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="inactivity-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onContinue}
      />

      {/* Modal */}
      <div
        ref={modalRef}
        className={`
          relative bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6
          transform transition-all duration-200 ease-out
          ${isUrgent ? 'ring-4 ring-red-500 ring-opacity-50 animate-pulse' : ''}
        `}
      >
        {/* Icon */}
        <div className="flex justify-center mb-4">
          <div className={`
            w-16 h-16 rounded-full flex items-center justify-center
            ${isUrgent ? 'bg-red-100' : 'bg-amber-100'}
          `}>
            <svg
              className={`w-8 h-8 ${isUrgent ? 'text-red-600' : 'text-amber-600'}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
        </div>

        {/* Title */}
        <h2
          id="inactivity-title"
          className="text-xl font-semibold text-center text-zinc-900 mb-2"
        >
          Session inactive
        </h2>

        {/* Description */}
        <p className="text-center text-zinc-600 mb-6">
          Vous allez etre deconnecte dans{' '}
          <span className={`font-bold ${isUrgent ? 'text-red-600' : 'text-amber-600'}`}>
            {formatTimeRemaining(remainingSeconds)}
          </span>{' '}
          pour des raisons de securite.
        </p>

        {/* Progress bar */}
        <div className="h-2 bg-zinc-200 rounded-full mb-6 overflow-hidden">
          <div
            className={`h-full transition-all duration-1000 rounded-full ${
              isUrgent ? 'bg-red-500' : 'bg-amber-500'
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Buttons */}
        <div className="flex gap-3">
          <button
            onClick={onLogout}
            className="flex-1 px-4 py-3 text-sm font-medium text-zinc-700 bg-zinc-100 rounded-lg hover:bg-zinc-200 transition-colors"
          >
            Se deconnecter
          </button>
          <button
            ref={continueButtonRef}
            onClick={onContinue}
            className={`
              flex-1 px-4 py-3 text-sm font-medium text-white rounded-lg transition-colors
              ${isUrgent ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'}
            `}
          >
            Continuer
          </button>
        </div>

        {/* Helper text */}
        <p className="text-xs text-center text-zinc-500 mt-4">
          Appuyez sur Echap ou cliquez hors du modal pour continuer
        </p>
      </div>
    </div>
  );
}
