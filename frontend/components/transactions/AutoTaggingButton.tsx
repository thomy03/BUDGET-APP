'use client';

import { useState } from 'react';

interface AutoTaggingButtonProps {
  totalTransactions: number;
  untaggedCount: number;
  onStartAutoTagging: () => void;
  isProcessing?: boolean;
  progress?: number;
  processedCount?: number;
  statusMessage?: string;
}

export function AutoTaggingButton({
  totalTransactions,
  untaggedCount,
  onStartAutoTagging,
  isProcessing = false,
  progress = 0,
  processedCount = 0,
  statusMessage
}: AutoTaggingButtonProps) {
  const [isHovered, setIsHovered] = useState(false);

  const handleClick = () => {
    if (!isProcessing && untaggedCount > 0) {
      onStartAutoTagging();
    }
  };

  const getButtonText = () => {
    if (isProcessing) {
      return statusMessage || "Traitement en cours...";
    }
    if (untaggedCount === 0) {
      return "Toutes les transactions sont taguées";
    }
    return `🤖 Tagguer automatiquement (${untaggedCount} transactions)`;
  };

  return (
    <button
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      disabled={isProcessing || untaggedCount === 0}
      className={`
        px-6 py-3 rounded-lg font-medium transition-all duration-200
        ${isProcessing || untaggedCount === 0
          ? "bg-gray-300 text-gray-500 cursor-not-allowed"
          : "bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:from-blue-600 hover:to-purple-700 shadow-lg hover:shadow-xl"
        }
      `}
      title={untaggedCount === 0 ? "Aucune transaction à taguer" : `Taguer ${untaggedCount} transactions automatiquement`}
    >
      <span className="flex items-center gap-2">
        {isProcessing && (
          <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
        )}
        {getButtonText()}
      </span>
    </button>
  );
}