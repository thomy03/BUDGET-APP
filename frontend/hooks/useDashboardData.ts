'use client';

import { useState, useEffect } from 'react';
import { api, Summary, ConfigOut, CustomProvision, FixedLine, provisionsApi, fixedExpensesApi } from '../lib/api';

export interface DashboardData {
  summary: Summary | null;
  config: ConfigOut | null;
  provisions: CustomProvision[];
  fixedExpenses: FixedLine[];
}

export function useDashboardData(month: string, isAuthenticated: boolean) {
  const [data, setData] = useState<DashboardData>({
    summary: null,
    config: null,
    provisions: [],
    fixedExpenses: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadData = async () => {
    if (!isAuthenticated) return;
    
    console.log('📊 Dashboard - Loading data for month:', month);
    try {
      setLoading(true);
      setError("");
      
      const [configResponse, summaryResponse, provisions, fixedExpenses] = await Promise.all([
        api.get<ConfigOut>("/config"),
        api.get<Summary>("/summary", { params: { month } }),
        provisionsApi.getAll(),
        fixedExpensesApi.getAll()
      ]);
      
      console.log('✅ Dashboard - Data loaded for month:', month);
      setData({
        summary: summaryResponse.data,
        config: configResponse.data,
        provisions: provisions,
        fixedExpenses: fixedExpenses
      });
    } catch (err: any) {
      setError("Erreur lors du chargement des données");
      console.error("❌ Dashboard - Load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log('🔄 Dashboard useEffect - Month:', month, 'Auth:', isAuthenticated);
    if (isAuthenticated) {
      loadData();
    }
  }, [month, isAuthenticated]);

  return {
    ...data,
    loading,
    error,
    reload: loadData
  };
}