import React from "react";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  text?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = "md",
  className = "",
  text,
}) => {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-8 w-8",
    lg: "h-12 w-12",
  };

  return (
    <div className={`flex flex-col items-center gap-3 ${className}`}>
      <div
        className={`animate-spin rounded-full border-b-2 border-zinc-900 ${sizeClasses[size]}`}
        role="status"
        aria-label="Chargement"
      >
        <span className="sr-only">Chargement...</span>
      </div>
      {text && (
        <p className="text-zinc-600 text-sm">{text}</p>
      )}
    </div>
  );
};

export default LoadingSpinner;