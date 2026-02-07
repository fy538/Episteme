/**
 * Research Page — stub placeholder
 *
 * This route is referenced by CaseHomePage and ProjectHomePage
 * for "Generate Research" actions. Currently redirects to the
 * case workspace until a dedicated research UI is built.
 */

'use client';

import { useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';

export default function ResearchPage() {
  const router = useRouter();
  const params = useParams();
  const caseId = params.caseId as string;

  useEffect(() => {
    // Redirect to case workspace — research UI not yet implemented
    router.replace(`/cases/${caseId}`);
  }, [router, caseId]);

  return (
    <div className="flex items-center justify-center h-screen">
      <p className="text-neutral-500">Loading research view...</p>
    </div>
  );
}
