'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { coachApi, aiApi, api, categoryBudgetsApi, CoachTip, QuickAction, DailyInsight, CategoryBudget, CategoryBudgetSuggestion, ChatSession } from '@/lib/api';

interface AICoachWidgetProps {
  month: string;
  className?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

// Session storage key
const SESSION_STORAGE_KEY = 'ai_coach_session_id';

interface BudgetInfo {
  category: string;
  budgeted: number;
  spent: number;
  variance: number;
  variancePct: number;
  status: 'under' | 'on_track' | 'warning' | 'over';
}

interface FinancialContext {
  month: string;
  totalIncome: number;
  // Dépenses incluses (courantes)
  totalExpenses: number;
  // Dépenses exclues (provisions, épargne, virements compte à compte)
  excludedExpenses: number;
  excludedCount: number;
  // Total toutes dépenses
  allExpensesTotal: number;
  savings: number;
  topCategories: { name: string; amount: number }[];
  // Top catégories des transactions exclues (provisions)
  topExcludedCategories: { name: string; amount: number }[];
  transactionCount: number;
  budgetStatus: string;
  budgets: BudgetInfo[];
  totalBudgeted: number;
  budgetsDefined: boolean;
  suggestions: CategoryBudgetSuggestion[];
}

export function AICoachWidget({ month, className = '' }: AICoachWidgetProps) {
  const router = useRouter();
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // UI States
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'tips' | 'chat'>('tips');

  // Tips data
  const [tips, setTips] = useState<CoachTip[]>([]);
  const [dailyInsight, setDailyInsight] = useState<DailyInsight | null>(null);
  const [quickActions, setQuickActions] = useState<QuickAction[]>([]);
  const [currentTipIndex, setCurrentTipIndex] = useState(0);

  // Chat data
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [useStreaming, setUseStreaming] = useState(true); // Toggle for streaming mode

  // Session management
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionInfo, setSessionInfo] = useState<ChatSession | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState(false);

  // Financial context
  const [financialContext, setFinancialContext] = useState<FinancialContext | null>(null);

