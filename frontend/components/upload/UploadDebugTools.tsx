'use client';

import { useEffect } from 'react';
import { ImportPhase, PhaseState } from '../../hooks/useFileUpload';
import { useFileAnalysis } from '../../hooks/useFileAnalysis';

interface UploadDebugToolsProps {
  file: File | null;
  loading: boolean;
  phases: Record<ImportPhase, PhaseState>;
  currentPhase: ImportPhase;
  isAuthenticated: boolean;
}

export function UploadDebugTools({
  file,
  loading,
  phases,
  currentPhase,
  isAuthenticated
}: UploadDebugToolsProps) {
  const { logFileAnalysis } = useFileAnalysis();

  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      (window as any).debugCSVImport = {
        getCurrentState: () => ({
          file: file ? {
            name: file.name,
            size: file.size,
            type: file.type,
            lastModified: new Date(file.lastModified).toISOString()
          } : null,
          loading,
          phases,
          currentPhase,
          isAuthenticated,
          authToken: localStorage.getItem("auth_token")?.substring(0, 10) + "...",
          tokenType: localStorage.getItem("token_type"),
          currentUrl: window.location.href
        }),
        testAuthHeaders: () => {
          const token = localStorage.getItem("auth_token");
          const tokenType = localStorage.getItem("token_type");
          console.log("🔑 Current auth state:", {
            hasToken: !!token,
            tokenLength: token?.length,
            tokenType,
            tokenPreview: token?.substring(0, 10) + "...",
            isAuthenticated,
            apiDefaults: (window as any).api?.defaults?.headers?.common
          });
        },
        analyzeCurrentFile: file ? () => logFileAnalysis(file) : () => console.log("No file selected")
      };
      
      console.log("🛠️ Debug tools available: window.debugCSVImport");
    }
  }, [file, loading, phases, currentPhase, isAuthenticated, logFileAnalysis]);

  return null; // This component doesn't render anything
}