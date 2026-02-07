/**
 * Legacy chat route - redirects to home
 * Chat is now embedded in the home page at /
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Spinner } from '@/components/ui/spinner';

export default function LegacyChatPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/');
  }, [router]);

  return (
    <div className="flex h-screen items-center justify-center">
      <Spinner size="lg" className="text-accent-600" />
    </div>
  );
}
