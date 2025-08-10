import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  children: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ 
    variant = "secondary", 
    size = "md", 
    loading = false, 
    children, 
    className = "", 
    disabled,
    ...props 
  }, ref) => {
    const baseClasses = "inline-flex items-center justify-center gap-2 font-medium transition-all rounded-xl focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";
    
    const variantClasses = {
      primary: "bg-zinc-900 text-white border-zinc-900 hover:bg-black focus:ring-zinc-900",
      secondary: "bg-white text-zinc-900 border border-zinc-300 hover:bg-zinc-50 focus:ring-zinc-200",
      danger: "bg-red-600 text-white border-red-600 hover:bg-red-700 focus:ring-red-200",
      ghost: "bg-transparent text-zinc-600 border-transparent hover:bg-zinc-100 focus:ring-zinc-200",
    };

    const sizeClasses = {
      sm: "px-3 py-2 text-sm",
      md: "px-4 py-3 text-sm",
      lg: "px-6 py-4 text-base",
    };

    const combinedClassName = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`;

    return (
      <button
        ref={ref}
        className={combinedClassName}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
            <span>Chargement...</span>
          </>
        ) : (
          children
        )}
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;