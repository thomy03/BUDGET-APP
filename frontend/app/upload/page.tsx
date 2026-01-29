'use client';

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../lib/auth";
import { LoadingSpinner } from "../../components/ui";
import { CsvImportProgress } from "../../components/CsvImportProgress";
import {
  FileSelector,
  UploadInstructions,
  UploadDebugTools,
  FilePreview,
  ImportPreviewModal
} from "../../components/upload";
import { useFileUpload, useImportPhases } from "../../hooks/useFileUpload";
import { useFileAnalysis } from "../../hooks/useFileAnalysis";
import { useUploadApi } from "../../hooks/useUploadApi";
import { useUploadErrorHandler } from "../../hooks/useUploadErrorHandler";

export default function UploadPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const { file, setFile, loading, setLoading, clearFile } = useFileUpload();
  const { phases, currentPhase, setPhase, reset } = useImportPhases();
  const { logFileAnalysis } = useFileAnalysis();
  const { uploadFile } = useUploadApi();
  const { handleUploadError } = useUploadErrorHandler();

  // État pour le modal de prévisualisation
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  // Redirection si non authentifié
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

  const onUpload = async () => {
    if (!file) return;
    
    console.log('🚀 Starting upload with animation...');
    
    // Analyser le fichier pour le débogage en mode développement
    if (process.env.NODE_ENV === "development") {
      await logFileAnalysis(file);
    }
    
    try {
      setLoading(true);
      reset();
      console.log('✅ Loading state set to true');
      
      await uploadFile(file, setPhase);
      
    } catch (err: any) {
      handleUploadError(err, file);
    } finally {
      setLoading(false);
      reset();
      clearFile(); // Reset le fichier après upload (succès ou échec)
    }
  };

  // Affichage du loader pendant l'authentification
  if (authLoading) {
    return (
      <div className="container py-12 flex justify-center">
        <LoadingSpinner size="lg" text="Chargement..." />
      </div>
    );
  }

  // Ne rien afficher si non authentifié
  if (!isAuthenticated) {
    return null;
  }

  return (
    <main className="container py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="h1">📥 Import de fichier</h1>
        <div className="text-sm text-zinc-500">
          <span className="mr-4">Formats acceptés: CSV, XLSX, XLS, PDF</span>
          <span>Max: 10MB</span>
        </div>
      </div>

      {/* Debug Tools (only in development) */}
      <UploadDebugTools
        file={file}
        loading={loading}
        phases={phases}
        currentPhase={currentPhase}
        isAuthenticated={isAuthenticated}
      />

      {loading ? (
        <>
          {console.log('CsvImportProgress:', {
            currentPhase,
            progress: phases[currentPhase].progress,
            fileName: file?.name
          })}
          <CsvImportProgress
            fileName={file?.name}
            progress={phases[currentPhase].progress}
            phase={currentPhase}
            cancellable={false}
            hint="L'analyse du fichier commencera après le téléversement. Veuillez patienter."
            fileSize={file?.size}
            estimatedLines={file ? Math.max(1, Math.floor(file.size / 50)) : undefined}
          />
        </>
      ) : (
        <>
          <FileSelector
            file={file}
            onFileChange={setFile}
            loading={loading}
            onUpload={onUpload}
          />

          {/* Bouton de prévisualisation */}
          {file && (
            <div className="flex justify-center">
              <button
                onClick={() => setShowPreviewModal(true)}
                className="px-6 py-3 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors flex items-center gap-2 font-medium"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                Prévisualiser avant import
              </button>
            </div>
          )}

          {/* Preview du fichier sélectionné */}
          <FilePreview file={file} />

          <UploadInstructions />
        </>
      )}

      {/* Modal de prévisualisation */}
      <ImportPreviewModal
        isOpen={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        file={file}
        onConfirmImport={() => {
          setShowPreviewModal(false);
          onUpload();
        }}
      />
    </main>
  );
}