'use client';

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Summary, ConfigOut, CustomProvision, FixedLine } from "../lib/api";
import { useGlobalMonth } from "../lib/month";
import { useAuth } from "../lib/auth";
import { LoadingSpinner, Card, Button } from "../components/ui";
import ProvisionsWidget from "../components/ProvisionsWidget";

// Test comment to verify cache clearance - Clean restart working
export default function Page() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [month] = useGlobalMonth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [cfg, setCfg] = useState<ConfigOut | null>(null);
  const [provisions, setProvisions] = useState<CustomProvision[]>([]);
  const [fixedExpenses, setFixedExpenses] = useState<FixedLine[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Redirection si non authentifié
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

  const load = async () => {
    if (!isAuthenticated) return;
    
    console.log('📊 Dashboard - Loading data for month:', month);
    try {
      setLoading(true);
      setError("");
      
      const [configResponse, summaryResponse, provisionsResponse, fixedExpensesResponse] = await Promise.all([
        api.get<ConfigOut>("/config"),
        api.get<Summary>("/summary", { params: { month } }),
        api.get<CustomProvision[]>("/custom-provisions"),
        api.get<FixedLine[]>("/fixed-lines")
      ]);
      
      console.log('✅ Dashboard - Data loaded for month:', month);
      setCfg(configResponse.data);
      setSummary(summaryResponse.data);
      setProvisions(provisionsResponse.data || []);
      setFixedExpenses(fixedExpensesResponse.data || []);
    } catch (err: any) {
      setError("Erreur lors du chargement des données");
      console.error("❌ Dashboard - Load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    console.log('🔄 Dashboard useEffect - Month:', month, 'Auth:', isAuthenticated);
    if (isAuthenticated) {
      load();
    }
  }, [month, isAuthenticated]);

  // Affichage du loader pendant l'authentification
  if (authLoading) {
    return (
      <div className="container py-12 flex justify-center">
        <LoadingSpinner size="lg" text="Chargement..." />
      </div>
    );
  }

  // Ne rien afficher si non authentifié (redirection en cours)
  if (!isAuthenticated) {
    return null;
  }

  return (
    <main className="container py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="h1">Tableau de bord</h1>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl">
          {error}
        </div>
      )}

      {summary && cfg ? (
        <>
          {/* Key Metrics */}
          <KeyMetrics 
            summary={summary} 
            config={cfg} 
            provisions={provisions} 
            fixedExpenses={fixedExpenses}
          />

          {/* Provisions Widget */}
          <ProvisionsWidget config={cfg} />

          {/* Detailed Budget Table */}
          <DetailedBudgetTable 
            summary={summary} 
            config={cfg} 
            provisions={provisions} 
            fixedExpenses={fixedExpenses}
            month={month}
          />
        </>
      ) : (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" text="Chargement des données..." />
        </div>
      )}
    </main>
  );
}

// Interfaces for component props
interface KeyMetricsProps {
  summary: Summary;
  config: ConfigOut;
  provisions: CustomProvision[];
  fixedExpenses: FixedLine[];
}

interface DetailedBudgetTableProps {
  summary: Summary;
  config: ConfigOut;
  provisions: CustomProvision[];
  fixedExpenses: FixedLine[];
  month: string;
}

// Utility functions
function calculateMonthlyAmount(expense: FixedLine): number {
  switch (expense.freq) {
    case 'mensuelle':
      return expense.amount;
    case 'trimestrielle':
      return expense.amount / 3;
    case 'annuelle':
      return expense.amount / 12;
    default:
      return expense.amount;
  }
}

function calculateProvisionMonthlyAmount(provision: CustomProvision, config: ConfigOut): number {
  let base = 0;
  switch (provision.base_calculation) {
    case 'total':
      base = (config.rev1 || 0) + (config.rev2 || 0);
      break;
    case 'member1':
      base = config.rev1 || 0;
      break;
    case 'member2':
      base = config.rev2 || 0;
      break;
    case 'fixed':
      return provision.fixed_amount || 0;
  }
  return (base * provision.percentage / 100) / 12;
}

