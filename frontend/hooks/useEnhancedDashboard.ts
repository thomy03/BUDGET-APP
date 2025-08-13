'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

// Types pour l'endpoint enhanced
export interface EnhancedSummaryData {
  month: string;
  member1: string;
  member2: string;
  split_ratio: {
    member1: number;
    member2: number;
  };
  revenues: {
    member1_revenue: number;
    member2_revenue: number;
    total_revenue: number;
    provision_needed: number;
  };
  savings: {
    total: number;
    member1_total: number;
    member2_total: number;
    count: number;
    detail: SavingsDetail[];
  };
  fixed_expenses: {
    total: number;
    member1_total: number;
    member2_total: number;
    count: number;
    detail: FixedExpenseDetail[];
  };
  variables: {
    total: number;
    member1_total: number;
    member2_total: number;
    tagged_count: number;
    untagged_count: number;
    total_transactions: number;
    detail: VariableDetail[];
  };
  totals: {
    grand_total: number;
    member1_total: number;
    member2_total: number;
    total_expenses: number;
  };
  metadata: {
    active_provisions: number;
    active_fixed_expenses: number;
    unique_tags: number;
    calculation_timestamp: string;
  };
}

export interface SavingsDetail {
  name: string;
  icon: string;
  color: string;
  monthly_amount: number;
  member1_amount: number;
  member2_amount: number;
  type: 'provision';
}

export interface FixedExpenseDetail {
  name: string;
  monthly_amount: number;
  member1_amount: number;
  member2_amount: number;
  category: string;
  type: 'fixed';
  source: 'manual' | 'ai_classified';
  icon: string;
  tag?: string;
}

export interface VariableDetail {
  name: string;
  tag: string | null;
  amount: number;
  member1_amount: number;
  member2_amount: number;
  transaction_count: number;
  type: 'tagged_variable' | 'untagged_variable';
  transaction_ids?: number[]; // Pour identifier les transactions à convertir
}

