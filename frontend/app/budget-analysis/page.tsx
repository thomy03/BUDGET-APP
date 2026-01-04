'use client';

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../lib/auth";
import { useGlobalMonth } from "../../lib/month";
import { LoadingSpinner, Card, Button, Alert } from "../../components/ui";
import { BudgetVarianceAnalysis } from "../../components/analytics";
import { aiApi } from "../../lib/api";

type AIView = 'variance' | 'summary' | 'savings' | 'chat';

export default function BudgetAnalysisPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [month] = useGlobalMonth();

  const [activeView, setActiveView] = useState<AIView>('variance');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [aiConfigured, setAiConfigured] = useState(false);

  // Monthly summary state
  const [monthlySummary, setMonthlySummary] = useState<any>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);

  // Savings suggestions state
  const [selectedCategory, setSelectedCategory] = useState('');
  const [savingsSuggestions, setSavingsSuggestions] = useState<any>(null);
  const [loadingSavings, setLoadingSavings] = useState(false);

  // Chat state
  const [chatQuestion, setChatQuestion] = useState('');
  const [chatAnswer, setChatAnswer] = useState<any>(null);
  const [loadingChat, setLoadingChat] = useState(false);

  // Redirection si non authentifie
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

  // Check AI status
  useEffect(() => {
    const checkAI = async () => {
      try {
        const status = await aiApi.getStatus();
        setAiConfigured(status.configured);
      } catch (err) {
        console.error('Error checking AI status:', err);
      }
    };
    if (isAuthenticated) {
      checkAI();
    }
  }, [isAuthenticated]);

  const handleGetMonthlySummary = async () => {
    try {
      setLoadingSummary(true);
      setError('');
      const summary = await aiApi.monthlySummary(month);
      setMonthlySummary(summary);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la generation du resume');
    } finally {
      setLoadingSummary(false);
    }
  };

  const handleGetSavingsSuggestions = async () => {
    if (!selectedCategory) {
      setError('Selectionnez une categorie');
      return;
    }
    try {
      setLoadingSavings(true);
      setError('');
      const suggestions = await aiApi.suggestSavings(selectedCategory, 6);
      setSavingsSuggestions(suggestions);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la generation des suggestions');
    } finally {
      setLoadingSavings(false);
    }
  };

  const handleChat = async () => {
    if (!chatQuestion.trim()) {
      setError('Posez une question');
      return;
    }
    try {
      setLoadingChat(true);
      setError('');
      const answer = await aiApi.chat(chatQuestion, month);
      setChatAnswer(answer);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de la reponse IA');
    } finally {
      setLoadingChat(false);
    }
  };

  if (authLoading) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner text="Verification de l'authentification..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <main className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            🎯 Analyse Budgetaire Intelligente
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Analyse IA de vos budgets et suggestions personnalisees
          </p>
        </div>
        <div className="flex items-center gap-2">
          {aiConfigured ? (
            <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">
              ✅ IA Active
            </span>
          ) : (
            <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm">
              ⚠️ IA Non configuree
            </span>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="error">
          {error}
          <button onClick={() => setError('')} className="ml-2">×</button>
        </Alert>
      )}

      {/* Navigation */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700">
        {[
          { id: 'variance', label: '📊 Ecarts Budget', icon: '📊' },
          { id: 'summary', label: '📝 Resume Mensuel', icon: '📝' },
          { id: 'savings', label: '💰 Suggestions Economies', icon: '💰' },
          { id: 'chat', label: '💬 Chat IA', icon: '💬' }
        ].map(view => (
          <button
            key={view.id}
            onClick={() => setActiveView(view.id as AIView)}
            className={`px-4 py-3 font-medium transition-colors ${
              activeView === view.id
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {view.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="min-h-[500px]">
        {/* Vue Variance */}
        {activeView === 'variance' && (
          <BudgetVarianceAnalysis month={month} />
        )}

        {/* Vue Resume Mensuel */}
        {activeView === 'summary' && (
          <div className="space-y-6">
            <Card className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    📝 Resume Mensuel Intelligent
                  </h2>
                  <p className="text-sm text-gray-500">
                    Bilan detaille de vos finances pour {new Date(month + '-01').toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}
                  </p>
                </div>
                <Button
                  onClick={handleGetMonthlySummary}
                  disabled={loadingSummary || !aiConfigured}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {loadingSummary ? (
                    <>
                      <LoadingSpinner size="sm" className="mr-2" />
                      Generation...
                    </>
                  ) : (
                    '✨ Generer le resume'
                  )}
                </Button>
              </div>

              {monthlySummary ? (
                <div className="space-y-4">
                  {/* Stats */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                      <p className="text-sm text-green-600">Revenus</p>
                      <p className="text-2xl font-bold text-green-700">
                        {monthlySummary.income?.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' }) || '0 €'}
                      </p>
                    </div>
                    <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
                      <p className="text-sm text-red-600">Depenses</p>
                      <p className="text-2xl font-bold text-red-700">
                        {monthlySummary.expenses?.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' }) || '0 €'}
                      </p>
                    </div>
                    <div className={`p-4 rounded-lg ${
                      (monthlySummary.savings || 0) >= 0 ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-orange-50 dark:bg-orange-900/20'
                    }`}>
                      <p className={`text-sm ${(monthlySummary.savings || 0) >= 0 ? 'text-blue-600' : 'text-orange-600'}`}>
                        Epargne
                      </p>
                      <p className={`text-2xl font-bold ${(monthlySummary.savings || 0) >= 0 ? 'text-blue-700' : 'text-orange-700'}`}>
                        {monthlySummary.savings?.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' }) || '0 €'}
                      </p>
                    </div>
                  </div>

                  {/* Summary text */}
                  <div className="p-6 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg">
                    <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
                      {monthlySummary.summary}
                    </p>
                    <p className="text-xs text-gray-500 mt-4">
                      Genere par {monthlySummary.model_used}
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">
                  Cliquez sur le bouton pour generer un resume intelligent de votre mois.
                </p>
              )}
            </Card>
          </div>
        )}

        {/* Vue Suggestions Economies */}
        {activeView === 'savings' && (
          <div className="space-y-6">
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
                💰 Suggestions d'Economies
              </h2>
              <p className="text-sm text-gray-500 mb-6">
                Obtenez des conseils personnalises pour reduire vos depenses dans une categorie specifique.
              </p>

              <div className="flex gap-4 mb-6">
                <input
                  type="text"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  placeholder="Ex: courses, transport, loisirs..."
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
                <Button
                  onClick={handleGetSavingsSuggestions}
                  disabled={loadingSavings || !aiConfigured || !selectedCategory}
                  className="bg-green-600 hover:bg-green-700 text-white"
                >
                  {loadingSavings ? (
                    <LoadingSpinner size="sm" />
                  ) : (
                    '💡 Obtenir des conseils'
                  )}
                </Button>
              </div>

              {savingsSuggestions && (
                <div className="space-y-4">
                  <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <p className="text-sm text-blue-600">Depense moyenne mensuelle ({savingsSuggestions.category})</p>
                    <p className="text-2xl font-bold text-blue-700">
                      {savingsSuggestions.average_spending?.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' }) || '0 €'}
                    </p>
                  </div>

                  <div className="p-6 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-lg">
                    <h3 className="font-semibold text-green-700 mb-3">Conseils personnalises:</h3>
                    <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {savingsSuggestions.suggestions}
                    </p>
                    <p className="text-xs text-gray-500 mt-4">
                      Genere par {savingsSuggestions.model_used}
                    </p>
                  </div>
                </div>
              )}
            </Card>
          </div>
        )}

        {/* Vue Chat IA */}
        {activeView === 'chat' && (
          <div className="space-y-6">
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
                💬 Posez vos questions sur votre budget
              </h2>
              <p className="text-sm text-gray-500 mb-6">
                L'IA analysera vos donnees financieres pour repondre a vos questions.
              </p>

              <div className="space-y-4">
                <textarea
                  value={chatQuestion}
                  onChange={(e) => setChatQuestion(e.target.value)}
                  placeholder="Ex: Ou est-ce que je depense le plus ? Comment reduire mes depenses alimentaires ? Quel est mon taux d'epargne ?"
                  rows={3}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white resize-none"
                />
                <div className="flex justify-between items-center">
                  <p className="text-xs text-gray-500">
                    Contexte: {new Date(month + '-01').toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}
                  </p>
                  <Button
                    onClick={handleChat}
                    disabled={loadingChat || !aiConfigured || !chatQuestion.trim()}
                    className="bg-purple-600 hover:bg-purple-700 text-white"
                  >
                    {loadingChat ? (
                      <>
                        <LoadingSpinner size="sm" className="mr-2" />
                        Reflexion...
                      </>
                    ) : (
                      '🤖 Demander a l\'IA'
                    )}
                  </Button>
                </div>
              </div>

              {chatAnswer && (
                <div className="mt-6 space-y-4">
                  <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
                    <p className="text-sm text-gray-500 mb-2">Votre question:</p>
                    <p className="text-gray-900 dark:text-white">{chatAnswer.question}</p>
                  </div>

                  <div className="p-6 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-lg">
                    <p className="text-sm text-purple-600 mb-2">Reponse de l'IA:</p>
                    <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {chatAnswer.answer}
                    </p>
                    <p className="text-xs text-gray-500 mt-4">
                      Genere par {chatAnswer.model_used}
                    </p>
                  </div>
                </div>
              )}

              {/* Suggestions de questions */}
              <div className="mt-6">
                <p className="text-sm text-gray-500 mb-3">Suggestions de questions:</p>
                <div className="flex flex-wrap gap-2">
                  {[
                    "Quel est mon plus gros poste de depense ?",
                    "Comment puis-je economiser 10% ?",
                    "Mes depenses sont-elles normales ?",
                    "Ou est-ce que je depense le plus ?"
                  ].map((q, i) => (
                    <button
                      key={i}
                      onClick={() => setChatQuestion(q)}
                      className="px-3 py-1 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-full text-sm hover:bg-gray-200 dark:hover:bg-gray-700 transition"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>
    </main>
  );
}
