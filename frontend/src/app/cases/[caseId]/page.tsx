/**
 * Legacy case route - redirects to new workspace route
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Spinner } from '@/components/ui/spinner';

export default function LegacyCasePage({ params }: { params: { caseId: string } }) {
  const router = useRouter();

  useEffect(() => {
    // Redirect to new workspace route
    router.replace(`/workspace/cases/${params.caseId}`);
  }, [params.caseId, router]);

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-center">
        <Spinner size="lg" className="text-accent-600 mb-4" />
        <p className="text-primary-600 dark:text-primary-400">
          Redirecting to workspace...
        </p>
      </div>
    </div>
  );
}
