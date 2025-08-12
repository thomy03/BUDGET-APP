'use client';

import { useState, useRef, useEffect } from 'react';
import { useTagsManagement } from '../../hooks/useTagsManagement';

interface TagsInputProps {
  value: string;
  onChange: (value: string) => void;
  onFocus?: () => void;
  onBlur?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  isClassifying?: boolean;
}

export function TagsInput({
  value,
  onChange,
  onFocus,
  onBlur,
  placeholder = "Sélectionner ou saisir des tags...",
  disabled = false,
  className = "",
  isClassifying = false
}: TagsInputProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  
  const { tags, isLoading } = useTagsManagement();
  
  // Filter tags based on search term and exclude already selected ones
  const currentTags = value.split(',').map(t => t.trim()).filter(Boolean);
  const filteredTags = tags.filter(tag => {
    const matchesSearch = tag.name.toLowerCase().includes(searchTerm.toLowerCase());
    const notAlreadySelected = !currentTags.some(current => 
      current.toLowerCase() === tag.name.toLowerCase()
    );
    return matchesSearch && notAlreadySelected;
  });

  // Handle clicking outside to close dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current && 
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setSearchTerm("");
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    
    // Update search term for filtering dropdown
    const lastCommaIndex = newValue.lastIndexOf(',');
    const afterLastComma = lastCommaIndex >= 0 ? newValue.substring(lastCommaIndex + 1).trim() : newValue;
    setSearchTerm(afterLastComma);
    
    // Open dropdown when typing
    if (afterLastComma.length > 0 && !isOpen) {
      setIsOpen(true);
    }
  };

  const handleInputFocus = () => {
    setIsOpen(true);
    onFocus?.();
  };

  const handleInputBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    // Delay closing to allow tag selection
    setTimeout(() => {
      if (!dropdownRef.current?.contains(document.activeElement)) {
        setIsOpen(false);
        setSearchTerm("");
        onBlur?.(e.target.value);
      }
    }, 200);
  };

  const handleTagSelect = (tagName: string) => {
    const currentValue = value.trim();
    let newValue = "";
    
    if (currentValue === "") {
      newValue = tagName;
    } else {
      const lastCommaIndex = currentValue.lastIndexOf(',');
      if (lastCommaIndex >= 0) {
        // Replace text after last comma
        newValue = currentValue.substring(0, lastCommaIndex + 1) + ' ' + tagName;
      } else {
        // Add to existing value
        newValue = currentValue + ', ' + tagName;
      }
    }
    
    onChange(newValue);
    setSearchTerm("");
    setIsOpen(false);
    
    // Focus back to input
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      setSearchTerm("");
    } else if (e.key === 'Enter' && filteredTags.length === 1) {
      e.preventDefault();
      handleTagSelect(filteredTags[0].name);
    } else if (e.key === 'ArrowDown' && !isOpen) {
      setIsOpen(true);
    }
  };

  return (
    <div className="relative">
      <input
        ref={inputRef}
        className={`w-full px-2 py-1 border rounded text-sm transition-all duration-300 ${
          isClassifying 
            ? 'border-blue-300 bg-blue-50/50 ring-1 ring-blue-200 shadow-sm' 
            : 'border-zinc-200 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 hover:border-zinc-300'
        } ${className}`}
        value={value}
        onChange={handleInputChange}
        onFocus={handleInputFocus}
        onBlur={handleInputBlur}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled || isClassifying}
      />
      
      {/* Dropdown */}
      {isOpen && !isLoading && filteredTags.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 bg-white border border-zinc-200 rounded-md shadow-lg max-h-48 overflow-y-auto"
        >
          {filteredTags.slice(0, 10).map((tag) => (
            <button
              key={tag.name}
              type="button"
              className="w-full px-3 py-2 text-left text-sm hover:bg-zinc-50 focus:bg-zinc-50 focus:outline-none flex items-center justify-between"
              onMouseDown={(e) => e.preventDefault()} // Prevent input blur
              onClick={() => handleTagSelect(tag.name)}
            >
              <span>{tag.name}</span>
              <span className={`text-xs px-2 py-1 rounded-full ${
                tag.expense_type === 'fixed' 
                  ? 'bg-emerald-100 text-emerald-700' 
                  : 'bg-orange-100 text-orange-700'
              }`}>
                {tag.expense_type === 'fixed' ? 'FIXE' : 'VAR'}
              </span>
            </button>
          ))}
          
          {/* Show "create new tag" option if search doesn't match existing */}
          {searchTerm.length > 0 && !filteredTags.some(tag => 
            tag.name.toLowerCase() === searchTerm.toLowerCase()
          ) && (
            <button
              type="button"
              className="w-full px-3 py-2 text-left text-sm text-blue-600 hover:bg-blue-50 focus:bg-blue-50 focus:outline-none border-t border-zinc-100"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => handleTagSelect(searchTerm)}
            >
              <span className="font-medium">Créer "{searchTerm}"</span>
            </button>
          )}
        </div>
      )}
      
      {/* Loading state */}
      {isOpen && isLoading && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-zinc-200 rounded-md shadow-lg p-3 text-center text-sm text-zinc-500">
          Chargement des tags...
        </div>
      )}
    </div>
  );
}