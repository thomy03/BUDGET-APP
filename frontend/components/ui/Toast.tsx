'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import Alert from './Alert';

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface Toast {
  id: string;
  variant: 'info' | 'success' | 'warning' | 'error';
  title: string;
  description?: string;
  actions?: ToastAction[];
  secondaryAction?: ToastAction;
  dismissible?: boolean;
  duration?: number; // en millisecondes, 0 = permanent
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
  success: (title: string, options?: Partial<Omit<Toast, 'id' | 'variant'>>) => string;
  error: (title: string, options?: Partial<Omit<Toast, 'id' | 'variant'>>) => string;
  warning: (title: string, options?: Partial<Omit<Toast, 'id' | 'variant'>>) => string;
  info: (title: string, options?: Partial<Omit<Toast, 'id' | 'variant'>>) => string;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast: Toast = {
      id,
      dismissible: true,
      duration: 5000, // 5 secondes par défaut
      ...toast,
    };

    setToasts(prev => [...prev, newToast]);

    // Auto-remove après la durée spécifiée
    if (newToast.duration && newToast.duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, newToast.duration);
    }

    return id;
  }, [removeToast]);

  const success = useCallback((title: string, options?: Partial<Omit<Toast, 'id' | 'variant'>>) => {
    return addToast({ variant: 'success', title, ...options });
  }, [addToast]);

  const error = useCallback((title: string, options?: Partial<Omit<Toast, 'id' | 'variant'>>) => {
    return addToast({ variant: 'error', title, duration: 0, ...options }); // Erreurs permanentes par défaut
  }, [addToast]);

  const warning = useCallback((title: string, options?: Partial<Omit<Toast, 'id' | 'variant'>>) => {
    return addToast({ variant: 'warning', title, ...options });
  }, [addToast]);

  const info = useCallback((title: string, options?: Partial<Omit<Toast, 'id' | 'variant'>>) => {
    return addToast({ variant: 'info', title, ...options });
  }, [addToast]);

  const value: ToastContextValue = {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
};

const ToastContainer: React.FC<{
  toasts: Toast[];
  onRemove: (id: string) => void;
}> = ({ toasts, onRemove }) => {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  );
};

const ToastItem: React.FC<{
  toast: Toast;
  onRemove: (id: string) => void;
}> = ({ toast, onRemove }) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Animation d'entrée
    const timer = setTimeout(() => setIsVisible(true), 50);
    return () => clearTimeout(timer);
  }, []);

  const handleClose = () => {
    setIsVisible(false);
    setTimeout(() => onRemove(toast.id), 200); // Délai pour l'animation de sortie
  };

  return (
    <div
      className={`
        transform transition-all duration-200 ease-in-out
        ${isVisible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
      `}
    >
      <Alert
        variant={toast.variant}
        {...(toast.dismissible && { onClose: handleClose })}
        className="shadow-lg border min-w-0"
      >
        <div className="space-y-2">
          <div className="font-medium">{toast.title}</div>
          {toast.description && (
            <div className="text-sm opacity-90">{toast.description}</div>
          )}
          
          {(toast.actions && toast.actions.length > 0) || toast.secondaryAction ? (
            <div className="flex gap-2 mt-3">
              {toast.actions?.slice(0, 3).map((action, index) => (
                <button
                  key={index}
                  onClick={() => {
                    action.onClick();
                    handleClose();
                  }}
                  className="px-3 py-1 text-xs font-medium bg-white bg-opacity-20 hover:bg-opacity-30 rounded-md transition-colors"
                >
                  {action.label}
                </button>
              ))}
              {toast.secondaryAction && (
                <button
                  onClick={() => {
                    toast.secondaryAction!.onClick();
                    handleClose();
                  }}
                  className="px-3 py-1 text-xs font-medium bg-white bg-opacity-10 hover:bg-opacity-20 rounded-md transition-colors ml-auto"
                >
                  {toast.secondaryAction.label}
                </button>
              )}
            </div>
          ) : null}
        </div>
      </Alert>
    </div>
  );
};

export default ToastProvider;