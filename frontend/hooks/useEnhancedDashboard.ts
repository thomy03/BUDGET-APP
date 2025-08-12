'use client';

import { useState, useEffect } from 'react';
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

export function useEnhancedDashboard(month: string, isAuthenticated: boolean) {
  const [data, setData] = useState<EnhancedSummaryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadEnhancedData = async () => {
    if (!isAuthenticated) return;
    
    console.log('📊 Enhanced Dashboard - Loading data for month:', month);
    try {
      setLoading(true);
      setError("");
      
      const response = await api.get<EnhancedSummaryData>("/summary/enhanced", { params: { month } });
      
      console.log('✅ Enhanced Dashboard - Data loaded for month:', month);
      setData(response.data);
    } catch (err: any) {
      setError("Erreur lors du chargement des données enhanced");
      console.error("❌ Enhanced Dashboard - Load error:", err);
    } finally {
      setLoading(false);
    }
  };

  const convertExpenseType = async (transactionId: number, newType: 'FIXED' | 'VARIABLE' | 'PROVISION'): Promise<boolean> => {
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

  const bulkConvertExpenseType = async (transactionIds: number[], newType: 'FIXED' | 'VARIABLE' | 'PROVISION'): Promise<boolean> => {
    if (!isAuthenticated || transactionIds.length === 0) return false;
    
    try {
      console.log(`🔄 Bulk converting ${transactionIds.length} transactions to type: ${newType}`);
      
      // Conversion en parallèle pour de meilleures performances
      const promises = transactionIds.map(id => 
        api.patch(`/transactions/${id}/expense-type`, { expense_type: newType })
      );
      
      await Promise.all(promises);
      
      console.log(`✅ Bulk conversion completed: ${transactionIds.length} transactions → ${newType}`);
      
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
  }, [month, isAuthenticated]);

  return {
    data,
    loading,
    error,
    reload: loadEnhancedData,
    convertExpenseType,
    bulkConvertExpenseType
  };
}