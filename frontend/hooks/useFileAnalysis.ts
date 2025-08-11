'use client';

import { useCallback } from 'react';

export interface FileAnalysis {
  name: string;
  size: number;
  type: string;
  lastModified: string;
  sizeInMB: string;
  firstChars?: string;
  hasUTF8BOM?: boolean;
  lineCount?: number;
  delimiter?: string;
  encoding?: string;
}

export function useFileAnalysis() {
  const analyzeFile = useCallback(async (file: File): Promise<FileAnalysis | null> => {
    try {
      const analysis: FileAnalysis = {
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: new Date(file.lastModified).toISOString(),
        sizeInMB: (file.size / 1024 / 1024).toFixed(2)
      };

      // Lire les premiers caractères du fichier pour détecter l'encodage/format
      if (file.size > 0 && file.size < 10 * 1024 * 1024) { // Moins de 10MB
        const slice = file.slice(0, Math.min(1000, file.size));
        const text = await slice.text();
        
        analysis.firstChars = text.substring(0, 200);
        analysis.hasUTF8BOM = text.charCodeAt(0) === 0xFEFF;
        analysis.lineCount = text.split('\n').length;
        analysis.delimiter = text.includes(';') ? ';' : (text.includes(',') ? ',' : 'unknown');
        analysis.encoding = 'UTF-8'; // Par défaut, le navigateur lit en UTF-8
      }

      console.log("🔬 File Analysis:", analysis);
      return analysis;
    } catch (error) {
      console.warn("⚠️ Could not analyze file:", error);
      return null;
    }
  }, []);

  const logFileAnalysis = useCallback(async (file: File): Promise<void> => {
    await analyzeFile(file);
  }, [analyzeFile]);

  return { analyzeFile, logFileAnalysis };
}