function calculateMemberSplit(expense: FixedLine, monthlyAmount: number, config: ConfigOut) {
  switch (expense.split_mode) {
    case 'clé':
      const totalRev = (config.rev1 || 0) + (config.rev2 || 0);
      if (totalRev > 0) {
        const r1 = (config.rev1 || 0) / totalRev;
        const r2 = (config.rev2 || 0) / totalRev;
        return { member1: monthlyAmount * r1, member2: monthlyAmount * r2 };
      }
      return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
    case '50/50':
      return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
    case 'm1':
      return { member1: monthlyAmount, member2: 0 };
    case 'm2':
      return { member1: 0, member2: monthlyAmount };
    case 'manuel':
      return { member1: monthlyAmount * expense.split1, member2: monthlyAmount * expense.split2 };
    default:
      return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
  }
}

function calculateProvisionMemberSplit(provision: CustomProvision, monthlyAmount: number, config: ConfigOut) {
  switch (provision.split_mode) {
    case 'key':
      const totalRev = (config.rev1 || 0) + (config.rev2 || 0);
      if (totalRev > 0) {
        const r1 = (config.rev1 || 0) / totalRev;
        const r2 = (config.rev2 || 0) / totalRev;
        return { member1: monthlyAmount * r1, member2: monthlyAmount * r2 };
      }
      return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
    case '50/50':
      return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
    case '100/0':
      return { member1: monthlyAmount, member2: 0 };
    case '0/100':
      return { member1: 0, member2: monthlyAmount };
    case 'custom':
      return {
        member1: monthlyAmount * (provision.split_member1 / 100),
        member2: monthlyAmount * (provision.split_member2 / 100)
      };
    default:
      return { member1: monthlyAmount * 0.5, member2: monthlyAmount * 0.5 };
  }
}

// Key Metrics Component
function KeyMetrics({ summary, config, provisions, fixedExpenses }: KeyMetricsProps) {
  // Calculate provisions total
  const activeProvisions = provisions.filter(p => p.is_active);
  const totalProvisions = activeProvisions.reduce((sum, provision) => {
    return sum + calculateProvisionMonthlyAmount(provision, config);
  }, 0);

  // Calculate fixed expenses total
  const activeFixedExpenses = fixedExpenses.filter(e => e.active);
  const totalFixedExpenses = activeFixedExpenses.reduce((sum, expense) => {
    return sum + calculateMonthlyAmount(expense);
  }, 0);

  // Variables from transactions
  const totalVariables = summary.var_total;

  // Budget overview
  const budgetTotal = totalProvisions + totalFixedExpenses + totalVariables;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard 
        title="Total Provisions" 
        value={totalProvisions} 
        color="indigo" 
        icon="🎯"
        subtitle={`${activeProvisions.length} provision${activeProvisions.length > 1 ? 's' : ''}`}
      />
      <MetricCard 
        title="Charges Fixes" 
        value={totalFixedExpenses} 
        color="emerald" 
        icon="💳"
        subtitle={`${activeFixedExpenses.length} dépense${activeFixedExpenses.length > 1 ? 's' : ''}`}
      />
      <MetricCard 
        title="Variables" 
        value={totalVariables} 
        color="blue" 
        icon="📊"
        subtitle="Transactions bancaires"
      />
      <MetricCard 
        title="Budget Total" 
        value={budgetTotal} 
        color="purple" 
        icon="📈"
        subtitle="Vision d'ensemble"
        isTotal
      />
    </div>
  );
}