  // Loading states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load financial context
  const loadFinancialContext = useCallback(async () => {
    try {
      // Fetch all data in parallel
      // IMPORTANT: limit=500 pour récupérer TOUTES les transactions du mois (défaut API = 50)
      const [configRes, transactionsRes, budgetsRes, suggestionsRes] = await Promise.all([
        api.get('/config').catch(() => ({ data: {} })),
        api.get(`/transactions?month=${month}&limit=500`).catch(() => ({ data: [] })),
        categoryBudgetsApi.getAll(month).catch(() => []),
        categoryBudgetsApi.getSuggestions(6).catch(() => ({ suggestions: [] }))
      ]);

      const config = configRes?.data || {};
      // L'API retourne maintenant un objet paginé { items: [...], total, page, ... }
      const transactionsData = transactionsRes?.data || {};
      const transactions = transactionsData.items || transactionsData || [];
      const budgets: CategoryBudget[] = budgetsRes || [];
      const suggestions = suggestionsRes?.suggestions || [];

      // Revenus depuis la config (salaires configurés, comme le dashboard)
      const rev1Gross = config.rev1 || 0;
      const rev2Gross = config.rev2 || 0;
      const tax1 = (config.tax_rate1 || 0) / 100;
      const tax2 = (config.tax_rate2 || 0) / 100;
      const rev1Net = rev1Gross * (1 - tax1);
      const rev2Net = rev2Gross * (1 - tax2);
      const totalIncome = rev1Net + rev2Net;

      // Calculate expenses from transactions - INCLUSES (dépenses courantes)
      const includedExpenses = transactions.filter((t: any) => t.amount < 0 && !t.exclude);
      const totalExpenses = includedExpenses.reduce((sum: number, t: any) => sum + Math.abs(t.amount), 0);

      // Calculate EXCLUDED expenses (provisions, épargne, virements compte à compte)
      const excludedTransactions = transactions.filter((t: any) => t.amount < 0 && t.exclude);
      const excludedExpenses = excludedTransactions.reduce((sum: number, t: any) => sum + Math.abs(t.amount), 0);
      const excludedCount = excludedTransactions.length;

      // Total de TOUTES les dépenses (incluses + exclues)
      const allExpensesTotal = totalExpenses + excludedExpenses;

      // Group INCLUDED by category/tag
      const categoryTotals: Record<string, number> = {};
      includedExpenses.forEach((t: any) => {
        const tag = t.tags?.[0] || t.category || 'autres';
        categoryTotals[tag] = (categoryTotals[tag] || 0) + Math.abs(t.amount);
      });

      const topCategories = Object.entries(categoryTotals)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 5)
        .map(([name, amount]) => ({ name, amount }));

      // Group EXCLUDED by category/tag (provisions, épargne)
      const excludedCategoryTotals: Record<string, number> = {};
      excludedTransactions.forEach((t: any) => {
        const tag = t.tags?.[0] || t.category || 'provision/épargne';
        excludedCategoryTotals[tag] = (excludedCategoryTotals[tag] || 0) + Math.abs(t.amount);
      });

      const topExcludedCategories = Object.entries(excludedCategoryTotals)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 5)
        .map(([name, amount]) => ({ name, amount }));

      // Calculate budget variance per category
      const budgetInfos: BudgetInfo[] = budgets.map(b => {
        const spent = categoryTotals[b.category] || 0;
        const variance = spent - b.budget_amount;
        const variancePct = b.budget_amount > 0 ? (variance / b.budget_amount) * 100 : 0;
        let status: BudgetInfo['status'] = 'on_track';
        if (variancePct > 20) status = 'over';
        else if (variancePct > 0) status = 'warning';
        else if (variancePct < -20) status = 'under';
        return {
          category: b.category,
          budgeted: b.budget_amount,
          spent,
          variance,
          variancePct,
          status
        };
      });

      const totalBudgeted = budgets.reduce((sum, b) => sum + b.budget_amount, 0);

      // Determine overall budget status
      const savingsRate = totalIncome > 0 ? ((totalIncome - totalExpenses) / totalIncome) * 100 : 0;
      let budgetStatus = 'équilibré';
      if (savingsRate < 0) budgetStatus = 'déficitaire';
      else if (savingsRate < 10) budgetStatus = 'serré';
      else if (savingsRate > 30) budgetStatus = 'excellent';
      else if (savingsRate > 20) budgetStatus = 'bon';

      setFinancialContext({
        month,
        totalIncome,
        totalExpenses,
        excludedExpenses,
        excludedCount,
        allExpensesTotal,
        savings: totalIncome - totalExpenses,
        topCategories,
        topExcludedCategories,
        transactionCount: transactions.length,
        budgetStatus,
        budgets: budgetInfos,
        totalBudgeted,
        budgetsDefined: budgets.length > 0,
        suggestions
      });
    } catch (err) {
      console.error('Failed to load financial context:', err);
    }
  }, [month]);

  // Load coach tips
  const loadCoachData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [tipsResponse, insightResponse, actionsResponse] = await Promise.all([
        coachApi.getDashboardTips(month, 5).catch(() => ({ tips: [] })),
        coachApi.getDailyInsight().catch(() => ({ insight: null })),
        coachApi.getQuickActions(month).catch(() => ({ actions: [] }))
      ]);

      setTips(tipsResponse.tips || []);
      setDailyInsight(insightResponse.insight);
      setQuickActions(actionsResponse.actions || []);
    } catch (err) {
      console.error('Failed to load coach data:', err);
      setError('Mode hors-ligne');
      setTips([{
        id: 'fallback',
        message: 'Bienvenue! Posez-moi vos questions sur votre budget.',
        category: 'tip',
        icon: '💡',
        priority: 0
      }]);
    } finally {
      setLoading(false);
    }
  }, [month]);

  useEffect(() => {
    loadCoachData();
    loadFinancialContext();
  }, [loadCoachData, loadFinancialContext]);

  // Initialize or restore chat session
  const initializeSession = useCallback(async (forceNew: boolean = false) => {
    setIsLoadingSession(true);
    try {
      // Check for existing session in localStorage
      const storedSessionId = !forceNew ? localStorage.getItem(SESSION_STORAGE_KEY) : null;

      if (storedSessionId && !forceNew) {
        // Try to get active session from backend
        try {
          const history = await aiApi.getSessionHistory(storedSessionId);
          if (history && history.messages.length > 0) {
            setSessionId(storedSessionId);
            // Restore messages from session
            const restoredMessages: ChatMessage[] = history.messages.map(m => ({
              id: m.message_id,
              role: m.role as 'user' | 'assistant',
              content: m.content,
              timestamp: new Date(m.timestamp)
            }));
            setMessages(restoredMessages);
            console.log(`Restored session ${storedSessionId} with ${history.message_count} messages`);
            return;
          }
        } catch (err) {
          console.log('Previous session expired or not found, creating new one');
          localStorage.removeItem(SESSION_STORAGE_KEY);
        }
      }

      // Create new session
      const newSession = await aiApi.createSession(month);
      setSessionId(newSession.session_id);
      setSessionInfo(newSession);
      localStorage.setItem(SESSION_STORAGE_KEY, newSession.session_id);
      console.log(`Created new session: ${newSession.session_id}`);

      // Clear local messages for new session
      if (forceNew) {
        setMessages([]);
      }

    } catch (err) {
      console.error('Failed to initialize session:', err);
      // Continue without session - will use stateless chat
      setSessionId(null);
    } finally {
      setIsLoadingSession(false);
    }
  }, [month]);

  // Initialize session on mount
  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  // Start new conversation
  const startNewConversation = useCallback(async () => {
    await initializeSession(true);
    // The welcome message will be added by the existing useEffect
  }, [initializeSession]);

  // Auto-rotate tips
  useEffect(() => {
    if (tips.length <= 1 || activeTab === 'chat') return;
    const interval = setInterval(() => {
      setCurrentTipIndex(prev => (prev + 1) % tips.length);
    }, 10000);
    return () => clearInterval(interval);
  }, [tips.length, activeTab]);

  // Scroll to bottom of chat
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Initialize chat with welcome message
  useEffect(() => {
    if (messages.length === 0 && financialContext) {
      const monthLabel = new Date(month + '-01').toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });

      // Build budget status line
      let budgetLine = '';
      if (financialContext.budgetsDefined && financialContext.budgets.length > 0) {
        const overCount = financialContext.budgets.filter(b => b.status === 'over').length;
        const variance = financialContext.totalExpenses - financialContext.totalBudgeted;
        if (overCount > 0) {
          budgetLine = `\n⚠️ ${overCount} catégorie(s) en dépassement de budget`;
        } else if (variance > 0) {
          budgetLine = `\n⚡ Proche du budget total (${variance.toFixed(0)}€ de plus)`;
        } else {
          budgetLine = `\n✅ Budgets respectés (${Math.abs(variance).toFixed(0)}€ de marge)`;
        }
      } else {
        budgetLine = `\n💡 Astuce: Définissez vos budgets dans Paramètres > Objectifs Budget`;
      }

      // Ligne pour les provisions/épargne si présentes
      let provisionLine = '';
      if (financialContext.excludedExpenses > 0) {
        provisionLine = `\n• Provisions/Épargne: ${financialContext.excludedExpenses.toFixed(0)}€ (${financialContext.excludedCount} virements)`;
      }

      const welcomeMessage: ChatMessage = {
        id: 'welcome',
        role: 'assistant',
        content: `Bonjour! Je suis votre coach budget IA. 📊\n\n**Aperçu ${monthLabel}:**\n• Revenus nets: ${financialContext.totalIncome.toFixed(0)}€\n• Dépenses courantes: ${financialContext.totalExpenses.toFixed(0)}€${provisionLine}\n• Solde disponible: ${financialContext.savings >= 0 ? '+' : ''}${financialContext.savings.toFixed(0)}€\n• Statut: ${financialContext.budgetStatus}${financialContext.budgetsDefined ? `\n• Budgets: ${financialContext.budgets.length} catégories définies` : ''}${budgetLine}\n\nPosez-moi vos questions! Par exemple:\n• "Comment réduire mes dépenses?"\n• "Analyse mes catégories"\n• "Quels budgets suggères-tu?"`,
        timestamp: new Date()
      };
      setMessages([welcomeMessage]);
    }
  }, [financialContext, month, messages.length]);

  // Build context prompt for AI
  const buildContextPrompt = (userQuestion: string): string => {
    if (!financialContext) return userQuestion;

    // Build budget status section
    let budgetSection = '';
    if (financialContext.budgetsDefined && financialContext.budgets.length > 0) {
      const overBudget = financialContext.budgets.filter(b => b.status === 'over');
      const warningBudget = financialContext.budgets.filter(b => b.status === 'warning');
      budgetSection = `
BUDGETS DÉFINIS (${financialContext.budgets.length} catégories):
- Budget total: ${financialContext.totalBudgeted.toFixed(2)}€
- Dépensé: ${financialContext.totalExpenses.toFixed(2)}€
- Écart global: ${(financialContext.totalExpenses - financialContext.totalBudgeted).toFixed(2)}€
${overBudget.length > 0 ? `- DÉPASSEMENTS: ${overBudget.map(b => `${b.category} (+${b.variance.toFixed(0)}€)`).join(', ')}` : ''}
${warningBudget.length > 0 ? `- Attention: ${warningBudget.map(b => `${b.category} (${b.variancePct.toFixed(0)}%)`).join(', ')}` : ''}
Détail par catégorie:
${financialContext.budgets.map(b => `  - ${b.category}: budget ${b.budgeted.toFixed(0)}€, dépensé ${b.spent.toFixed(0)}€ (${b.status === 'over' ? '⚠️ dépassé' : b.status === 'warning' ? '⚡ attention' : '✅ OK'})`).join('\n')}`;
    } else {
      // Include suggestions if no budgets defined
      budgetSection = `
BUDGETS NON DÉFINIS:
L'utilisateur n'a pas encore défini de budgets par catégorie.
Suggestions basées sur l'historique (6 derniers mois):
${financialContext.suggestions.slice(0, 5).map(s => `  - ${s.category}: ~${s.suggested_amount.toFixed(0)}€/mois (tendance: ${s.trend})`).join('\n')}
Tu peux suggérer à l'utilisateur de définir des budgets via Paramètres > Objectifs Budget.`;
    }

    // Section provisions/épargne (transactions exclues)
    let provisionSection = '';
    if (financialContext.excludedExpenses > 0) {
      provisionSection = `
PROVISIONS ET ÉPARGNE (virements compte à compte exclus des dépenses courantes):
- Total provisions/épargne: ${financialContext.excludedExpenses.toFixed(2)}€ (${financialContext.excludedCount} virements)
- Catégories: ${financialContext.topExcludedCategories.map(c => `${c.name}: ${c.amount.toFixed(0)}€`).join(', ')}
Note: Ces montants sont des virements vers des comptes d'épargne (vacances, bébé, etc.) et ne sont pas comptés dans les dépenses courantes.`;
    }

    const contextInfo = `
CONTEXTE FINANCIER COMPLET DE L'UTILISATEUR (${month}):
- Revenus nets (salaires après impôts): ${financialContext.totalIncome.toFixed(2)}€
- Dépenses courantes (incluses): ${financialContext.totalExpenses.toFixed(2)}€
- Provisions/Épargne (exclues): ${financialContext.excludedExpenses.toFixed(2)}€
- TOTAL SORTIES (dépenses + provisions): ${financialContext.allExpensesTotal.toFixed(2)}€
- Solde disponible: ${financialContext.savings.toFixed(2)}€
- Taux d'épargne (hors provisions): ${financialContext.totalIncome > 0 ? ((financialContext.savings / financialContext.totalIncome) * 100).toFixed(1) : 0}%
- Nombre de transactions: ${financialContext.transactionCount}
- Statut global: ${financialContext.budgetStatus}

TOP CATÉGORIES DE DÉPENSES COURANTES:
${financialContext.topCategories.map((c, i) => `  ${i + 1}. ${c.name}: ${c.amount.toFixed(2)}€`).join('\n')}
${provisionSection}
${budgetSection}

QUESTION DE L'UTILISATEUR:
${userQuestion}

INSTRUCTIONS:
Tu es un coach budget familial bienveillant et expert. Réponds de manière:
- Personnalisée en utilisant TOUTES les données ci-dessus (dépenses ET provisions)
- Pratique avec des conseils actionnables
- Encourageante mais honnête
- Concise (2-3 paragraphes max)
- Si pertinent, mentionne les catégories en dépassement ou proches du seuil
- N'hésite pas à mentionner les provisions/épargne si pertinent pour l'analyse complète
Utilise des emojis avec modération pour rendre la réponse plus engageante.
`;
    return contextInfo;
  };

  // Send message to AI (with streaming support and session memory)
  const sendMessage = async () => {
    if (!inputMessage.trim() || isTyping) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);
    setStreamingContent('');

    try {
      // Use session-based chat if we have a session, otherwise fall back to stateless
      const hasSession = sessionId !== null;
      const question = userMessage.content;

      if (useStreaming) {
        // Use streaming API (with session if available)
        const assistantMsgId = (Date.now() + 1).toString();
        let fullContent = '';

        // Add placeholder message that will be updated
        setMessages(prev => [...prev, {
          id: assistantMsgId,
          role: 'assistant',
          content: '',
          timestamp: new Date()
        }]);

        try {
          // Use session streaming if we have a session, otherwise use regular streaming with context
          const streamGenerator = hasSession
            ? aiApi.sessionStreamChat(sessionId, question, month)
            : aiApi.streamChat(buildContextPrompt(question), month);

          for await (const chunk of streamGenerator) {
            fullContent += chunk;
            setStreamingContent(fullContent);

            // Update the message in real-time
            setMessages(prev => prev.map(msg =>
              msg.id === assistantMsgId
                ? { ...msg, content: fullContent }
                : msg
            ));
          }
        } catch (streamError) {
          console.warn('Streaming failed, falling back to regular API:', streamError);
          // Fallback to non-streaming if streaming fails
          setUseStreaming(false);

          const response = hasSession
            ? await aiApi.sessionChat(sessionId, question, month)
            : await aiApi.askQuestion(buildContextPrompt(question), month);

          const answer = 'answer' in response ? response.answer : '';
          setMessages(prev => prev.map(msg =>
            msg.id === assistantMsgId
              ? { ...msg, content: answer || "Je n'ai pas pu générer une réponse." }
              : msg
          ));
        }
      } else {
        // Use regular (non-streaming) API
        const response = hasSession
          ? await aiApi.sessionChat(sessionId, question, month)
          : await aiApi.askQuestion(buildContextPrompt(question), month);

        const answer = 'answer' in response ? response.answer : '';

        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: answer || "Je n'ai pas pu générer une réponse. Réessayez.",
          timestamp: new Date()
        };

        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (err) {
      console.error('Failed to get AI response:', err);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "Désolé, je rencontre un problème technique. Vérifiez que le service IA est configuré (clé API OpenRouter).",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
      setStreamingContent('');
    }
  };

  // Handle quick action click
  const handleActionClick = (action: QuickAction) => {
    if (action.action_type === 'navigate') {
      router.push(action.target);
    }
  };

  // Quick question buttons - dynamically based on context
  const quickQuestions = financialContext?.budgetsDefined
    ? [
        "Analyse mes dépassements",
        "Où puis-je économiser?",
        "Prévisions fin de mois",
        "Optimiser mes budgets"
      ]
    : [
        "Suggère-moi des budgets",
        "Comment épargner plus?",
        "Analyse mes dépenses",
        "Mes catégories principales"
      ];

  // Category styling
  const getCategoryStyle = (category: CoachTip['category']) => {
    switch (category) {
      case 'warning':
        return 'bg-amber-50 border-amber-200';
      case 'motivation':
        return 'bg-green-50 border-green-200';
      case 'insight':
        return 'bg-blue-50 border-blue-200';
      default:
        return 'bg-purple-50 border-purple-200';
    }
  };

  const currentTip = tips[currentTipIndex];

  return (
    <div className={`rounded-xl bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border border-purple-200/50 overflow-hidden transition-all duration-300 ${isExpanded ? 'max-h-[600px]' : 'max-h-[280px]'} ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-purple-200/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🤖</span>
            <h3 className="font-semibold text-gray-900">Coach Budget IA</h3>
            {financialContext && (
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                financialContext.budgetStatus === 'excellent' ? 'bg-green-100 text-green-700' :
                financialContext.budgetStatus === 'bon' ? 'bg-blue-100 text-blue-700' :
                financialContext.budgetStatus === 'déficitaire' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {financialContext.budgetStatus}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Session indicator */}
            {activeTab === 'chat' && sessionId && (
              <span className="text-xs text-gray-400 hidden sm:inline" title={`Session: ${sessionId.slice(0, 8)}...`}>
                🔗 Memoire active
              </span>
            )}
            {/* New Conversation button */}
            {activeTab === 'chat' && (
              <button
                onClick={startNewConversation}
                disabled={isLoadingSession}
                className="px-2 py-1 text-xs bg-white/70 hover:bg-white border border-purple-200 rounded-md text-purple-600 hover:text-purple-700 transition-all disabled:opacity-50"
                title="Nouvelle conversation"
              >
                {isLoadingSession ? '...' : '🔄 Nouveau'}
              </button>
            )}
            {/* Tabs */}
            <div className="flex bg-white/50 rounded-lg p-0.5">
              <button
                onClick={() => setActiveTab('tips')}
                className={`px-3 py-1 text-xs rounded-md transition-all ${
                  activeTab === 'tips' ? 'bg-white shadow text-purple-700' : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Conseils
              </button>
              <button
                onClick={() => { setActiveTab('chat'); setIsExpanded(true); }}
                className={`px-3 py-1 text-xs rounded-md transition-all ${
                  activeTab === 'chat' ? 'bg-white shadow text-purple-700' : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                💬 Chat {sessionId && messages.length > 1 && <span className="ml-1 text-purple-400">({messages.length})</span>}
              </button>
            </div>
            {/* Expand/collapse */}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 hover:bg-white/50 rounded transition-colors"
            >
              <svg className={`w-4 h-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {activeTab === 'tips' ? (
          /* Tips View */
          <div className="space-y-3">
            {/* Daily Insight */}
            {dailyInsight && (
              <div className="p-3 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-100">
                <div className="flex items-start gap-2">
                  <span className="text-xl">{dailyInsight.emoji}</span>
                  <div>
                    <p className="text-sm text-gray-700">{dailyInsight.message}</p>
                    {dailyInsight.data_point && (
                      <p className="text-xs text-indigo-600 mt-1 font-medium">{dailyInsight.data_point}</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Current Tip */}
            {currentTip && (
              <div className={`p-3 rounded-lg border ${getCategoryStyle(currentTip.category)}`}>
                <div className="flex items-start gap-2">
                  <span className="text-lg">{currentTip.icon}</span>
                  <p className="text-sm text-gray-700 flex-1">{currentTip.message}</p>
                </div>
                {tips.length > 1 && (
                  <div className="flex justify-center gap-1.5 mt-2">
                    {tips.map((_, idx) => (
                      <button
                        key={idx}
                        onClick={() => setCurrentTipIndex(idx)}
                        className={`w-1.5 h-1.5 rounded-full transition-all ${
                          idx === currentTipIndex ? 'bg-purple-500 w-4' : 'bg-gray-300'
                        }`}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Quick Actions */}
            {quickActions.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {quickActions.map(action => (
                  <button
                    key={action.id}
                    onClick={() => handleActionClick(action)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-purple-300 transition-all"
                  >
                    <span>{action.icon}</span>
                    <span>{action.label}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Open Chat Button */}
            <button
              onClick={() => { setActiveTab('chat'); setIsExpanded(true); }}
              className="w-full py-2 text-sm text-purple-600 hover:text-purple-700 hover:bg-purple-50 rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <span>💬</span>
              <span>Poser une question au coach</span>
            </button>
          </div>
        ) : (
          /* Chat View */
          <div className="flex flex-col h-[400px]">
            {/* Messages */}
            <div
              ref={chatContainerRef}
              className="flex-1 overflow-y-auto space-y-3 mb-3 pr-2"
            >
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] p-3 rounded-xl text-sm whitespace-pre-wrap ${
                      msg.role === 'user'
                        ? 'bg-purple-600 text-white rounded-br-sm'
                        : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              {isTyping && !streamingContent && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 p-3 rounded-xl rounded-bl-sm">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                        <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                        <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                      </div>
                      <span className="text-xs text-gray-400">Reflexion...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Quick Questions */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              {quickQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => setInputMessage(q)}
                  className="px-2 py-1 text-xs bg-white border border-gray-200 rounded-full text-gray-600 hover:border-purple-300 hover:text-purple-600 transition-all"
                >
                  {q}
                </button>
              ))}
            </div>

            {/* Input */}
            <div className="flex gap-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="Posez votre question..."
                className="flex-1 px-4 py-2 border border-gray-200 rounded-full text-sm focus:outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
                disabled={isTyping}
              />
              <button
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isTyping}
                className="px-4 py-2 bg-purple-600 text-white rounded-full text-sm font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Envoyer
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default AICoachWidget;
