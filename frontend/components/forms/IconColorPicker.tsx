'use client';

import React from 'react';

const ICON_OPTIONS = [
  '💰', '📈', '✈️', '🏗️', '🚨', '🚗', '🏖️', '📚', '🏥', '🎁', '💝', '🎯',
  '💎', '🏠', '🌟', '⚡', '🔥', '🌈', '🚀', '💡', '🎉', '🎊', '🍀', '✨'
];

const COLOR_OPTIONS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f59e0b', '#10b981',
  '#059669', '#0891b2', '#0284c7', '#3b82f6', '#7c3aed', '#a855f7',
  '#c2410c', '#dc2626', '#ea580c', '#ca8a04', '#65a30d', '#84cc16'
];

interface IconColorPickerProps {
  selectedIcon: string;
  selectedColor: string;
  onIconChange: (icon: string) => void;
  onColorChange: (color: string) => void;
}

const IconColorPicker = React.memo<IconColorPickerProps>(({
  selectedIcon,
  selectedColor,
  onIconChange,
  onColorChange
}) => {
  return (
    <div className="space-y-4">
      {/* Icon Selection */}
      <div>
        <label style={{ color: '#374151' }} className="block text-sm font-medium mb-2">
          Icône : {selectedIcon}
        </label>
        <div className="grid grid-cols-8 gap-2 p-3 border border-zinc-200 rounded-lg max-h-32 overflow-y-auto" style={{ backgroundColor: 'white' }}>
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

      {/* Color Selection */}
      <div>
        <label style={{ color: '#374151' }} className="block text-sm font-medium mb-2">
          Couleur
        </label>
        <div className="grid grid-cols-9 gap-2">
          {COLOR_OPTIONS.map((color) => (
            <button
              key={color}
              type="button"
              onClick={() => onColorChange(color)}
              className={`w-8 h-8 rounded-full border-2 hover:scale-110 transition-transform ${
                selectedColor === color ? 'ring-2 ring-zinc-400 ring-offset-2' : 'border-zinc-300'
              }`}
              style={{ backgroundColor: color }}
              title={color}
            />
          ))}
        </div>
      </div>
    </div>
  );
});

IconColorPicker.displayName = 'IconColorPicker';

export default IconColorPicker;
