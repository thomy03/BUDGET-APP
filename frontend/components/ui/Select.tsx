'use client';

import { forwardRef, SelectHTMLAttributes } from 'react';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  options: SelectOption[];
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  variant?: 'default' | 'compact';
  size?: 'sm' | 'md' | 'lg';
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ 
    options, 
    value, 
    onChange, 
    placeholder, 
    variant = 'default',
    size = 'md',
    className = '', 
    disabled,
    ...props 
  }, ref) => {
    const baseClasses = 'border rounded focus:outline-none focus:ring-2 transition-colors duration-200';
    
    const variantClasses = {
      default: 'bg-white border-gray-300 focus:ring-blue-500 focus:border-blue-500',
      compact: 'bg-gray-50 border-gray-200 focus:ring-blue-400 focus:border-blue-400'
    };
    
    const sizeClasses = {
      sm: 'px-2 py-1 text-sm',
      md: 'px-3 py-2 text-sm',
      lg: 'px-4 py-3 text-base'
    };
    
    const disabledClasses = disabled 
      ? 'opacity-50 cursor-not-allowed bg-gray-100' 
      : 'hover:border-gray-400';

    const selectClasses = `
      ${baseClasses} 
      ${variantClasses[variant]} 
      ${sizeClasses[size]} 
      ${disabledClasses}
      ${className}
    `.trim();

    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
      onChange?.(e.target.value);
    };

    return (
      <select autoComplete="off"
        ref={ref}
        value={value}
        onChange={handleChange}
        disabled={disabled}
        style={{ backgroundColor: 'white', pointerEvents: disabled ? 'none' : 'auto' }}
        className={selectClasses}
        {...props}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  }
);

Select.displayName = 'Select';

export default Select;
export type { SelectProps, SelectOption };