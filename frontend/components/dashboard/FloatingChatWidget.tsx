'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { aiApi, api, categoryBudgetsApi, CategoryBudget, CategoryBudgetSuggestion, ChatSession } from '@/lib/api';
import { XMarkIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline';

interface FloatingChatWidgetProps {
  month: string;
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

export function FloatingChatWidget({ month }: FloatingChatWidgetProps) {
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // UI States
  const [isOpen, setIsOpen] = useState(false);

  // Chat data
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [useStreaming, setUseStreaming] = useState(true);

  // Session management
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoadingSession, setIsLoadingSession] = useState(false);

  // Financial context
  const [financialContext, setFinancialContext] = useState<FinancialContext | null>(null);

  // Load financial context
  const loadFinancialContext = useCallback(async () => {
    try {
      // IMPORTANT: limit=500 pour recuperer TOUTES les transactions du mois
      const [configRes, transactionsRes, budgetsRes, suggestionsRes] = await Promise.all([
        api.get('/config').catch(() => ({ data: {} })),
        api.get(`/transactions?month=${month}&limit=500`).catch(() => ({ data: [] })),
        categoryBudgetsApi.getAll(month).catch(() => []),
        categoryBudgetsApi.getSuggestions(6).catch(() => ({ suggestions: [] }))
      ]);

      const config = configRes?.data || {};
      const transactionsData = transactionsRes?.data || {};
      const transactions = transactionsData.items || transactionsData || [];
      const budgets: CategoryBudget[] = budgetsRes || [];
      const suggestions = suggestionsRes?.suggestions || [];

      // Revenus depuis la config (salaires configures, comme le dashboard)
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
      let budgetStatus = 'equilibre';
      if (savingsRate < 0) budgetStatus = 'deficitaire';
      else if (savingsRate < 10) budgetStatus = 'serre';
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

  // Recharger les données quand le mois change ou quand le widget s'ouvre
  useEffect(() => {
    if (isOpen) {
      loadFinancialContext();
    }
  }, [isOpen, month, loadFinancialContext]);

  // Réinitialiser le contexte et les messages quand le mois change
  useEffect(() => {
    setFinancialContext(null);
    setMessages([]);
  }, [month]);

  // Initialize or restore chat session
  const initializeSession = useCallback(async (forceNew: boolean = false) => {
    setIsLoadingSession(true);
    try {
      const storedSessionId = !forceNew ? localStorage.getItem(SESSION_STORAGE_KEY) : null;

      if (storedSessionId && !forceNew) {
        try {
          const history = await aiApi.getSessionHistory(storedSessionId);
          if (history && history.messages.length > 0) {
            setSessionId(storedSessionId);
            const restoredMessages: ChatMessage[] = history.messages.map(m => ({
              id: m.message_id,
              role: m.role as 'user' | 'assistant',
              content: m.content,
              timestamp: new Date(m.timestamp)
            }));
            setMessages(restoredMessages);
            return;
          }
        } catch (err) {
          console.log('Previous session expired or not found, creating new one');
          localStorage.removeItem(SESSION_STORAGE_KEY);
        }
      }

      const newSession = await aiApi.createSession(month);
      setSessionId(newSession.session_id);
      localStorage.setItem(SESSION_STORAGE_KEY, newSession.session_id);

      if (forceNew) {
        setMessages([]);
      }
    } catch (err) {
      console.error('Failed to initialize session:', err);
      setSessionId(null);
    } finally {
      setIsLoadingSession(false);
    }
  }, [month]);

  // Initialize session when chat opens
  useEffect(() => {
    if (isOpen && !sessionId) {
      initializeSession();
    }
  }, [isOpen, sessionId, initializeSession]);

  // Scroll to bottom of chat
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Initialize chat with welcome message
  useEffect(() => {
    if (messages.length === 0 && financialContext && isOpen) {
      const monthLabel = new Date(month + '-01').toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });

      let budgetLine = '';
      if (financialContext.budgetsDefined && financialContext.budgets.length > 0) {
        const overCount = financialContext.budgets.filter(b => b.status === 'over').length;
        const variance = financialContext.totalExpenses - financialContext.totalBudgeted;
        if (overCount > 0) {
          budgetLine = `\n - ${overCount} categorie(s) en depassement`;
        } else if (variance > 0) {
          budgetLine = `\n - Proche du budget total`;
        } else {
          budgetLine = `\n - Budgets respectes`;
        }
      }

      // Ligne pour les provisions/épargne si présentes
      let provisionLine = '';
      if (financialContext.excludedExpenses > 0) {
        provisionLine = `\n - Provisions/Epargne: ${financialContext.excludedExpenses.toFixed(0)}E (${financialContext.excludedCount} virements)`;
      }

      const welcomeMessage: ChatMessage = {
        id: 'welcome',
        role: 'assistant',
        content: `Bonjour! Je suis votre coach budget.\n\n**${monthLabel}:**\n - Revenus nets: ${financialContext.totalIncome.toFixed(0)}E\n - Depenses courantes: ${financialContext.totalExpenses.toFixed(0)}E${provisionLine}\n - Solde disponible: ${financialContext.savings >= 0 ? '+' : ''}${financialContext.savings.toFixed(0)}E${budgetLine}\n\nComment puis-je vous aider?`,
        timestamp: new Date()
      };
      setMessages([welcomeMessage]);
    }
  }, [financialContext, month, messages.length, isOpen]);

  // Build context prompt for AI
  const buildContextPrompt = (userQuestion: string): string => {
    if (!financialContext) return userQuestion;

    let budgetSection = '';
    if (financialContext.budgetsDefined && financialContext.budgets.length > 0) {
      const overBudget = financialContext.budgets.filter(b => b.status === 'over');
      budgetSection = `
BUDGETS (${financialContext.budgets.length} categories):
- Budget total: ${financialContext.totalBudgeted.toFixed(2)}E
- Depense: ${financialContext.totalExpenses.toFixed(2)}E
${overBudget.length > 0 ? `- DEPASSEMENTS: ${overBudget.map(b => `${b.category} (+${b.variance.toFixed(0)}E)`).join(', ')}` : ''}`;
    }

    // Section provisions/épargne (transactions exclues)
    let provisionSection = '';
    if (financialContext.excludedExpenses > 0) {
      provisionSection = `
PROVISIONS ET EPARGNE (virements compte a compte exclus des depenses courantes):
- Total provisions/epargne: ${financialContext.excludedExpenses.toFixed(2)}E (${financialContext.excludedCount} virements)
- Categories: ${financialContext.topExcludedCategories.map(c => `${c.name}: ${c.amount.toFixed(0)}E`).join(', ')}
Note: Ces montants sont des virements vers des comptes d'epargne (vacances, bebe, etc.) et ne sont pas comptes dans les depenses courantes.`;
    }

    return `
CONTEXTE FINANCIER COMPLET (${month}):
- Revenus nets (salaires apres impots): ${financialContext.totalIncome.toFixed(2)}E
- Depenses courantes (incluses): ${financialContext.totalExpenses.toFixed(2)}E
- Provisions/Epargne (exclues): ${financialContext.excludedExpenses.toFixed(2)}E
- TOTAL SORTIES (depenses + provisions): ${financialContext.allExpensesTotal.toFixed(2)}E
- Solde disponible: ${financialContext.savings.toFixed(2)}E
- Nombre total de transactions: ${financialContext.transactionCount}
- Statut budget: ${financialContext.budgetStatus}

TOP CATEGORIES DEPENSES COURANTES:
${financialContext.topCategories.map((c, i) => `  ${i + 1}. ${c.name}: ${c.amount.toFixed(2)}E`).join('\n')}
${provisionSection}
${budgetSection}

QUESTION DE L'UTILISATEUR: ${userQuestion}

INSTRUCTIONS: Tu es un coach budget familial. Reponds de maniere:
- Personnalisee en utilisant TOUTES les donnees ci-dessus (depenses ET provisions)
- Concise (2-3 paragraphes max)
- Pratique avec des conseils actionnables
- N'hesite pas a mentionner les provisions/epargne si pertinent pour l'analyse
`;
  };

  // Send message to AI
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
      const hasSession = sessionId !== null;
      const question = userMessage.content;

      if (useStreaming) {
        const assistantMsgId = (Date.now() + 1).toString();
        let fullContent = '';

        setMessages(prev => [...prev, {
          id: assistantMsgId,
          role: 'assistant',
          content: '',
          timestamp: new Date()
        }]);

        try {
          const streamGenerator = hasSession
            ? aiApi.sessionStreamChat(sessionId, question, month)
            : aiApi.streamChat(buildContextPrompt(question), month);

          for await (const chunk of streamGenerator) {
            fullContent += chunk;
            setStreamingContent(fullContent);
            setMessages(prev => prev.map(msg =>
              msg.id === assistantMsgId
                ? { ...msg, content: fullContent }
                : msg
            ));
          }
        } catch (streamError) {
          console.warn('Streaming failed, falling back to regular API:', streamError);
          setUseStreaming(false);

          const response = hasSession
            ? await aiApi.sessionChat(sessionId, question, month)
            : await aiApi.askQuestion(buildContextPrompt(question), month);

          const answer = 'answer' in response ? response.answer : '';
          setMessages(prev => prev.map(msg =>
            msg.id === assistantMsgId
              ? { ...msg, content: answer || "Je n'ai pas pu generer une reponse." }
              : msg
          ));
        }
      } else {
        const response = hasSession
          ? await aiApi.sessionChat(sessionId, question, month)
          : await aiApi.askQuestion(buildContextPrompt(question), month);

        const answer = 'answer' in response ? response.answer : '';

        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: answer || "Je n'ai pas pu generer une reponse.",
          timestamp: new Date()
        };

        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (err) {
      console.error('Failed to get AI response:', err);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "Desole, je rencontre un probleme technique.",
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
      setStreamingContent('');
    }
  };

  // Quick questions
  const quickQuestions = [
    "Comment reduire mes depenses?",
    "Analyse mes categories",
    "Ou puis-je economiser?"
  ];

  // Start new conversation
  const startNewConversation = useCallback(async () => {
    await initializeSession(true);
  }, [initializeSession]);

  return (
    <>
      {/* Floating Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-full shadow-lg hover:shadow-xl transform hover:scale-105 transition-all flex items-center justify-center"
          title="Ouvrir le coach IA"
        >
          <ChatBubbleLeftRightIcon className="w-7 h-7" />
          {/* Notification badge */}
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center text-[10px] font-bold">
            ?
          </span>
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-50 w-96 h-[500px] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-gray-200">
          {/* Header */}
          <div className="p-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xl">🤖</span>
              <div>
                <h3 className="font-semibold">Coach Budget IA</h3>
                {sessionId && (
                  <span className="text-xs text-purple-200">Memoire active</span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={startNewConversation}
                disabled={isLoadingSession}
                className="px-2 py-1 text-xs bg-white/20 hover:bg-white/30 rounded-md transition-colors"
                title="Nouvelle conversation"
              >
                {isLoadingSession ? '...' : 'Nouveau'}
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 hover:bg-white/20 rounded-lg transition-colors"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50"
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
                      : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {isTyping && !streamingContent && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 p-3 rounded-xl rounded-bl-sm shadow-sm">
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
          <div className="px-4 py-2 bg-white border-t border-gray-100">
            <div className="flex flex-wrap gap-1.5">
              {quickQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => setInputMessage(q)}
                  className="px-2 py-1 text-xs bg-gray-100 hover:bg-purple-100 hover:text-purple-700 rounded-full text-gray-600 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Input */}
          <div className="p-4 bg-white border-t border-gray-200">
            <div className="flex gap-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="Posez votre question..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-full text-sm focus:outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
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
        </div>
      )}
    </>
  );
}

export default FloatingChatWidget;
