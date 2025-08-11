'use client';

import React from 'react';
import { Summary, ConfigOut, CustomProvision, FixedLine } from '../../lib/api';
import { 
  calculateProvisionMonthlyAmount,
  calculateProvisionMemberSplit,
  calculateMonthlyAmount,
  calculateMemberSplit,
  BudgetItem
} from '../../lib/dashboard-calculations';
import { Card } from '../ui';

interface DetailedBudgetTableProps {
  summary: Summary;
  config: ConfigOut;
  provisions: CustomProvision[];
  fixedExpenses: FixedLine[];
  month: string;
}

const DetailedBudgetTable = React.memo<DetailedBudgetTableProps>(({ 
  summary, 
  config, 
  provisions, 
  fixedExpenses, 
  month 
}) => {
  const activeProvisions = provisions.filter(p => p.is_active);
  const activeFixedExpenses = fixedExpenses.filter(e => e.active);

  // Calculate provisions breakdown
  const provisionsData = activeProvisions.map(provision => {
    const monthlyAmount = calculateProvisionMonthlyAmount(provision, config);
    const split = calculateProvisionMemberSplit(provision, monthlyAmount, config);
    return {
      name: `${provision.icon} ${provision.name}`,
      member1: typeof split.member1 === 'number' && !isNaN(split.member1) ? split.member1 : 0,
      member2: typeof split.member2 === 'number' && !isNaN(split.member2) ? split.member2 : 0,
      type: 'provision' as const
    };
  });

  // Calculate fixed expenses breakdown
  const fixedExpensesData = activeFixedExpenses.map(expense => {
    const monthlyAmount = calculateMonthlyAmount(expense);
    const split = calculateMemberSplit(expense, monthlyAmount, config);
    return {
      name: expense.label,
      member1: typeof split.member1 === 'number' && !isNaN(split.member1) ? split.member1 : 0,
      member2: typeof split.member2 === 'number' && !isNaN(split.member2) ? split.member2 : 0,
      type: 'fixed' as const
    };
  });

  // Transactions data from summary.detail
  const transactionsData = Object.entries(summary.detail || {}).map(([poste, byMember]) => ({
    name: poste,
    member1: typeof (byMember as any)[config.member1] === 'number' ? (byMember as any)[config.member1] : 0,
    member2: typeof (byMember as any)[config.member2] === 'number' ? (byMember as any)[config.member2] : 0,
    type: 'variable' as const
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
                  {(typeof grandTotal.member1 === 'number' && !isNaN(grandTotal.member1) ? grandTotal.member1 : 0).toFixed(2)} €
                </td>
                <td className="p-4 text-right font-bold text-purple-900 text-base font-mono">
                  {(typeof grandTotal.member2 === 'number' && !isNaN(grandTotal.member2) ? grandTotal.member2 : 0).toFixed(2)} €
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </section>
  );
});

DetailedBudgetTable.displayName = 'DetailedBudgetTable';

// Helper components for the table
const SectionHeader = React.memo<{ title: string }>(({ title }) => {
  return (
    <tr>
      <td colSpan={3} className="p-3 bg-zinc-100 font-semibold text-zinc-700 border-t-2 border-zinc-200">
        {title}
      </td>
    </tr>
  );
});

SectionHeader.displayName = 'SectionHeader';

const DataRow = React.memo<{ 
  item: BudgetItem;
  isProvision?: boolean;
  isFixed?: boolean;
  isVariable?: boolean;
}>(({ item, isProvision = false, isFixed = false, isVariable = false }) => {
  let bgColor = 'hover:bg-zinc-50';
  if (isProvision) bgColor = 'hover:bg-indigo-25';
  if (isFixed) bgColor = 'hover:bg-emerald-25';
  if (isVariable) bgColor = 'hover:bg-blue-25';

  return (
    <tr className={`border-t border-zinc-100 ${bgColor} transition-colors`}>
      <td className="p-3 pl-6">{item.name}</td>
      <td className="p-3 text-right font-mono text-zinc-700">{(typeof item.member1 === 'number' && !isNaN(item.member1) ? item.member1 : 0).toFixed(2)} €</td>
      <td className="p-3 text-right font-mono text-zinc-700">{(typeof item.member2 === 'number' && !isNaN(item.member2) ? item.member2 : 0).toFixed(2)} €</td>
    </tr>
  );
});

DataRow.displayName = 'DataRow';

const SubtotalRow = React.memo<{ 
  title: string; 
  subtotal: { member1: number; member2: number }; 
  bgColor: string;
  textColor: string;
}>(({ title, subtotal, bgColor, textColor }) => {
  return (
    <tr className={`border-t border-zinc-200 ${bgColor}`}>
      <td className={`p-3 pl-6 font-semibold ${textColor}`}>{title}</td>
      <td className={`p-3 text-right font-bold font-mono ${textColor}`}>
        {(typeof subtotal.member1 === 'number' && !isNaN(subtotal.member1) ? subtotal.member1 : 0).toFixed(2)} €
      </td>
      <td className={`p-3 text-right font-bold font-mono ${textColor}`}>
        {(typeof subtotal.member2 === 'number' && !isNaN(subtotal.member2) ? subtotal.member2 : 0).toFixed(2)} €
      </td>
    </tr>
  );
});

SubtotalRow.displayName = 'SubtotalRow';

export default DetailedBudgetTable;