// Individual metric card
function MetricCard({ 
  title, 
  value, 
  color, 
  icon, 
  subtitle, 
  isTotal = false 
}: { 
  title: string; 
  value: number; 
  color: string; 
  icon: string;
  subtitle?: string;
  isTotal?: boolean;
}) {
  const colorClasses = {
    indigo: 'border-l-indigo-500 bg-gradient-to-r from-indigo-50 to-indigo-100 text-indigo-900',
    emerald: 'border-l-emerald-500 bg-gradient-to-r from-emerald-50 to-emerald-100 text-emerald-900',
    blue: 'border-l-blue-500 bg-gradient-to-r from-blue-50 to-blue-100 text-blue-900',
    purple: 'border-l-purple-500 bg-gradient-to-r from-purple-50 to-purple-100 text-purple-900'
  };

  return (
    <Card className={`p-4 border-l-4 ${colorClasses[color as keyof typeof colorClasses]} ${
      isTotal ? 'ring-2 ring-purple-200 shadow-lg' : ''
    }`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-lg">{icon}</span>
        {isTotal && <span className="text-xs font-medium px-2 py-1 bg-purple-200 rounded-full">TOTAL</span>}
      </div>
      <div className="text-sm font-medium mb-1">{title}</div>
      <div className={`text-xl font-bold ${isTotal ? 'text-2xl' : ''}`}>{value.toFixed(2)} €</div>
      {subtitle && <div className="text-xs opacity-75 mt-1">{subtitle}</div>}
    </Card>
  );
}

// Detailed Budget Table Component
function DetailedBudgetTable({ summary, config, provisions, fixedExpenses, month }: DetailedBudgetTableProps) {
  const activeProvisions = provisions.filter(p => p.is_active);
  const activeFixedExpenses = fixedExpenses.filter(e => e.active);

  // Calculate provisions breakdown
  const provisionsData = activeProvisions.map(provision => {
    const monthlyAmount = calculateProvisionMonthlyAmount(provision, config);
    const split = calculateProvisionMemberSplit(provision, monthlyAmount, config);
    return {
      name: `${provision.icon} ${provision.name}`,
      member1: split.member1,
      member2: split.member2,
      type: 'provision'
    };
  });

  // Calculate fixed expenses breakdown
  const fixedExpensesData = activeFixedExpenses.map(expense => {
    const monthlyAmount = calculateMonthlyAmount(expense);
    const split = calculateMemberSplit(expense, monthlyAmount, config);
    return {
      name: expense.label,
      member1: split.member1,
      member2: split.member2,
      type: 'fixed'
    };
  });

  // Transactions data from summary.detail
  const transactionsData = Object.entries(summary.detail).map(([poste, byMember]) => ({
    name: poste,
    member1: (byMember as any)[config.member1] || 0,
    member2: (byMember as any)[config.member2] || 0,
    type: 'variable'
  }));

  // Calculate subtotals
  const provisionsSubtotal = {
    member1: provisionsData.reduce((sum, item) => sum + item.member1, 0),
    member2: provisionsData.reduce((sum, item) => sum + item.member2, 0)
  };

  const fixedExpensesSubtotal = {
    member1: fixedExpensesData.reduce((sum, item) => sum + item.member1, 0),
    member2: fixedExpensesData.reduce((sum, item) => sum + item.member2, 0)
  };

  const variablesSubtotal = {
    member1: transactionsData.reduce((sum, item) => sum + item.member1, 0),
    member2: transactionsData.reduce((sum, item) => sum + item.member2, 0)
  };

  const grandTotal = {
    member1: provisionsSubtotal.member1 + fixedExpensesSubtotal.member1 + variablesSubtotal.member1,
    member2: provisionsSubtotal.member2 + fixedExpensesSubtotal.member2 + variablesSubtotal.member2
  };

  return (
    <section>
      <Card padding="lg">
        <h2 className="h2 mb-6 flex items-center">
          <span className="mr-2">📊</span>
          Détail par poste — {month}
        </h2>
        
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-zinc-200">
                <th className="text-left p-3 font-semibold text-zinc-700">Poste</th>
                <th className="text-right p-3 font-semibold text-zinc-700">{summary.member1}</th>
                <th className="text-right p-3 font-semibold text-zinc-700">{summary.member2}</th>
              </tr>
            </thead>
            <tbody>
              {/* Provisions Section */}
              {provisionsData.length > 0 && (
                <>
                  <SectionHeader title="🎯 PROVISIONS" />
                  {provisionsData.map((item, index) => (
                    <DataRow key={`provision-${index}`} item={item} isProvision />
                  ))}
                  <SubtotalRow 
                    title="Sous-total Provisions" 
                    subtotal={provisionsSubtotal} 
                    bgColor="bg-indigo-50" 
                    textColor="text-indigo-900"
                  />
                </>
              )}

              {/* Fixed Expenses Section */}
              {fixedExpensesData.length > 0 && (
                <>
                  <SectionHeader title="💳 CHARGES FIXES" />
                  {fixedExpensesData.map((item, index) => (
                    <DataRow key={`fixed-${index}`} item={item} isFixed />
                  ))}
                  <SubtotalRow 
                    title="Sous-total Charges Fixes" 
                    subtotal={fixedExpensesSubtotal} 
                    bgColor="bg-emerald-50" 
                    textColor="text-emerald-900"
                  />
                </>
              )}

              {/* Variables Section */}
              {transactionsData.length > 0 && (
                <>
                  <SectionHeader title="📈 VARIABLES" />
                  {transactionsData.map((item, index) => (
                    <DataRow key={`variable-${index}`} item={item} isVariable />
                  ))}
                  <SubtotalRow 
                    title="Sous-total Variables" 
                    subtotal={variablesSubtotal} 
                    bgColor="bg-blue-50" 
                    textColor="text-blue-900"
                  />
                </>
              )}

              {/* Grand Total */}
              <tr className="border-t-2 border-zinc-300 bg-gradient-to-r from-purple-100 to-purple-200">
                <td className="p-4 font-bold text-purple-900 text-base">🏆 TOTAL GÉNÉRAL</td>
                <td className="p-4 text-right font-bold text-purple-900 text-base font-mono">
                  {grandTotal.member1.toFixed(2)} €
                </td>
                <td className="p-4 text-right font-bold text-purple-900 text-base font-mono">
                  {grandTotal.member2.toFixed(2)} €
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </section>
  );
}

// Helper components for the table
function SectionHeader({ title }: { title: string }) {
  return (
    <tr>
      <td colSpan={3} className="p-3 bg-zinc-100 font-semibold text-zinc-700 border-t-2 border-zinc-200">
        {title}
      </td>
    </tr>
  );
}

function DataRow({ item, isProvision = false, isFixed = false, isVariable = false }: { 
  item: { name: string; member1: number; member2: number; type: string };
  isProvision?: boolean;
  isFixed?: boolean;
  isVariable?: boolean;
}) {
  let bgColor = 'hover:bg-zinc-50';
  if (isProvision) bgColor = 'hover:bg-indigo-25';
  if (isFixed) bgColor = 'hover:bg-emerald-25';
  if (isVariable) bgColor = 'hover:bg-blue-25';

  return (
    <tr className={`border-t border-zinc-100 ${bgColor} transition-colors`}>
      <td className="p-3 pl-6">{item.name}</td>
      <td className="p-3 text-right font-mono text-zinc-700">{item.member1.toFixed(2)} €</td>
      <td className="p-3 text-right font-mono text-zinc-700">{item.member2.toFixed(2)} €</td>
    </tr>
  );
}

function SubtotalRow({ 
  title, 
  subtotal, 
  bgColor, 
  textColor 
}: { 
  title: string; 
  subtotal: { member1: number; member2: number }; 
  bgColor: string;
  textColor: string;
}) {
  return (
    <tr className={`border-t border-zinc-200 ${bgColor}`}>
      <td className={`p-3 pl-6 font-semibold ${textColor}`}>{title}</td>
      <td className={`p-3 text-right font-bold font-mono ${textColor}`}>
        {subtotal.member1.toFixed(2)} €
      </td>
      <td className={`p-3 text-right font-bold font-mono ${textColor}`}>
        {subtotal.member2.toFixed(2)} €
      </td>
    </tr>
  );
}
