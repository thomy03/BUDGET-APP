'use client';

import React, { useState, useCallback } from 'react';
import { aiApi } from '@/lib/api';

interface TransactionTipTooltipProps {
  transactionId: number;
  label: string;
  amount: number;
  category?: string;
  children: React.ReactNode;
}

export function TransactionTipTooltip({
  transactionId,
  label,
  amount,
  category,
  children
}: TransactionTipTooltipProps) {
  const [tip, setTip] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [hasError, setHasError] = useState(false);

  // Fetch tip on hover
  const fetchTip = useCallback(async () => {
    if (tip || loading || hasError) return;

    try {
      setLoading(true);

      // Ask AI about this transaction
      const response = await aiApi.askQuestion(
        `Donne un conseil court (max 2 phrases) pour cette transaction: "${label}" de ${Math.abs(amount)}€ ${category ? `(catégorie: ${category})` : ''}. Sois pratique et direct.`
      );

      setTip(response.answer || 'Aucun conseil disponible.');
    } catch (err) {
      console.error('Failed to fetch tip:', err);
      setHasError(true);
      setTip('Conseil non disponible pour le moment.');
    } finally {
      setLoading(false);
    }
  }, [transactionId, label, amount, category, tip, loading, hasError]);

  // Handle mouse enter
  const handleMouseEnter = () => {
    setIsOpen(true);
    fetchTip();
  };

  // Handle mouse leave
  const handleMouseLeave = () => {
    setIsOpen(false);
  };

  return (
    <div
      className="relative inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}

      {/* Tooltip */}
      {isOpen && (
        <div className="absolute z-50 left-0 top-full mt-2 w-64 transform -translate-x-1/4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3">
            {/* Arrow */}
            <div className="absolute -top-2 left-1/4 w-3 h-3 bg-white dark:bg-gray-800 border-l border-t border-gray-200 dark:border-gray-700 transform rotate-45" />

            {/* Content */}
            <div className="relative">
              {loading ? (
                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                  <span className="animate-spin">⏳</span>
                  Chargement du conseil...
                </div>
              ) : (
                <div className="flex items-start gap-2">
                  <span className="text-lg">💡</span>
                  <p className="text-sm text-gray-700 dark:text-gray-200">{tip}</p>
                </div>
              )}
            </div>

            {/* Category info */}
            {category && (
              <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Catégorie: <span className="capitalize font-medium">{category}</span>
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Simpler version that just shows info icon with tooltip trigger
interface TipIconProps {
  transactionId: number;
  label: string;
  amount: number;
  category?: string;
}

export function TransactionTipIcon({
  transactionId,
  label,
  amount,
  category
}: TipIconProps) {
  return (
    <TransactionTipTooltip
      transactionId={transactionId}
      label={label}
      amount={amount}
      category={category}
    >
      <button
        className="p-1 text-gray-400 hover:text-indigo-500 dark:hover:text-indigo-400 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        title="Obtenir un conseil IA"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
          />
        </svg>
      </button>
    </TransactionTipTooltip>
  );
}

export default TransactionTipTooltip;
