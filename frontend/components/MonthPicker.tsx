'use client';

import { usePathname } from 'next/navigation';
import { useGlobalMonth, useGlobalMonthWithUrl } from '../lib/month';

export default function MonthPicker() {
  const pathname = usePathname();
  
  // Utiliser le hook approprié selon la page
  // Sur /transactions, on synchronise avec l'URL
  const isTransactionsPage = pathname === '/transactions';
  const [month, setMonth] = isTransactionsPage 
    ? useGlobalMonthWithUrl() 
    : useGlobalMonth();

  console.log('📅 MonthPicker render - Page:', pathname, 'Month:', month, 'URL sync:', isTransactionsPage);

  const navigateMonth = (direction: 'prev' | 'next') => {
    const currentDate = new Date(month + "-01");
    const offset = direction === 'prev' ? -1 : 1;
    currentDate.setMonth(currentDate.getMonth() + offset);
    const newMonth = currentDate.toISOString().slice(0, 7);
    
    console.log('📅 MonthPicker navigation:', direction, month, '->', newMonth, 'on page:', pathname);
    setMonth(newMonth);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newMonth = e.target.value;
    console.log('📅 MonthPicker input change:', month, '->', newMonth, 'on page:', pathname);
    setMonth(newMonth);
  };

  return (
    <div className="flex items-center justify-center">
      {/* Container moderne avec design épuré */}
      <div className="flex items-center bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl shadow-md border border-blue-200/50 p-2 gap-1">
        
        {/* Bouton précédent moderne */}
        <button
          onClick={() => navigateMonth('prev')}
          className="w-10 h-10 flex items-center justify-center rounded-xl bg-white shadow-sm hover:shadow-md hover:bg-blue-50 transition-all duration-200 text-slate-700 hover:text-blue-600 font-semibold"
          title="Mois précédent"
        >
          ‹
        </button>

        {/* Sélecteur de mois moderne et visible */}
        <input
          type="month"
          value={month}
          onChange={handleInputChange}
          className="mx-3 px-4 py-2.5 bg-white rounded-xl shadow-sm border-0 font-semibold text-slate-800 text-center min-w-[160px] focus:outline-none focus:ring-2 focus:ring-blue-400 focus:shadow-md transition-all duration-200 cursor-pointer hover:shadow-md month-picker-modern"
          style={{
            colorScheme: 'light',
            fontSize: '15px',
            fontWeight: '600'
          }}
        />

        {/* Bouton suivant moderne */}
        <button
          onClick={() => navigateMonth('next')}
          className="w-10 h-10 flex items-center justify-center rounded-xl bg-white shadow-sm hover:shadow-md hover:bg-blue-50 transition-all duration-200 text-slate-700 hover:text-blue-600 font-semibold"
          title="Mois suivant"
        >
          ›
        </button>
      </div>
    </div>
  );
}
