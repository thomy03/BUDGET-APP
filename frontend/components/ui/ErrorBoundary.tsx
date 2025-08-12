'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  componentName?: string;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

/**
 * Error Boundary Component for catching JavaScript errors anywhere in the child component tree
 * 
 * Usage:
 * <ErrorBoundary componentName="TransactionRow">
 *   <TransactionRow {...props} />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details for debugging
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo
    });

    // Report to error tracking service in production
    if (process.env.NODE_ENV === 'production') {
      // Add your error reporting service here
      // Example: Sentry.captureException(error, { extra: errorInfo });
    }
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2 text-red-800 mb-2">
            <span>⚠️</span>
            <h3 className="font-semibold">
              Erreur dans {this.props.componentName || 'le composant'}
            </h3>
          </div>
          <p className="text-red-600 text-sm mb-3">
            Une erreur inattendue s'est produite. Veuillez actualiser la page.
          </p>
          
          {/* Development error details */}
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details className="bg-red-100 p-2 rounded text-xs">
              <summary className="cursor-pointer font-medium text-red-700">
                Détails de l'erreur (développement)
              </summary>
              <pre className="mt-2 whitespace-pre-wrap text-red-600">
                {this.state.error.message}
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}
          
          <button
            onClick={() => window.location.reload()}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
          >
            Actualiser la page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Higher-Order Component wrapper for easy error boundary usage
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  componentName?: string
) {
  const WithErrorBoundaryComponent = (props: P) => (
    <ErrorBoundary componentName={componentName || WrappedComponent.name}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );

  WithErrorBoundaryComponent.displayName = `withErrorBoundary(${componentName || WrappedComponent.name})`;
  
  return WithErrorBoundaryComponent;
}

/**
 * Hook for manual error reporting
 */
export function useErrorHandler() {
  return (error: Error, errorInfo?: string) => {
    console.error('Manual error report:', error, errorInfo);
    
    if (process.env.NODE_ENV === 'production') {
      // Report to error tracking service
      // Example: Sentry.captureException(error, { extra: { info: errorInfo } });
    }
  };
}