'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { LoadingSpinner } from '../../components/ui';

/**
 * /dashboard redirects to / (main dashboard with modern CleanDashboard)
 * The modern dashboard is at the root route
 */
export default function DashboardRedirect() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to the main modern dashboard at /
    router.replace('/');
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <LoadingSpinner size="lg" text="Redirection vers le dashboard moderne..." />
    </div>
  );
}
