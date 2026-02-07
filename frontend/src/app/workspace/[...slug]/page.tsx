/**
 * Legacy workspace catch-all — redirects /workspace/anything to /anything
 * Handles old bookmarks like /workspace/cases/123 → /cases/123
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Spinner } from '@/components/ui/spinner';

export default function LegacyWorkspaceCatchAll({
  params,
}: {
  params: { slug: string[] };
}) {
  const router = useRouter();

  useEffect(() => {
    // Redirect /workspace/cases/123 → /cases/123
    const newPath = '/' + params.slug.join('/');
    router.replace(newPath);
  }, [router, params.slug]);

  return (
    <div className="flex h-screen items-center justify-center">
      <Spinner size="lg" className="text-accent-600" />
    </div>
  );
}
