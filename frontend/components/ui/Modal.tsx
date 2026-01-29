'use client';

import { ReactNode, useEffect, useRef, useCallback } from "react";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  showCloseButton?: boolean;
  /** Optional: Custom aria-label for the modal */
  ariaLabel?: string;
  /** Optional: ID for aria-describedby */
  ariaDescribedBy?: string;
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  showCloseButton = true,
  ariaLabel,
  ariaDescribedBy,
}: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedElement = useRef<HTMLElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // Focus trap - get all focusable elements
  const getFocusableElements = useCallback(() => {
    if (!modalRef.current) return [];
    return Array.from(
      modalRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input:not([type="hidden"]), select, textarea, [tabindex]:not([tabindex="-1"])'
      )
    ).filter(el => !el.hasAttribute('disabled') && el.offsetParent !== null);
  }, []);

  // Handle keyboard events
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      // Handle Escape
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }

      // Handle Tab for focus trapping
      if (e.key === 'Tab') {
        const focusableElements = getFocusableElements();
        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
          // Shift + Tab
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          // Tab
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose, getFocusableElements]);

  // Manage focus on open/close
  useEffect(() => {
    if (isOpen) {
      // Store currently focused element
      previouslyFocusedElement.current = document.activeElement as HTMLElement;

      // Lock body scroll
      document.body.style.overflow = 'hidden';

      // Focus the close button or first focusable element
      requestAnimationFrame(() => {
        if (closeButtonRef.current) {
          closeButtonRef.current.focus();
        } else {
          const focusableElements = getFocusableElements();
          if (focusableElements.length > 0) {
            focusableElements[0].focus();
          }
        }
      });
    } else {
      // Restore focus to previously focused element
      if (previouslyFocusedElement.current) {
        previouslyFocusedElement.current.focus();
      }
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, getFocusableElements]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-[95vw] md:max-w-[90vw]',
  };

  const modalId = `modal-${title.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto"
      role="presentation"
    >
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Container */}
      <div className="flex min-h-full items-center justify-center p-3 md:p-4 text-center">
        <div
          ref={modalRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={`${modalId}-title`}
          aria-describedby={ariaDescribedBy}
          aria-label={ariaLabel}
          className={`
            relative transform overflow-hidden rounded-xl md:rounded-lg bg-white text-left shadow-xl
            transition-all w-full ${sizeClasses[size]}
            max-h-[90vh] flex flex-col
          `}
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 md:px-6 py-3 md:py-4 border-b border-gray-200 flex-shrink-0">
            <h3
              id={`${modalId}-title`}
              className="text-base md:text-lg font-semibold text-gray-900"
            >
              {title}
            </h3>
            {showCloseButton && (
              <button
                ref={closeButtonRef}
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 rounded-md p-2 min-h-[44px] min-w-[44px] flex items-center justify-center -mr-2"
                aria-label="Fermer la fenêtre"
              >
                <svg className="h-5 w-5 md:h-6 md:w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {/* Content - Scrollable */}
          <div className="px-4 md:px-6 py-3 md:py-4 overflow-y-auto flex-1">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
