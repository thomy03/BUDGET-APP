import React from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  onRightIconClick?: () => void;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ 
    label, 
    error, 
    hint, 
    leftIcon, 
    rightIcon, 
    onRightIconClick,
    className = "", 
    id,
    ...props 
  }, ref) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
    const hasError = !!error;

    return (
      <div className="space-y-2">
        {label && (
          <label htmlFor={inputId} className="block text-sm font-medium text-zinc-700">
            {label}
          </label>
        )}
        
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-zinc-400">
              {leftIcon}
            </div>
          )}
          
          <input
            ref={ref}
            id={inputId}
            className={`
              w-full px-4 py-3 border rounded-xl transition-all
              focus:outline-none focus:ring-2 focus:border-transparent
              disabled:opacity-50 disabled:cursor-not-allowed
              ${leftIcon ? "pl-10" : ""}
              ${rightIcon ? "pr-10" : ""}
              ${hasError 
                ? "border-red-300 focus:ring-red-200 focus:border-red-500" 
                : "border-zinc-300 focus:ring-zinc-900 focus:border-zinc-900"
              }
              ${className}
            `}
            {...props}
          />
          
          {rightIcon && (
            <button
              type="button"
              onClick={onRightIconClick}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-zinc-400 hover:text-zinc-600 transition-colors"
              disabled={props.disabled}
            >
              {rightIcon}
            </button>
          )}
        </div>

        {error && (
          <p className="text-sm text-red-600 flex items-center gap-1">
            <span>⚠️</span>
            {error}
          </p>
        )}
        
        {hint && !error && (
          <p className="text-sm text-zinc-500">
            {hint}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export default Input;