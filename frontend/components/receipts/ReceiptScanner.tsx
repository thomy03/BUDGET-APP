'use client';

import { useState, useRef, useCallback } from 'react';
import { Card, Button, LoadingSpinner, Alert } from '../ui';
import { API_BASE } from '../../lib/api';

interface ScanResult {
  success: boolean;
  merchant: string | null;
  amount: number | null;
  date: string | null;
  suggested_tag: string | null;
  confidence: number;
  all_amounts: number[];
  raw_text: string;
  message: string;
}

interface ReceiptScannerProps {
  onTransactionCreated?: (transactionId: number) => void;
  className?: string;
}

export function ReceiptScanner({ onTransactionCreated, className = '' }: ReceiptScannerProps) {
  const [scanning, setScanning] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [showRawText, setShowRawText] = useState(false);

  // Editable fields
  const [editMerchant, setEditMerchant] = useState('');
  const [editAmount, setEditAmount] = useState('');
  const [editDate, setEditDate] = useState('');
  const [editTag, setEditTag] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  const getAuthToken = () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('token');
    }
    return null;
  };

  const handleFileSelect = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreviewUrl(reader.result as string);
    };
    reader.readAsDataURL(file);

    // Scan the receipt
    setScanning(true);
    setError('');
    setScanResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = getAuthToken();
      const response = await fetch(`${API_BASE}/receipts/scan`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Erreur ${response.status}`);
      }

      const result: ScanResult = await response.json();
      setScanResult(result);

      // Pre-fill editable fields
      setEditMerchant(result.merchant || '');
      setEditAmount(result.amount?.toString() || '');
      setEditDate(result.date || new Date().toISOString().split('T')[0]);
      setEditTag(result.suggested_tag || '');

    } catch (err: any) {
      console.error('Scan error:', err);
      setError(err.message || 'Erreur lors du scan');
    } finally {
      setScanning(false);
    }
  }, []);

  const handleCreateTransaction = useCallback(async () => {
    if (!editMerchant || !editAmount) {
      setError('Marchand et montant requis');
      return;
    }

    setCreating(true);
    setError('');

    try {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE}/receipts/create`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          merchant: editMerchant,
          amount: parseFloat(editAmount),
          date: editDate,
          tag: editTag || null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Erreur ${response.status}`);
      }

      const result = await response.json();

      if (result.success && result.transaction_id) {
        // Reset form
        setScanResult(null);
        setPreviewUrl(null);
        setEditMerchant('');
        setEditAmount('');
        setEditDate('');
        setEditTag('');
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }

        // Notify parent
        if (onTransactionCreated) {
          onTransactionCreated(result.transaction_id);
        }
      }

    } catch (err: any) {
      console.error('Create error:', err);
      setError(err.message || 'Erreur lors de la creation');
    } finally {
      setCreating(false);
    }
  }, [editMerchant, editAmount, editDate, editTag, onTransactionCreated]);

  const handleReset = () => {
    setScanResult(null);
    setPreviewUrl(null);
    setError('');
    setEditMerchant('');
    setEditAmount('');
    setEditDate('');
    setEditTag('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const selectAmount = (amount: number) => {
    setEditAmount(amount.toString());
  };

  return (
    <Card className={`p-6 ${className}`}>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-2xl">📸</span>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          Scanner un ticket
        </h2>
      </div>

      {error && (
        <Alert variant="error" className="mb-4">
          {error}
        </Alert>
      )}

      {/* File input - works on both desktop and mobile */}
      <div className="mb-4">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFileSelect}
          className="hidden"
          id="receipt-input"
        />

        {!previewUrl ? (
          <label
            htmlFor="receipt-input"
            className="flex flex-col items-center justify-center w-full h-48 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              <svg className="w-10 h-10 mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <p className="mb-2 text-sm text-gray-500 dark:text-gray-400">
                <span className="font-semibold">Cliquez pour choisir</span> ou prenez une photo
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                JPEG, PNG (max 10MB)
              </p>
            </div>
          </label>
        ) : (
          <div className="relative">
            <img
              src={previewUrl}
              alt="Receipt preview"
              className="w-full max-h-64 object-contain rounded-lg bg-gray-100 dark:bg-gray-800"
            />
            <button
              onClick={handleReset}
              className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
              title="Supprimer"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Scanning indicator */}
      {scanning && (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner text="Analyse du ticket en cours..." />
        </div>
      )}

      {/* Scan results and edit form */}
      {scanResult && !scanning && (
        <div className="space-y-4">
          {/* Confidence indicator */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Confiance OCR:</span>
            <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  scanResult.confidence > 0.7 ? 'bg-green-500' :
                  scanResult.confidence > 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${scanResult.confidence * 100}%` }}
              />
            </div>
            <span className="text-sm font-medium">{Math.round(scanResult.confidence * 100)}%</span>
          </div>

          {/* Editable fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Marchand
              </label>
              <input
                type="text"
                value={editMerchant}
                onChange={(e) => setEditMerchant(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                placeholder="Nom du marchand"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Montant (EUR)
              </label>
              <input
                type="number"
                step="0.01"
                value={editAmount}
                onChange={(e) => setEditAmount(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                placeholder="0.00"
              />
              {/* Alternative amounts */}
              {scanResult.all_amounts.length > 1 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  <span className="text-xs text-gray-500">Autres montants:</span>
                  {scanResult.all_amounts.slice(0, 5).map((amount, idx) => (
                    <button
                      key={idx}
                      onClick={() => selectAmount(amount)}
                      className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
                    >
                      {amount.toFixed(2)}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Date
              </label>
              <input
                type="date"
                value={editDate}
                onChange={(e) => setEditDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Tag
              </label>
              <input
                type="text"
                value={editTag}
                onChange={(e) => setEditTag(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                placeholder={scanResult.suggested_tag || "Tag (optionnel)"}
              />
              {scanResult.suggested_tag && !editTag && (
                <button
                  onClick={() => setEditTag(scanResult.suggested_tag!)}
                  className="mt-1 text-xs text-blue-600 hover:underline"
                >
                  Utiliser suggestion: {scanResult.suggested_tag}
                </button>
              )}
            </div>
          </div>

          {/* Raw text toggle */}
          <div>
            <button
              onClick={() => setShowRawText(!showRawText)}
              className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 flex items-center gap-1"
            >
              {showRawText ? '▼' : '▶'} Texte extrait
            </button>
            {showRawText && scanResult.raw_text && (
              <pre className="mt-2 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs overflow-auto max-h-40 whitespace-pre-wrap">
                {scanResult.raw_text}
              </pre>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              onClick={handleCreateTransaction}
              disabled={creating || !editMerchant || !editAmount}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white"
            >
              {creating ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  Creation...
                </>
              ) : (
                <>Creer la transaction</>
              )}
            </Button>
            <Button
              onClick={handleReset}
              variant="outline"
              className="px-4"
            >
              Annuler
            </Button>
          </div>
        </div>
      )}

      {/* Help text */}
      {!scanResult && !scanning && !previewUrl && (
        <div className="text-center text-sm text-gray-500 dark:text-gray-400 mt-4">
          <p>Prenez une photo de votre ticket de caisse</p>
          <p className="text-xs mt-1">
            Fonctionne sur PC et smartphone
          </p>
        </div>
      )}
    </Card>
  );
}

export default ReceiptScanner;
