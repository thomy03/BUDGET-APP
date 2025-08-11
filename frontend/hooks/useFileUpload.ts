'use client';

import { useState, useCallback, useRef } from 'react';

export type ImportPhase = 'upload' | 'parse' | 'validate' | 'import';

export type PhaseState = {
  status: 'pending' | 'active' | 'done' | 'error';
  progress: number;
};

// Configuration des durées pour chaque phase
const PHASE_DURATIONS: Record<ImportPhase, number> = {
  upload: 800,
  parse: 900,
  validate: 1000,
  import: 1100
};

const jitter = (ms: number, ratio = 0.15) => 
  Math.round(ms * (1 - ratio + Math.random() * ratio * 2));

const sleep = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms));

async function withMinDuration<T>(promise: Promise<T>, minMs: number): Promise<T> {
  const [result] = await Promise.all([promise, sleep(minMs)]);
  return result;
}

function smoothProgress(
  updateFn: (progress: number) => void,
  durationMs: number,
  cap = 93
) {
  let rafId = 0;
  let lastProgress = 0;
  const startTime = performance.now();
  
  const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
  
  const tick = (now: number) => {
    const elapsed = now - startTime;
    const t = Math.min(1, elapsed / durationMs);
    lastProgress = Math.min(cap, Math.round(easeOutCubic(t) * cap));
    updateFn(lastProgress);
    
    if (t < 1) {
      rafId = requestAnimationFrame(tick);
    }
  };
  
  rafId = requestAnimationFrame(tick);
  
  return (finishMs = 250) => {
    cancelAnimationFrame(rafId);
    const from = lastProgress;
    const startFinish = performance.now();
    
    const finish = (now: number) => {
      const t = Math.min(1, (now - startFinish) / finishMs);
      const progress = Math.round(from + t * (100 - from));
      updateFn(progress);
      
      if (t < 1) {
        requestAnimationFrame(finish);
      }
    };
    
    requestAnimationFrame(finish);
  };
}

export async function runPhase<T>(
  phase: ImportPhase,
  task: () => Promise<T> | T,
  setPhase: (phase: ImportPhase, data: Partial<PhaseState>) => void,
  baseMs = PHASE_DURATIONS[phase]
): Promise<T> {
  const minMs = jitter(baseMs);
  
  setPhase(phase, { status: 'active', progress: 0 });
  
  const stopProgress = smoothProgress(
    (progress) => setPhase(phase, { status: 'active', progress }),
    Math.max(minMs - 200, 200)
  );
  
  try {
    const result = await withMinDuration(Promise.resolve(task()), minMs);
    stopProgress(250);
    setPhase(phase, { status: 'done', progress: 100 });
    return result;
  } catch (error) {
    stopProgress(150);
    setPhase(phase, { status: 'error', progress: 100 });
    throw error;
  }
}

export function useImportPhases() {
  const [phases, setPhases] = useState<Record<ImportPhase, PhaseState>>({
    upload: { status: 'pending', progress: 0 },
    parse: { status: 'pending', progress: 0 },
    validate: { status: 'pending', progress: 0 },
    import: { status: 'pending', progress: 0 }
  });
  
  const [currentPhase, setCurrentPhase] = useState<ImportPhase>('upload');
  const rafRef = useRef<number | undefined>(undefined);
  
  const setPhase = useCallback((phase: ImportPhase, data: Partial<PhaseState>) => {
    setPhases(prev => ({ 
      ...prev, 
      [phase]: { ...prev[phase], ...data } 
    }));
    if (data.status === 'active') {
      setCurrentPhase(phase);
    }
  }, []);
  
  const reset = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
    }
    setPhases({
      upload: { status: 'pending', progress: 0 },
      parse: { status: 'pending', progress: 0 },
      validate: { status: 'pending', progress: 0 },
      import: { status: 'pending', progress: 0 }
    });
    setCurrentPhase('upload');
  }, []);
  
  return { phases, currentPhase, setPhase, reset };
}

export function useFileUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  
  const clearFile = useCallback(() => setFile(null), []);
  
  return {
    file,
    setFile,
    loading,
    setLoading,
    clearFile
  };
}