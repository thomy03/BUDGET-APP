'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, Button, Input, LoadingSpinner, Alert } from '../ui';
import {
  CategoryBudget,
  CategoryBudgetCreate,
  CategoryBudgetSuggestion,
  categoryBudgetsApi
} from '../../lib/api';

interface CategoryBudgetsConfigProps {
  currentMonth?: string;
}

export function CategoryBudgetsConfig({ currentMonth }: CategoryBudgetsConfigProps) {
  const [budgets, setBudgets] = useState<CategoryBudget[]>([]);
  const [suggestions, setSuggestions] = useState<CategoryBudgetSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [editingBudget, setEditingBudget] = useState<CategoryBudget | null>(null);
  const [newBudget, setNewBudget] = useState<Partial<CategoryBudgetCreate>>({});
  const [showNewForm, setShowNewForm] = useState(false);

  // Mois selectionne pour les budgets
  const [selectedMonth, setSelectedMonth] = useState(
    currentMonth || new Date().toISOString().slice(0, 7)
  );

  const loadBudgets = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const data = await categoryBudgetsApi.getAll(selectedMonth);
      setBudgets(data);
    } catch (err) {
      console.error('Erreur chargement budgets:', err);
      setError('Erreur lors du chargement des budgets');
    } finally {
      setLoading(false);
    }
  }, [selectedMonth]);

  const loadSuggestions = async () => {
    try {
      setLoadingSuggestions(true);
      const data = await categoryBudgetsApi.getSuggestions(6);
      setSuggestions(data.suggestions);
      setShowSuggestions(true);
    } catch (err) {
      console.error('Erreur chargement suggestions:', err);
      setError('Erreur lors du chargement des suggestions');
    } finally {
      setLoadingSuggestions(false);
    }
  };

  useEffect(() => {
    loadBudgets();
  }, [loadBudgets]);

  const handleCreateBudget = async () => {
    if (!newBudget.category || !newBudget.budget_amount) {
      setError('Veuillez remplir la categorie et le montant');
      return;
    }

    try {
      setSaving(true);
      setError('');
      await categoryBudgetsApi.create({
        category: newBudget.category,
        budget_amount: newBudget.budget_amount,
        month: selectedMonth,
        alert_threshold: newBudget.alert_threshold || 0.8,
        notes: newBudget.notes
      });
      setSuccess('Budget cree avec succes');
      setNewBudget({});
      setShowNewForm(false);
      await loadBudgets();
    } catch (err: any) {
      console.error('Erreur creation budget:', err);
      setError(err.response?.data?.detail || 'Erreur lors de la creation');
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateBudget = async () => {
    if (!editingBudget) return;

    try {
      setSaving(true);
      setError('');
      await categoryBudgetsApi.update(editingBudget.id, {
        budget_amount: editingBudget.budget_amount,
        alert_threshold: editingBudget.alert_threshold,
        notes: editingBudget.notes
      });
      setSuccess('Budget mis a jour');
      setEditingBudget(null);
      await loadBudgets();
    } catch (err: any) {
      console.error('Erreur mise a jour budget:', err);
      setError(err.response?.data?.detail || 'Erreur lors de la mise a jour');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteBudget = async (id: number) => {
    if (!confirm('Supprimer ce budget ?')) return;

    try {
      setSaving(true);
      await categoryBudgetsApi.delete(id);
      setSuccess('Budget supprime');
      await loadBudgets();
    } catch (err) {
      console.error('Erreur suppression budget:', err);
      setError('Erreur lors de la suppression');
    } finally {
      setSaving(false);
    }
  };

  const handleApplySuggestion = async (suggestion: CategoryBudgetSuggestion) => {
    // Verifier si un budget existe deja pour cette categorie
    const existing = budgets.find(b => b.category === suggestion.category);
    if (existing) {
      setError(`Un budget existe deja pour "${suggestion.category}"`);
      return;
    }

    try {
      setSaving(true);
      await categoryBudgetsApi.create({
        category: suggestion.category,
        budget_amount: suggestion.suggested_amount,
        month: selectedMonth,
        alert_threshold: 0.8,
        notes: `Suggere depuis historique (${suggestion.months_with_data} mois)`
      });
      setSuccess(`Budget "${suggestion.category}" cree`);
      await loadBudgets();
    } catch (err: any) {
      console.error('Erreur application suggestion:', err);
      setError(err.response?.data?.detail || 'Erreur lors de l\'application');
    } finally {
      setSaving(false);
    }
  };

  const handleApplyAllSuggestions = async () => {
    const minAmount = 50;
    const toApply = suggestions.filter(s =>
      s.suggested_amount >= minAmount &&
      !budgets.find(b => b.category === s.category)
    );

    if (toApply.length === 0) {
      setError('Aucune suggestion applicable');
      return;
    }

    try {
      setSaving(true);
      await categoryBudgetsApi.applySuggestions(selectedMonth, minAmount);
      setSuccess(`${toApply.length} budgets crees depuis les suggestions`);
      setShowSuggestions(false);
      await loadBudgets();
    } catch (err) {
      console.error('Erreur application suggestions:', err);
      setError('Erreur lors de l\'application des suggestions');
    } finally {
      setSaving(false);
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing': return '📈';
      case 'decreasing': return '📉';
      default: return '➡️';
    }
  };

  const totalBudgeted = budgets.reduce((sum, b) => sum + b.budget_amount, 0);

  return (
    <div className="space-y-6">
      {/* Header avec selection du mois */}
      <Card>
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                💰 Budgets par Categorie
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Definissez des objectifs de depenses par tag/categorie
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600 dark:text-gray-400">Mois:</label>
                <input
                  type="month"
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Resume */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Budget total planifie</p>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {totalBudgeted.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600 dark:text-gray-400">{budgets.length} categories</p>
                <p className="text-lg font-semibold text-gray-700 dark:text-gray-300">budgetees</p>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Alerts */}
      {error && (
        <Alert variant="error" className="mb-4">
          {error}
          <button onClick={() => setError('')} className="ml-2 text-red-800 hover:text-red-900">×</button>
        </Alert>
      )}
      {success && (
        <Alert variant="success" className="mb-4">
          {success}
          <button onClick={() => setSuccess('')} className="ml-2 text-green-800 hover:text-green-900">×</button>
        </Alert>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          onClick={() => setShowNewForm(!showNewForm)}
          className="bg-blue-600 hover:bg-blue-700 text-white"
        >
          + Nouveau budget
        </Button>
        <Button
          onClick={loadSuggestions}
          variant="outline"
          disabled={loadingSuggestions}
          className="flex items-center gap-2"
        >
          {loadingSuggestions ? <LoadingSpinner size="sm" /> : '🤖'}
          Suggestions IA
        </Button>
      </div>

      {/* Formulaire nouveau budget */}
      {showNewForm && (
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold mb-4">Nouveau budget</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Categorie / Tag
                </label>
                <Input
                  value={newBudget.category || ''}
                  onChange={(e) => setNewBudget({ ...newBudget, category: e.target.value })}
                  placeholder="ex: courses, transport..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Budget mensuel (EUR)
                </label>
                <Input
                  type="number"
                  min="0"
                  step="10"
                  value={newBudget.budget_amount || ''}
                  onChange={(e) => setNewBudget({ ...newBudget, budget_amount: parseFloat(e.target.value) })}
                  placeholder="500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Seuil d'alerte (%)
                </label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={(newBudget.alert_threshold || 0.8) * 100}
                  onChange={(e) => setNewBudget({ ...newBudget, alert_threshold: parseFloat(e.target.value) / 100 })}
                  placeholder="80"
                />
              </div>
            </div>
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Notes (optionnel)
              </label>
              <Input
                value={newBudget.notes || ''}
                onChange={(e) => setNewBudget({ ...newBudget, notes: e.target.value })}
                placeholder="Notes sur ce budget..."
              />
            </div>
            <div className="flex gap-3 mt-4">
              <Button
                onClick={handleCreateBudget}
                disabled={saving}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                {saving ? 'Creation...' : 'Creer'}
              </Button>
              <Button
                onClick={() => { setShowNewForm(false); setNewBudget({}); }}
                variant="outline"
              >
                Annuler
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Suggestions IA */}
      {showSuggestions && suggestions.length > 0 && (
        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                🤖 Suggestions basees sur l'historique
              </h3>
              <div className="flex gap-2">
                <Button
                  onClick={handleApplyAllSuggestions}
                  disabled={saving}
                  className="bg-purple-600 hover:bg-purple-700 text-white text-sm"
                >
                  Appliquer toutes (≥50EUR)
                </Button>
                <Button
                  onClick={() => setShowSuggestions(false)}
                  variant="outline"
                  className="text-sm"
                >
                  Fermer
                </Button>
              </div>
            </div>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {suggestions.map((suggestion, idx) => {
                const alreadyExists = budgets.find(b => b.category === suggestion.category);
                return (
                  <div
                    key={idx}
                    className={`flex items-center justify-between p-3 rounded-lg border ${
                      alreadyExists
                        ? 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 opacity-60'
                        : 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-blue-900/20'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-lg">{getTrendIcon(suggestion.trend)}</span>
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white capitalize">
                          {suggestion.category}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          Moy. 3 mois: {suggestion.average_3_months.toFixed(0)}EUR |
                          Min: {suggestion.min_amount.toFixed(0)}EUR |
                          Max: {suggestion.max_amount.toFixed(0)}EUR
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <p className="font-bold text-blue-600 dark:text-blue-400">
                          {suggestion.suggested_amount.toFixed(0)}EUR
                        </p>
                        <p className="text-xs text-gray-500">suggere</p>
                      </div>
                      {alreadyExists ? (
                        <span className="px-3 py-1 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded text-sm">
                          Existe
                        </span>
                      ) : (
                        <Button
                          onClick={() => handleApplySuggestion(suggestion)}
                          disabled={saving}
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm"
                        >
                          Ajouter
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </Card>
      )}

      {/* Liste des budgets */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            Budgets pour {new Date(selectedMonth + '-01').toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}
          </h3>

          {loading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner text="Chargement des budgets..." />
            </div>
          ) : budgets.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <p className="text-4xl mb-3">📊</p>
              <p className="mb-2">Aucun budget defini pour ce mois</p>
              <p className="text-sm">Utilisez les suggestions IA ou creez un nouveau budget</p>
            </div>
          ) : (
            <div className="space-y-3">
              {budgets.map((budget) => (
                <div
                  key={budget.id}
                  className={`border rounded-lg p-4 transition-all ${
                    budget.is_active
                      ? 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 hover:shadow-sm'
                      : 'bg-gray-50 dark:bg-gray-800 border-gray-100 dark:border-gray-700 opacity-60'
                  }`}
                >
                  {editingBudget?.id === budget.id ? (
                    // Mode edition
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium mb-1">Budget (EUR)</label>
                          <Input
                            type="number"
                            value={editingBudget.budget_amount}
                            onChange={(e) => setEditingBudget({
                              ...editingBudget,
                              budget_amount: parseFloat(e.target.value)
                            })}
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1">Seuil alerte (%)</label>
                          <Input
                            type="number"
                            min="0"
                            max="100"
                            value={(editingBudget.alert_threshold || 0.8) * 100}
                            onChange={(e) => setEditingBudget({
                              ...editingBudget,
                              alert_threshold: parseFloat(e.target.value) / 100
                            })}
                          />
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          onClick={handleUpdateBudget}
                          disabled={saving}
                          className="bg-green-600 hover:bg-green-700 text-white text-sm"
                        >
                          Sauver
                        </Button>
                        <Button
                          onClick={() => setEditingBudget(null)}
                          variant="outline"
                          className="text-sm"
                        >
                          Annuler
                        </Button>
                      </div>
                    </div>
                  ) : (
                    // Mode affichage
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                          <span className="text-blue-600 dark:text-blue-400 font-bold">
                            {budget.category.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <h4 className="font-medium text-gray-900 dark:text-white capitalize">
                            {budget.category}
                          </h4>
                          {budget.notes && (
                            <p className="text-xs text-gray-500 dark:text-gray-400">{budget.notes}</p>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="font-bold text-gray-900 dark:text-white">
                            {budget.budget_amount.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            Alerte a {((budget.alert_threshold || 0.8) * 100).toFixed(0)}%
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          <Button
                            onClick={() => setEditingBudget(budget)}
                            variant="outline"
                            className="px-2 py-1 text-sm"
                          >
                            ✏️
                          </Button>
                          <Button
                            onClick={() => handleDeleteBudget(budget.id)}
                            variant="outline"
                            className="px-2 py-1 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                          >
                            🗑️
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