export function useEnhancedDashboard(month: string, isAuthenticated: boolean = false) {
  // Comprehensive validation for input parameters
  if (!month || typeof month !== 'string') {
    console.warn('Invalid month parameter provided to useEnhancedDashboard');
    month = new Date().toISOString().slice(0, 7); // Default to current month
  }
  const [data, setData] = useState<EnhancedSummaryData | null>(null);
  // Initialize data with a safe default structure to prevent undefined errors
  const defaultData: EnhancedSummaryData = {
    month: '',
    member1: '',
    member2: '',
    split_ratio: { member1: 0, member2: 0 },
    revenues: { 
      member1_revenue: 0, 
      member2_revenue: 0, 
      total_revenue: 0, 
      provision_needed: 0 
    },
    savings: { 
      total: 0, 
      member1_total: 0, 
      member2_total: 0, 
      count: 0, 
      detail: [] 
    },
    fixed_expenses: { 
      total: 0, 
      member1_total: 0, 
      member2_total: 0, 
      count: 0, 
      detail: [] 
    },
    variables: { 
      total: 0, 
      member1_total: 0, 
      member2_total: 0, 
      tagged_count: 0, 
      untagged_count: 0, 
      total_transactions: 0, 
      detail: [] 
    },
    totals: { 
      grand_total: 0, 
      member1_total: 0, 
      member2_total: 0, 
      total_expenses: 0 
    },
    metadata: { 
      active_provisions: 0, 
      active_fixed_expenses: 0, 
      unique_tags: 0, 
      calculation_timestamp: new Date().toISOString() 
    }
  };
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadEnhancedData = async (): Promise<void> => {
    // Implement comprehensive error handling
    const performDataLoad = async () => {
    if (!isAuthenticated) return;
    
    console.log('📊 Enhanced Dashboard - Loading data for month:', month);
    try {
      setLoading(true);
      setError("");
      
      // Type-safe and defensive data fetching
      const response = await api.get<EnhancedSummaryData>("/summary/enhanced", { 
        params: { 
          month: month || new Date().toISOString().slice(0, 7) 
        },
        transformResponse: [
          (data) => {
            try {
              const parsedData = JSON.parse(data);
              // Return parsed data or default if invalid
              return parsedData || defaultData;
            } catch {
              console.warn('Invalid data structure received');
              return defaultData;
            }
          }
        ]
      });
      
      console.log('✅ Enhanced Dashboard - Data loaded for month:', month);
      setData(response.data);
    } catch (err: any) {
      setError("Erreur lors du chargement des données enhanced");
      console.error("❌ Enhanced Dashboard - Load error:", err);
    } finally {
      setLoading(false);
    }
  };

  const convertExpenseType = async (
    transactionId: number, 
    newType: 'FIXED' | 'VARIABLE' | 'PROVISION'
  ): Promise<boolean> => {
    // Defensive input validation
    if (!transactionId || typeof transactionId !== 'number') {
      console.warn('Invalid transactionId provided');
      return false;
    }

    const validTypes: Record<string, boolean> = {
      'FIXED': true,
      'VARIABLE': true,
      'PROVISION': true
    };

    if (!validTypes[newType]) {
      console.warn(`Invalid expense type: ${newType}`);
      return false;
    }
    if (!isAuthenticated) return false;
    
    try {
      console.log(`🔄 Converting transaction ${transactionId} to type: ${newType}`);
      
      await api.patch(`/transactions/${transactionId}/expense-type`, {
        expense_type: newType
      });
      
      console.log(`✅ Transaction ${transactionId} converted to ${newType}`);
      
      // Rechargement automatique des données pour refléter les changements
      await loadEnhancedData();
      return true;
      
    } catch (err: any) {
      console.error(`❌ Error converting transaction ${transactionId} to ${newType}:`, err);
      setError(`Erreur lors de la conversion: ${err.response?.data?.detail || err.message}`);
      return false;
    }
  };

  const bulkConvertExpenseType = async (
    transactionIds: number[], 
    newType: 'FIXED' | 'VARIABLE' | 'PROVISION'
  ): Promise<boolean> => {
    // Comprehensive validation for bulk conversion
    if (!Array.isArray(transactionIds) || transactionIds.length === 0) {
      console.warn('Invalid or empty transactionIds array');
      return false;
    }

    const validTypes: Record<string, boolean> = {
      'FIXED': true,
      'VARIABLE': true,
      'PROVISION': true
    };

    if (!validTypes[newType]) {
      console.warn(`Invalid bulk conversion type: ${newType}`);
      return false;
    }

    if (!isAuthenticated || transactionIds.length === 0) return false;
    
    // Limit bulk conversion to prevent performance issues
    const MAX_BULK_CONVERSION = 50;
    const safeTransactionIds = transactionIds.slice(0, MAX_BULK_CONVERSION);
    
    try {
      console.log(`🔄 Bulk converting ${safeTransactionIds.length} transactions to type: ${newType}`);
      
      // Conversion en parallèle pour de meilleures performances
      const promises = safeTransactionIds.map(id => 
        api.patch(`/transactions/${id}/expense-type`, { expense_type: newType })
      );
      
      await Promise.all(promises);
      
      console.log(`✅ Bulk conversion completed: ${safeTransactionIds.length} transactions → ${newType}`);
      
      // Rechargement automatique des données
      await loadEnhancedData();
      return true;
      
    } catch (err: any) {
      console.error(`❌ Error in bulk conversion to ${newType}:`, err);
      setError(`Erreur lors de la conversion groupée: ${err.response?.data?.detail || err.message}`);
      return false;
    }
  };

  useEffect(() => {
    console.log('🔄 Enhanced Dashboard useEffect - Month:', month, 'Auth:', isAuthenticated);
    if (isAuthenticated) {
      loadEnhancedData();
    }
  }, [month, isAuthenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    data,
    loading,
    error,
    reload: loadEnhancedData,
    convertExpenseType,
    bulkConvertExpenseType
  };
}
