import React from "react";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  padding?: "sm" | "md" | "lg" | "none";
  shadow?: "sm" | "md" | "lg" | "none";
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ 
    children, 
    padding = "md", 
    shadow = "sm", 
    className = "", 
    ...props 
  }, ref) => {
    const paddingClasses = {
      none: "",
      sm: "p-4",
      md: "p-6",
      lg: "p-8",
    };

    const shadowClasses = {
      none: "",
      sm: "shadow-sm",
      md: "shadow-md",
      lg: "shadow-lg",
    };

    const combinedClassName = `
      bg-white rounded-2xl border border-zinc-200 transition-shadow
      ${paddingClasses[padding]} 
      ${shadowClasses[shadow]} 
      ${className}
    `.trim();

    return (
      <div ref={ref} className={combinedClassName} {...props}>
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";

export default Card;