'use client';

import { Tx } from '../../lib/api';
import { TransactionRow } from './TransactionRow';

interface TransactionsTableProps {
  rows: Tx[];
  importId: string | null;
  calculations: {
    totalAmount: number;
    includedCount: number;
    excludedCount: number;
    totalIncome: number;
    totalExpenses: number;
  };
  onToggle: (id: number, exclude: boolean) => void;
  onSaveTags: (id: number, tagsCSV: string) => void;
}

export function TransactionsTable({ 
  rows, 
  importId, 
  calculations, 
  onToggle, 
  onSaveTags 
}: TransactionsTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-200">
            <th className="text-left p-3 font-medium">Date</th>
            <th className="text-left p-3 font-medium">Libellé</th>
            <th className="text-left p-3 font-medium">Catégorie</th>
            <th className="text-right p-3 font-medium">Montant</th>
            <th className="text-center p-3 font-medium">Exclure</th>
            <th className="text-left p-3 font-medium">Tags</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <TransactionRow
              key={row.id}
              row={row}
              importId={importId}
              onToggle={onToggle}
              onSaveTags={onSaveTags}
            />
          ))}
        </tbody>
        {/* Ligne de totaux */}
        {rows.length > 0 && (
          <tfoot>
            <tr className="border-t-2 border-gray-300 bg-gray-50">
              <td className="p-3 font-medium text-gray-700" colSpan={3}>
                <div className="flex items-center justify-between">
                  <span>TOTAUX DU MOIS</span>
                  <span className="text-sm text-gray-600">
                    {calculations.includedCount} incluses, {calculations.excludedCount} exclues
                  </span>
                </div>
              </td>
              <td className="p-3 text-right font-bold text-lg">
                <span className={calculations.totalAmount >= 0 ? "text-green-600" : "text-red-600"}>
                  {calculations.totalAmount >= 0 ? "+" : ""}{calculations.totalAmount.toFixed(2)} €
                </span>
              </td>
              <td className="p-3" colSpan={2}>
                <div className="text-xs text-gray-600 space-y-1">
                  <div>Revenus: +{calculations.totalIncome.toFixed(2)} €</div>
                  <div>Dépenses: -{calculations.totalExpenses.toFixed(2)} €</div>
                </div>
              </td>
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  );
}
