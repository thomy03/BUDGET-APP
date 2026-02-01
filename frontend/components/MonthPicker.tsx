'use client';

import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { usePathname } from 'next/navigation';
import { useGlobalMonth, useGlobalMonthWithUrl } from '../lib/month';

interface MonthPickerProps {
  currentMonth?: string;
  onMonthChange?: (month: string) => void;
}

const MONTH_NAMES = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
];

const MONTH_NAMES_SHORT = [
  'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
  'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'
];

export default function MonthPicker({ currentMonth, onMonthChange }: MonthPickerProps = {}) {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [showYearSelector, setShowYearSelector] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Utiliser les props si fournis (pour les tests), sinon utiliser les hooks normalement
  const isTransactionsPage = pathname === '/transactions';
  const [month, setMonth] = currentMonth && onMonthChange
    ? [currentMonth, onMonthChange]
    : (isTransactionsPage
        ? useGlobalMonthWithUrl()
        : useGlobalMonth());

  // Parser le mois actuel
  const [currentYear, currentMonthNum] = month.split('-').map(Number);

  // Update dropdown position when opening
  useEffect(() => {
    if (isOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + 8,
        left: Math.max(8, rect.left + rect.width / 2 - 140) // Center dropdown, min 8px from edge
      });
    }
  }, [isOpen]);

  // Fermer le dropdown quand on clique ailleurs
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current && !dropdownRef.current.contains(event.target as Node) &&
        buttonRef.current && !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setShowYearSelector(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const navigateMonth = (direction: 'prev' | 'next') => {
    const currentDate = new Date(month + "-01");
    const offset = direction === 'prev' ? -1 : 1;
    currentDate.setMonth(currentDate.getMonth() + offset);
    const newMonth = currentDate.toISOString().slice(0, 7);
    setMonth(newMonth);
  };

  const selectMonth = (monthIndex: number) => {
    const newMonth = `${currentYear}-${String(monthIndex + 1).padStart(2, '0')}`;
    setMonth(newMonth);
    setIsOpen(false);
  };

  const selectYear = (year: number) => {
    const newMonth = `${year}-${String(currentMonthNum).padStart(2, '0')}`;
    setMonth(newMonth);
    setShowYearSelector(false);
  };

  // Générer les années disponibles (5 ans avant et après l'année actuelle)
  const years = Array.from({ length: 11 }, (_, i) => new Date().getFullYear() - 5 + i);

  // Dropdown content rendered via Portal
  const dropdownContent = isOpen && typeof document !== 'undefined' ? createPortal(
    <div 
      ref={dropdownRef}
      className="fixed z-[99999] animate-fadeIn"
      style={{ top: dropdownPosition.top, left: dropdownPosition.left }}
    >
      <div className="bg-white rounded-xl md:rounded-2xl shadow-2xl border border-gray-100 overflow-hidden min-w-[250px] sm:min-w-[280px]" role="listbox" aria-label="Sélection du mois">

        {/* Header avec sélecteur d'année */}
        <div className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 p-4">
          <button
            onClick={() => setShowYearSelector(!showYearSelector)}
            className="w-full flex items-center justify-center gap-2 text-white font-bold text-lg hover:opacity-90 transition-opacity"
          >
            <span>{currentYear}</span>
            <svg
              className={`w-4 h-4 transition-transform ${showYearSelector ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>

        {/* Sélecteur d'année */}
        {showYearSelector ? (
          <div className="p-3 max-h-[200px] overflow-y-auto">
            <div className="grid grid-cols-3 gap-2">
              {years.map(year => (
                <button
                  key={year}
                  onClick={() => selectYear(year)}
                  className={`py-2 px-3 rounded-xl font-medium transition-all duration-200 ${
                    year === currentYear
                      ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg'
                      : 'bg-gray-50 text-gray-700 hover:bg-indigo-50 hover:text-indigo-600'
                  }`}
                >
                  {year}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Grille des mois */
          <div className="p-3">
            <div className="grid grid-cols-3 gap-2">
              {MONTH_NAMES_SHORT.map((name, index) => (
                <button
                  key={index}
                  onClick={() => selectMonth(index)}
                  className={`py-3 px-2 rounded-xl font-medium transition-all duration-200 ${
                    index + 1 === currentMonthNum
                      ? 'bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white shadow-lg scale-105'
                      : 'bg-gray-50 text-gray-700 hover:bg-gradient-to-r hover:from-indigo-50 hover:to-purple-50 hover:text-indigo-600 hover:scale-102'
                  }`}
                >
                  {name}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Footer avec raccourcis */}
        <div className="border-t border-gray-100 p-2 bg-gray-50 flex justify-center gap-2">
          <button
            onClick={() => {
              const today = new Date();
              const newMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`;
              setMonth(newMonth);
              setIsOpen(false);
            }}
            className="px-4 py-1.5 text-sm font-medium text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
          >
            Aujourd'hui
          </button>
        </div>
      </div>
    </div>,
    document.body
  ) : null;

  return (
    <div className="relative">
      {/* Container principal ultra-moderne - responsive */}
      <div className="flex items-center gap-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 p-[2px] rounded-xl md:rounded-2xl shadow-lg">
        <div className="flex items-center bg-white rounded-[10px] md:rounded-[14px] p-0.5 md:p-1 gap-0.5 md:gap-1">

          {/* Bouton précédent */}
          <button
            onClick={() => navigateMonth('prev')}
            className="w-8 h-8 md:w-10 md:h-10 flex items-center justify-center rounded-lg md:rounded-xl bg-gradient-to-br from-gray-50 to-gray-100 hover:from-indigo-50 hover:to-purple-50 transition-all duration-300 text-gray-600 hover:text-indigo-600 group min-h-[44px] min-w-[44px] md:min-h-0 md:min-w-0"
            title="Mois précédent"
            aria-label="Mois précédent"
          >
            <svg className="w-4 h-4 md:w-5 md:h-5 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          {/* Affichage du mois cliquable */}
          <button
            ref={buttonRef}
            onClick={() => setIsOpen(!isOpen)}
            className="flex items-center gap-1 md:gap-2 px-2 md:px-4 py-1.5 md:py-2 min-w-[100px] md:min-w-[180px] justify-center rounded-lg md:rounded-xl bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 hover:from-indigo-100 hover:via-purple-100 hover:to-pink-100 transition-all duration-300 group min-h-[44px]"
            aria-label="Sélectionner le mois"
            aria-expanded={isOpen}
            aria-haspopup="listbox"
          >
            <span className="text-lg md:text-2xl">📅</span>
            <div className="flex flex-col items-start">
              <span className="text-xs md:text-sm font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
                {MONTH_NAMES_SHORT[currentMonthNum - 1]}
                <span className="hidden sm:inline"> {currentYear}</span>
              </span>
              <span className="text-[10px] md:text-xs text-gray-500 font-medium sm:hidden">{currentYear}</span>
            </div>
            <svg
              className={`w-3 h-3 md:w-4 md:h-4 text-gray-400 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Bouton suivant */}
          <button
            onClick={() => navigateMonth('next')}
            className="w-8 h-8 md:w-10 md:h-10 flex items-center justify-center rounded-lg md:rounded-xl bg-gradient-to-br from-gray-50 to-gray-100 hover:from-indigo-50 hover:to-purple-50 transition-all duration-300 text-gray-600 hover:text-indigo-600 group min-h-[44px] min-w-[44px] md:min-h-0 md:min-w-0"
            title="Mois suivant"
            aria-label="Mois suivant"
          >
            <svg className="w-4 h-4 md:w-5 md:h-5 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Portal dropdown */}
      {dropdownContent}

      {/* Styles pour l'animation */}
      <style jsx global>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.2s ease-out;
        }
      `}</style>
    </div>
  );
}
