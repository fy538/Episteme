/**
 * useAuth Hook
 *
 * Centralized authentication gate for the (app) route group.
 * Checks auth status on mount and redirects to /login if not authenticated.
 * In dev mode (NEXT_PUBLIC_DEV_MODE=true), bypasses the check.
 *
 * Used once in (app)/layout.tsx — individual pages no longer need auth checks.
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI } from '@/lib/api/auth';

export function useAuth() {
  const router = useRouter();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    async function checkAuth() {
      const isDevMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
      if (isDevMode) {
        setIsReady(true);
        return;
      }

      const ok = await authAPI.ensureAuthenticated();
      if (!ok) {
        router.push('/login');
        return;
      }
      setIsReady(true);
    }
    checkAuth();
  }, [router]);

  return { isReady };
}
