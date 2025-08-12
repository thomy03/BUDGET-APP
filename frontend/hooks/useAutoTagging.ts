'use client';

import { useState, useCallback, useRef } from 'react';
import { api } from '../lib/api';

interface AutoTaggingStats {
  totalTransactions: number;
  processed: number;
  successfullyTagged: number;
  skippedLowConfidence: number;
  fixedClassifications: number;
  variableClassifications: number;
  newTagsCreated: string[];
  processingTimeMs: number;
  estimatedTimeRemainingMs?: number;
}

interface AutoTaggingResult {
  id: number;
  label: string;
  amount: number;
  previousTags: string[];
  newTags: string[];
  classification: 'fixed' | 'variable';
  confidence: number;
  isNewClassification: boolean;
}

interface BatchAutoTagResponse {
  batch_id: string;
  status: string;
  message: string;
  total_transactions: number;
  estimated_duration_minutes: number;
}

interface BatchProgressResponse {
  batch_id: string;
  status: string;
  progress: number;
  total_transactions: number;
  processed_transactions: number;
  tagged_transactions: number;
  skipped_low_confidence: number;
  errors_count: number;
  current_operation?: string;
  processing_speed_per_minute?: number;
  estimated_time_remaining_minutes?: number;
}

interface UseAutoTaggingReturn {
  // State
  isProcessing: boolean;
  progress: number;
  stats: AutoTaggingStats;
  results: AutoTaggingResult[];
  error: string | null;
  jobId: string | null;
  
  // UI State
  showProgressModal: boolean;
  showResultsModal: boolean;
  
  // Actions
  startAutoTagging: (month: string, options?: {
    confidenceThreshold?: number;
    includeClassified?: boolean;
    limit?: number;
  }) => Promise<void>;
  cancelAutoTagging: () => Promise<void>;
  confirmResults: (approvedResults: AutoTaggingResult[]) => Promise<void>;
  dismissResults: () => void;
  closeProgressModal: () => void;
  retryAutoTagging: () => Promise<void>;
  
  // Utils
  getUntaggedCount: (transactions: any[]) => number;
  resetState: () => void;
}

