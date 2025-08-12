'use client';

import { useState } from 'react';
import { WebResearchIndicator } from '../ui/WebResearchIndicator';
import { MerchantInfoDisplay } from '../ui/MerchantInfoDisplay';

/**
 * Composant de démonstration pour tester l'interface de classification intelligente
 * Ce composant permet de simuler le workflow utilisateur complet.
 */
export function ClassificationDemo() {
  const [isSearching, setIsSearching] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [merchantName, setMerchantName] = useState('');

  const mockMerchantInfo = {
    name: 'Le Petit Paris',
    category: 'Restaurant gastronomique',
    type: 'variable' as const,
    confidence: 0.95,
    description: 'Restaurant français traditionnel spécialisé dans la cuisine parisienne authentique.',
    website: 'https://lepetitparis.fr',
    address: '12 Rue de la Paix, 75001 Paris',
    phone: '01 42 86 87 88',
    sources: ['Google Places', 'Yelp', 'TripAdvisor'],
    lastUpdated: '2025-08-12T10:00:00Z'
  };

  const simulateSearch = async () => {
    if (!merchantName.trim()) return;

    setIsSearching(true);
    setShowResult(false);

    // Simuler le délai de recherche
    await new Promise(resolve => setTimeout(resolve, 2000));

    setIsSearching(false);
    setShowResult(true);
  };

  const handleAccept = (type: 'fixed' | 'variable') => {
    console.log(`✅ Classification acceptée: ${type}`);
    setShowResult(false);
    setMerchantName('');
  };

  const handleReject = () => {
    console.log('❌ Classification rejetée');
    setShowResult(false);
  };

  const handleReportError = () => {
    console.log('⚠️ Erreur signalée');
    alert('Merci ! L\'erreur a été signalée pour améliorer notre système.');
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Démo Classification Intelligente
        </h1>
        <p className="text-gray-600">
          Testez le nouveau workflow de recherche web pour la classification des dépenses
        </p>
      </div>

      {/* Simulateur de saisie de tag */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-4">1. Saisie de Tag</h2>
        <div className="relative">
          <input
            type="text"
            value={merchantName}
            onChange={(e) => setMerchantName(e.target.value)}
            placeholder="Saisissez le nom d'un commerce (ex: Le Petit Paris)"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          
          {/* Indicateur de recherche */}
          <WebResearchIndicator
            isSearching={isSearching}
            merchantName={merchantName}
            onCancel={() => {
              setIsSearching(false);
              setShowResult(false);
            }}
            confidence={showResult ? mockMerchantInfo.confidence : undefined}
            result={showResult ? {
              name: mockMerchantInfo.name,
              category: mockMerchantInfo.category,
              type: mockMerchantInfo.type,
              source: 'Recherche web'
            } : undefined}
          />
        </div>

        <button
          onClick={simulateSearch}
          disabled={!merchantName.trim() || isSearching}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isSearching ? 'Recherche en cours...' : 'Démarrer la recherche'}
        </button>
      </div>

      {/* Résultat de la recherche */}
      {showResult && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">2. Résultat de la Recherche Web</h2>
          
          <MerchantInfoDisplay
            merchantInfo={mockMerchantInfo}
            mode="compact"
            showActions={true}
            onAccept={handleAccept}
            onReject={handleReject}
            onReportError={handleReportError}
          />
        </div>
      )}

      {/* Mode détaillé */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h2 className="text-xl font-semibold mb-4">3. Mode Détaillé (Dashboard)</h2>
        <p className="text-gray-600 mb-4">
          Voici comment les informations apparaîtraient dans la base de connaissances du dashboard :
        </p>
        
        <MerchantInfoDisplay
          merchantInfo={mockMerchantInfo}
          mode="detailed"
          showActions={true}
          onAccept={handleAccept}
          onReject={handleReject}
          onReportError={handleReportError}
        />
      </div>

      {/* Statistiques */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4 text-blue-900">
          Statistiques d'Enrichissement
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">127</div>
            <div className="text-sm text-gray-600">Commerces enrichis</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">94%</div>
            <div className="text-sm text-gray-600">Confiance moyenne</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">23</div>
            <div className="text-sm text-gray-600">En attente de validation</div>
          </div>
        </div>
      </div>

      {/* Workflow idéal */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Workflow Utilisateur Idéal</h2>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">1</div>
            <span>L'utilisateur tape "Le Petit Paris" dans le champ tag</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">2</div>
            <span>🔍 "Recherche web en cours..." s'affiche automatiquement</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-green-100 text-green-600 rounded-full flex items-center justify-center text-sm font-medium">3</div>
            <span>✅ "Restaurant gastronomique trouvé (95% confiance)"</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-orange-100 text-orange-600 rounded-full flex items-center justify-center text-sm font-medium">4</div>
            <span>💡 "Classification: Variable - Restaurants"</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center text-sm font-medium">5</div>
            <span>L'utilisateur peut accepter, modifier ou signaler une erreur</span>
          </div>
        </div>
      </div>
    </div>
  );
}