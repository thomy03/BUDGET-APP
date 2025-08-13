'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '../../lib/auth';

export function SessionStatus() {
  const { isAuthenticated, user } = useAuth();
  const [sessionInfo, setSessionInfo] = useState<string>('');

  useEffect(() => {
    if (!isAuthenticated) {
      setSessionInfo('');
      return;
    }

    const updateSessionInfo = () => {
      const loginTime = localStorage.getItem('login_time');
      if (loginTime) {
        const elapsed = Date.now() - parseInt(loginTime);
        const days = Math.floor(elapsed / (1000 * 60 * 60 * 24));
        const hours = Math.floor((elapsed % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        
        // Token valide pour 7 jours
        const remaining = 7 * 24 * 60 * 60 * 1000 - elapsed;
        const remainingDays = Math.floor(remaining / (1000 * 60 * 60 * 24));
        const remainingHours = Math.floor((remaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        
        if (remaining > 0) {
          setSessionInfo(`Session: ${remainingDays}j ${remainingHours}h restants`);
        } else {
          setSessionInfo('Session expirée');
        }
      }
    };

    updateSessionInfo();
    const interval = setInterval(updateSessionInfo, 60000); // Mise à jour chaque minute

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  if (!isAuthenticated || !sessionInfo) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 bg-green-50 border border-green-200 rounded-lg px-3 py-2 text-sm text-green-700 shadow-sm z-50">
      <div className="flex items-center gap-2">
        <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
        <span className="font-medium">{user}</span>
        <span className="text-green-600">•</span>
        <span className="text-green-600">{sessionInfo}</span>
      </div>
    </div>
  );
}