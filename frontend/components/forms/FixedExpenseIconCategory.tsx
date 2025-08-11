'use client';

import React from 'react';

const ICON_OPTIONS = [
  '🏠', '🚗', '⚡', '💧', '🌐', '📱', '🏥', '🎬', '💳', '🏦',
  '💰', '📊', '🔧', '🍕', '🛒', '⛽', '🚌', '🏋️', '📚', '💡'
];

const CATEGORY_OPTIONS = [
  { value: 'logement', label: 'Logement', icon: '🏠' },
  { value: 'transport', label: 'Transport', icon: '🚗' },
  { value: 'services', label: 'Services', icon: '⚡' },
  { value: 'loisirs', label: 'Loisirs', icon: '🎬' },
  { value: 'autre', label: 'Autre', icon: '💳' },
];

interface FixedExpenseIconCategoryProps {
  selectedIcon: string;
  selectedCategory: string;
  onIconChange: (icon: string) => void;
  onCategoryChange: (category: string) => void;
}

const FixedExpenseIconCategory = React.memo<FixedExpenseIconCategoryProps>(({
  selectedIcon,
  selectedCategory,
  onIconChange,
  onCategoryChange
}) => {
  return (
    <div className="space-y-4">
      {/* Category Selection */}
      <div>
        <label className="block text-sm font-medium mb-2">Catégorie</label>
        <div className="grid grid-cols-5 gap-2">
          {CATEGORY_OPTIONS.map((category) => (
            <button
              key={category.value}
              type="button"
              onClick={() => onCategoryChange(category.value)}
              className={`p-3 text-center text-sm border rounded-lg transition-colors ${
                selectedCategory === category.value
                  ? 'bg-blue-100 border-blue-300 text-blue-700'
                  : 'bg-zinc-50 border-zinc-200 hover:bg-zinc-100'
              }`}
            >
              <div className="text-lg mb-1">{category.icon}</div>
              <div className="text-xs font-medium">{category.label}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Icon Selection */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Icône : {selectedIcon}
        </label>
        <div className="grid grid-cols-10 gap-2 p-3 border border-zinc-200 rounded-lg max-h-24 overflow-y-auto">
          {ICON_OPTIONS.map((icon) => (
            <button
              key={icon}
              type="button"
              onClick={() => onIconChange(icon)}
              className={`p-2 text-lg hover:bg-zinc-100 rounded transition-colors ${
                selectedIcon === icon ? 'bg-blue-100 ring-2 ring-blue-300' : ''
              }`}
            >
              {icon}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
});

FixedExpenseIconCategory.displayName = 'FixedExpenseIconCategory';

export default FixedExpenseIconCategory;