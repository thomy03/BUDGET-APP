import React from "react";

interface AlertProps {
  variant?: "info" | "success" | "warning" | "error";
  children?: React.ReactNode;
  className?: string;
  onClose?: () => void;
  icon?: React.ReactNode;
  // For backward compatibility with tests
  message?: string;
  type?: "info" | "success" | "warning" | "error";
}

const Alert: React.FC<AlertProps> = ({
  variant = "info",
  children,
  className = "",
  onClose,
  icon,
  message,
  type,
}) => {
  // Use type prop as fallback for variant (test compatibility)
  const effectiveVariant = variant || type || "info";
  const variantClasses = {
    info: "bg-blue-50 border-blue-200 text-blue-800",
    success: "bg-green-50 border-green-200 text-green-800",
    warning: "bg-amber-50 border-amber-200 text-amber-800",
    error: "bg-red-50 border-red-200 text-red-700",
  };

  const defaultIcons = {
    info: "ℹ️",
    success: "✅",
    warning: "⚠️",
    error: "⚠️",
  };

  return (
    <div
      className={`
        flex items-start gap-3 p-4 border rounded-xl text-sm
        ${variantClasses[effectiveVariant]} 
        ${className}
      `}
      role="alert"
    >
      <span className="flex-shrink-0">
        {icon || defaultIcons[effectiveVariant]}
      </span>
      
      <div className="flex-1 min-w-0">
        {children || message}
      </div>
      
      {onClose && (
        <button
          onClick={onClose}
          className="flex-shrink-0 text-current opacity-60 hover:opacity-100 transition-opacity"
          aria-label="Fermer l'alerte"
        >
          ✕
        </button>
      )}
    </div>
  );
};

export default Alert;