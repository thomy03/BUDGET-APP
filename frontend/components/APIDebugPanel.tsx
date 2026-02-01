'use client';

import { useState } from 'react';
import { api, apiUtils } from '../lib/api';
import { Card, Button, Alert } from './ui';

export default function APIDebugPanel() {
  const [testing, setTesting] = useState(false);
  const [results, setResults] = useState<any>({});

  const runTests = async () => {
    setTesting(true);
    const testResults: any = {};

    try {
      // Test 1: Vérifier l'authentification locale
      testResults.auth = {
        hasToken: !!localStorage.getItem('auth_token'),
        tokenType: localStorage.getItem('token_type'),
        tokenLength: localStorage.getItem('auth_token')?.length || 0,
      };

      // Test 2: Health check
      try {
        const healthCheck = await apiUtils.checkHealth();
        testResults.health = { status: 'ok', accessible: healthCheck };
      } catch (err: any) {
        testResults.health = { status: 'error', error: err.message };
      }

      // Test 3: Test endpoint provisions
      try {
        const response = await api.get('/custom-provisions');
        testResults.provisions = {
          status: 'success',
          httpStatus: response.status,
          count: response.data?.length || 0,
          hasAuth: !!response.config?.headers?.Authorization
        };
      } catch (err: any) {
        testResults.provisions = {
          status: 'error',
          httpStatus: err.response?.status,
          error: err.response?.data?.detail || err.message,
          hasAuth: !!err.config?.headers?.Authorization,
          networkError: err.code === 'ERR_NETWORK'
        };
      }

      // Test 4: Test endpoint alternatif
      try {
        const response = await api.get('/provisions');
        testResults.alternativeProvisions = {
          status: 'success',
          httpStatus: response.status,
          count: response.data?.length || 0,
          hasAuth: !!response.config?.headers?.Authorization
        };
      } catch (err: any) {
        testResults.alternativeProvisions = {
          status: 'error',
          httpStatus: err.response?.status,
          error: err.response?.data?.detail || err.message,
          hasAuth: !!err.config?.headers?.Authorization,
          networkError: err.code === 'ERR_NETWORK'
        };
      }

    } catch (err) {
      testResults.globalError = err;
    }

    setResults(testResults);
    setTesting(false);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return '✅';
      case 'error': return '❌';
      default: return '⚠️';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'text-green-700 bg-green-50';
      case 'error': return 'text-red-700 bg-red-50';
      default: return 'text-amber-700 bg-amber-50';
    }
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">🔧 Debug API</h3>
        <Button
          onClick={runTests}
          disabled={testing}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
        >
          {testing ? '⏳ Test en cours...' : '🧪 Lancer les tests'}
        </Button>
      </div>

      {Object.keys(results).length > 0 && (
        <div className="space-y-4">
          {/* Test Authentification */}
          {results.auth && (
            <div className="border rounded-lg p-3">
              <h4 className="font-medium mb-2">🔐 Authentification</h4>
              <div className="text-sm space-y-1">
                <p>Token présent: <span className={results.auth.hasToken ? 'text-green-600' : 'text-red-600'}>
                  {results.auth.hasToken ? '✅ Oui' : '❌ Non'}
                </span></p>
                {results.auth.hasToken && (
                  <>
                    <p>Type: <span className="font-mono">{results.auth.tokenType || 'Bearer'}</span></p>
                    <p>Longueur: <span className="font-mono">{results.auth.tokenLength} caractères</span></p>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Test Health */}
          {results.health && (
            <div className="border rounded-lg p-3">
              <h4 className="font-medium mb-2">
                {getStatusIcon(results.health.status)} Santé API
              </h4>
              <div className={`text-sm p-2 rounded ${getStatusColor(results.health.status)}`}>
                {results.health.status === 'ok' ? (
                  <p>✅ API accessible</p>
                ) : (
                  <p>❌ Erreur: {results.health.error}</p>
                )}
              </div>
            </div>
          )}

          {/* Test Provisions */}
          {results.provisions && (
            <div className="border rounded-lg p-3">
              <h4 className="font-medium mb-2">
                {getStatusIcon(results.provisions.status)} Endpoint /custom-provisions
              </h4>
              <div className={`text-sm p-2 rounded ${getStatusColor(results.provisions.status)}`}>
                {results.provisions.status === 'success' ? (
                  <div>
                    <p>✅ Status HTTP: {results.provisions.httpStatus}</p>
                    <p>📊 Provisions trouvées: {results.provisions.count}</p>
                    <p>🔐 Auth envoyée: {results.provisions.hasAuth ? '✅ Oui' : '❌ Non'}</p>
                  </div>
                ) : (
                  <div>
                    <p>❌ Status HTTP: {results.provisions.httpStatus || 'N/A'}</p>
                    <p>🔐 Auth envoyée: {results.provisions.hasAuth ? '✅ Oui' : '❌ Non'}</p>
                    <p>⚠️ Erreur: {results.provisions.error}</p>
                    {results.provisions.networkError && <p>🌐 Erreur réseau détectée</p>}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Test Alternative Provisions */}
          {results.alternativeProvisions && (
            <div className="border rounded-lg p-3">
              <h4 className="font-medium mb-2">
                {getStatusIcon(results.alternativeProvisions.status)} Endpoint /provisions
              </h4>
              <div className={`text-sm p-2 rounded ${getStatusColor(results.alternativeProvisions.status)}`}>
                {results.alternativeProvisions.status === 'success' ? (
                  <div>
                    <p>✅ Status HTTP: {results.alternativeProvisions.httpStatus}</p>
                    <p>📊 Provisions trouvées: {results.alternativeProvisions.count}</p>
                    <p>🔐 Auth envoyée: {results.alternativeProvisions.hasAuth ? '✅ Oui' : '❌ Non'}</p>
                  </div>
                ) : (
                  <div>
                    <p>❌ Status HTTP: {results.alternativeProvisions.httpStatus || 'N/A'}</p>
                    <p>🔐 Auth envoyée: {results.alternativeProvisions.hasAuth ? '✅ Oui' : '❌ Non'}</p>
                    <p>⚠️ Erreur: {results.alternativeProvisions.error}</p>
                    {results.alternativeProvisions.networkError && <p>🌐 Erreur réseau détectée</p>}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Configuration */}
          <div className="border rounded-lg p-3">
            <h4 className="font-medium mb-2">⚙️ Configuration</h4>
            <div className="text-sm space-y-1 font-mono">
              <p>API Base: {process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:5000"}</p>
              <p>Environment: {process.env.NODE_ENV || "development"}</p>
              <p>Timeout: 15s</p>
            </div>
          </div>
        </div>
      )}

      {Object.keys(results).length === 0 && !testing && (
        <Alert variant="info">
          Cliquez sur "Lancer les tests" pour diagnostiquer les problèmes de connexion API
        </Alert>
      )}
    </Card>
  );
}