export function useAutoTagging(): UseAutoTaggingReturn {
  // Core state
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stats, setStats] = useState<AutoTaggingStats>({
    totalTransactions: 0,
    processed: 0,
    successfullyTagged: 0,
    skippedLowConfidence: 0,
    fixedClassifications: 0,
    variableClassifications: 0,
    newTagsCreated: [],
    processingTimeMs: 0
  });
  const [results, setResults] = useState<AutoTaggingResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  
  // UI state
  const [showProgressModal, setShowProgressModal] = useState(false);
  const [showResultsModal, setShowResultsModal] = useState(false);
  
  // Refs for cleanup
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastOptionsRef = useRef<{
    month: string;
    confidenceThreshold?: number;
    includeClassified?: boolean;
    limit?: number;
  } | null>(null);

  // Cleanup polling
  const clearPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  // Poll job status
  const pollJobStatus = useCallback(async (currentBatchId: string) => {
    try {
      const response = await api.get<BatchProgressResponse>(`/api/auto-tag/progress/${currentBatchId}`);
      const data = response.data;
      
      // Update progress
      setProgress(data.progress);
      
      // Update stats based on progress response
      setStats(prev => ({
        ...prev,
        totalTransactions: data.total_transactions,
        processed: data.processed_transactions,
        successfullyTagged: data.tagged_transactions,
        skippedLowConfidence: data.skipped_low_confidence,
        estimatedTimeRemainingMs: data.estimated_time_remaining_minutes ? data.estimated_time_remaining_minutes * 60 * 1000 : undefined
      }));
      
      // Handle completion
      if (data.status === 'completed') {
        clearPolling();
        setIsProcessing(false);
        setProgress(100);
        setShowProgressModal(false);
        
        // For now, we'll close the modal and trigger a refresh
        // In the future, we could show a results modal
        console.log('✅ Auto-tagging completed successfully');
      }
      
      // Handle failure
      if (data.status === 'failed') {
        clearPolling();
        setIsProcessing(false);
        setError('Une erreur est survenue pendant le traitement');
        console.error('❌ Auto-tagging failed');
      }
      
    } catch (err: any) {
      console.error('❌ Error polling batch status:', err);
      
      // Stop polling on persistent errors
      clearPolling();
      setIsProcessing(false);
      setError('Erreur de communication avec le serveur');
    }
  }, [clearPolling]);

  // Start auto-tagging process
  const startAutoTagging = useCallback(async (
    month: string,
    options: {
      confidenceThreshold?: number;
      includeClassified?: boolean;
      limit?: number;
    } = {}
  ) => {
    try {
      // Reset state
      setError(null);
      setResults([]);
      setProgress(0);
      setIsProcessing(true);
      setShowProgressModal(true);
      setShowResultsModal(false);
      
      // Store options for retry
      lastOptionsRef.current = { month, ...options };
      
      console.log('🚀 Starting auto-tagging for month:', month, 'with options:', options);
      
      // Start the batch processing job using the correct API endpoint
      const response = await api.post<BatchAutoTagResponse>('/api/auto-tag/batch', {
        month,
        confidence_threshold: options.confidenceThreshold || 0.7,
        force_retag: options.includeClassified || false,
        include_fixed_variable: true
      });
      
      const data = response.data;
      setJobId(data.batch_id);
      
      // Initialize stats with total transactions
      setStats(prev => ({
        ...prev,
        totalTransactions: data.total_transactions,
        estimatedTimeRemainingMs: data.estimated_duration_minutes * 60 * 1000
      }));
      
      console.log('📋 Auto-tagging batch started with ID:', data.batch_id);
      
      // Start polling for updates
      pollingIntervalRef.current = setInterval(() => {
        pollJobStatus(data.batch_id);
      }, 2000); // Poll every 2 seconds
      
    } catch (err: any) {
      console.error('❌ Failed to start auto-tagging:', err);
      
      setIsProcessing(false);
      setShowProgressModal(false);
      
      let errorMessage = 'Impossible de démarrer la classification automatique';
      if (err?.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err?.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
    }
  }, [pollJobStatus]);

  // Cancel auto-tagging
  const cancelAutoTagging = useCallback(async () => {
    if (!jobId) return;
    
    try {
      console.log('⏹️ Cancelling auto-tagging batch:', jobId);
      
      await api.delete(`/api/auto-tag/batch/${jobId}`);
      
      clearPolling();
      setIsProcessing(false);
      setShowProgressModal(false);
      setJobId(null);
      
    } catch (err: any) {
      console.error('❌ Failed to cancel auto-tagging:', err);
      // Even if cancellation fails, stop the UI
      clearPolling();
      setIsProcessing(false);
      setShowProgressModal(false);
    }
  }, [jobId, clearPolling]);

  // Confirm and apply results
  const confirmResults = useCallback(async (approvedResults: AutoTaggingResult[]) => {
    try {
      console.log('✅ Confirming', approvedResults.length, 'auto-tagging results');
      
      if (approvedResults.length > 0) {
        // Apply the approved results
        await api.post('/auto-tagging/apply-results', {
          job_id: jobId,
          approved_results: approvedResults.map(r => r.id)
        });
      }
      
      setShowResultsModal(false);
      setJobId(null);
      
      // Trigger a refresh of the transactions list
      // This will be handled by the parent component
      
    } catch (err: any) {
      console.error('❌ Failed to apply auto-tagging results:', err);
      setError('Erreur lors de l\'application des résultats');
    }
  }, [jobId]);

  // Dismiss results without applying
  const dismissResults = useCallback(() => {
    setShowResultsModal(false);
    setJobId(null);
    setResults([]);
  }, []);

  // Close progress modal
  const closeProgressModal = useCallback(() => {
    if (!isProcessing) {
      setShowProgressModal(false);
    }
  }, [isProcessing]);

  // Retry auto-tagging with last options
  const retryAutoTagging = useCallback(async () => {
    if (!lastOptionsRef.current) return;
    
    const { month, ...options } = lastOptionsRef.current;
    await startAutoTagging(month, options);
  }, [startAutoTagging]);

  // Get count of untagged transactions
  const getUntaggedCount = useCallback((transactions: any[]): number => {
    return transactions.filter(tx => {
      const isExpense = tx.amount < 0;
      const hasMinimalTags = Array.isArray(tx.tags) 
        ? tx.tags.length > 0 && tx.tags.some((tag: string) => tag.trim().length > 0)
        : (tx.tags || '').trim().length > 0;
      const hasClassification = tx.expense_type && ['fixed', 'variable'].includes(tx.expense_type);
      
      // Transaction needs tagging if it's an expense without proper tags or classification
      return isExpense && (!hasMinimalTags || !hasClassification);
    }).length;
  }, []);

  // Reset all state
  const resetState = useCallback(() => {
    clearPolling();
    setIsProcessing(false);
    setProgress(0);
    setStats({
      totalTransactions: 0,
      processed: 0,
      successfullyTagged: 0,
      skippedLowConfidence: 0,
      fixedClassifications: 0,
      variableClassifications: 0,
      newTagsCreated: [],
      processingTimeMs: 0
    });
    setResults([]);
    setError(null);
    setJobId(null);
    setShowProgressModal(false);
    setShowResultsModal(false);
    lastOptionsRef.current = null;
  }, [clearPolling]);

  // Cleanup on unmount
  // This would typically be handled by the component using this hook

  return {
    // State
    isProcessing,
    progress,
    stats,
    results,
    error,
    jobId,
    
    // UI State
    showProgressModal,
    showResultsModal,
    
    // Actions
    startAutoTagging,
    cancelAutoTagging,
    confirmResults,
    dismissResults,
    closeProgressModal,
    retryAutoTagging,
    
    // Utils
    getUntaggedCount,
    resetState
  };
}