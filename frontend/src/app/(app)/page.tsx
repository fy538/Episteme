/**
 * Home page → Redirects to /chat
 *
 * The root route now simply redirects to the chat landing page.
 * The chat landing shows the hero input, and the left panel shows conversations.
 * No separate "home" concept needed.
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Spinner } from '@/components/ui/spinner';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/chat');
  }, [router]);

  return (
    <div className="flex h-full items-center justify-center">
      <Spinner size="lg" className="text-accent-600" />
    </div>
  );
}
