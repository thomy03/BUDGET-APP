'use client';

import { useState } from 'react';
import { SparklesIcon } from '@heroicons/react/24/outline';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface UnifiedSmartTagProps {
  transaction: {
    id: number;
    label: string;
    amount: number;
    tags?: string;
  };
  onTagsSelected: (tags: string[]) => Promise<void>;
}

interface AlternativeSuggestion {
  tag?: string;
}

export function UnifiedSmartTag({ transaction, onTagsSelected }: UnifiedSmartTagProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [confidence, setConfidence] = useState(0);
  const [source, setSource] = useState('');
  const [originalSuggestion, setOriginalSuggestion] = useState<string | null>(null);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('auth_token');
    const tokenType = localStorage.getItem('token_type') || 'Bearer';
    return {
      'Content-Type': 'application/json',
      'Authorization': token ? tokenType + ' ' + token : ''
    };
  };

  const handleSmartTag = async () => {
    if (isLoading) return;

    setIsLoading(true);

    try {
      const response = await fetch(API_URL + '/api/ml-classification/classify', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          transaction_label: transaction.label,
          amount: transaction.amount,
          include_alternatives: true,
          confidence_threshold: 0.3
        })
      });

      if (response.ok) {
        const result = await response.json();

        // Adapter la reponse du nouveau endpoint ML
        const allSuggestions: string[] = [];
        if (result.suggested_tag) {
          allSuggestions.push(result.suggested_tag);
        }
        // Ajouter les alternatives
        if (result.alternative_suggestions) {
          result.alternative_suggestions.forEach((alt: AlternativeSuggestion) => {
            if (alt.tag && !allSuggestions.includes(alt.tag)) {
              allSuggestions.push(alt.tag);
            }
          });
        }

        if (allSuggestions.length > 0) {
          setSuggestions(allSuggestions);
          setConfidence(result.confidence || 0);
          setSource(result.feedback_pattern_used ? 'pattern' : (result.source || 'transformer'));
          setOriginalSuggestion(allSuggestions[0]);
        }
      }
    } catch (error) {
      console.error('Erreur Smart Tag:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMLFeedback = async (selectedTag: string) => {
    try {
      const feedbackType = originalSuggestion === selectedTag ? 'acceptance' : 'correction';

      await fetch(API_URL + '/api/ml-feedback/', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          transaction_id: transaction.id,
          original_tag: originalSuggestion || transaction.tags || null,
          corrected_tag: selectedTag,
          feedback_type: feedbackType,
          confidence_before: confidence
        })
      });

      console.log('ML Feedback envoye: ' + feedbackType + ' - ' + selectedTag);
    } catch (error) {
      console.warn('Erreur envoi ML feedback (non bloquant):', error);
    }
  };

  const handleApplyTag = async (tag: string) => {
    await onTagsSelected([tag]);
    sendMLFeedback(tag);
    setSuggestions([]);
    setOriginalSuggestion(null);
  };

  const getSourceIcon = () => {
    switch(source) {
      case 'transformer': return String.fromCodePoint(0x1F916);
      case 'web': return String.fromCodePoint(0x1F310);
      case 'pattern': return String.fromCodePoint(0x1F4D0);
      case 'feedback': return String.fromCodePoint(0x1F4D0);
      default: return String.fromCodePoint(0x2728);
    }
  };

  const getSourceLabel = () => {
    switch(source) {
      case 'transformer': return 'IA Avancee';
      case 'web': return 'Recherche Web';
      case 'pattern': return 'Appris';
      case 'feedback': return 'Appris';
      default: return 'Smart Tag';
    }
  };

  return (
    <div className="inline-flex flex-col gap-2">
      <button
        onClick={handleSmartTag}
        disabled={isLoading}
        className={'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ' + 
          (isLoading
            ? 'bg-gray-100 text-gray-400 cursor-wait'
            : 'bg-gradient-to-r from-purple-500 to-blue-500 text-white hover:from-purple-600 hover:to-blue-600 shadow-sm hover:shadow-md'
          )
        }
      >
        {isLoading ? (
          <>
            <div className="w-4 h-4 border-2 border-gray-300 border-t-transparent rounded-full animate-spin" />
            <span>Analyse...</span>
          </>
        ) : (
          <>
            <SparklesIcon className="w-4 h-4" />
            <span>Smart Tag</span>
          </>
        )}
      </button>

      {suggestions.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-2 shadow-sm dark:bg-gray-800 dark:border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1">
              <span className="text-lg">{getSourceIcon()}</span>
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{getSourceLabel()}</span>
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {Math.round(confidence * 100)}% confiance
            </span>
          </div>

          <div className="flex flex-wrap gap-1">
            {suggestions.map((tag, index) => (
              <button
                key={index}
                onClick={() => handleApplyTag(tag)}
                className={'px-2 py-1 text-xs font-medium rounded-md transition-all duration-150 hover:shadow-sm cursor-pointer ' +
                  (confidence > 0.7
                    ? 'bg-green-100 text-green-800 hover:bg-green-200 border border-green-300 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800'
                    : confidence > 0.4
                    ? 'bg-amber-100 text-amber-800 hover:bg-amber-200 border border-amber-300 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600'
                  )
                }
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
