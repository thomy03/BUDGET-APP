'use client';

import { Tx } from '../../lib/api';

interface TransactionRowProps {
  row: Tx;
  importId: string | null;
  onToggle: (id: number, exclude: boolean) => void;
  onSaveTags: (id: number, tagsCSV: string) => void;
}

export function TransactionRow({ row, importId, onToggle, onSaveTags }: TransactionRowProps) {
  const isHighlighted = importId && row.import_id === importId;
  
  return (
    <tr 
      className={`border-t border-zinc-100 hover:bg-zinc-50 ${
        isHighlighted ? 'bg-green-50 border-green-200' : ''
      }`}
    >
      <td className="p-3">{row.date_op}</td>
      <td className="p-3">
        <div className="flex items-center gap-2">
          {row.label}
          {isHighlighted && (
            <span className="px-2 py-1 text-xs bg-green-200 text-green-800 rounded-full">
              Nouveau
            </span>
          )}
        </div>
      </td>
      <td className="p-3">
        <span className="text-xs bg-zinc-100 px-2 py-1 rounded-full">
          {row.category}
        </span>
      </td>
      <td className="p-3 text-right font-mono">
        <span className={row.amount < 0 ? "text-red-600" : "text-green-600"}>
          {row.amount < 0 ? "-" : "+"}{Math.abs(row.amount).toFixed(2)} €
        </span>
      </td>
      <td className="p-3 text-center">
        <input 
          type="checkbox" 
          checked={row.exclude} 
          onChange={e => onToggle(row.id, e.target.checked)}
          className="rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900"
        />
      </td>
      <td className="p-3">
        <input 
          className="w-full px-2 py-1 border border-zinc-200 rounded text-sm focus:ring-1 focus:ring-zinc-900 focus:border-transparent" 
          defaultValue={Array.isArray(row.tags) ? row.tags.join(", ") : (row.tags || "")} 
          onBlur={e => onSaveTags(row.id, e.target.value)} 
          placeholder="courses, resto, santé…" 
        />
      </td>
    </tr>
  );
}
