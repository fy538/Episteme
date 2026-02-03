/**
 * Landing page
 */

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { authAPI } from '@/lib/api/auth';

export default function Home() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isDevMode, setIsDevMode] = useState(false);

  useEffect(() => {
    const devMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
    setIsDevMode(devMode);
    setIsAuthenticated(authAPI.isAuthenticated() || devMode);
  }, []);

  function handleLogout() {
    authAPI.logout();
    setIsAuthenticated(false);
  }

  // Redirect authenticated users to workspace
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/workspace');
    }
  }, [isAuthenticated, router]);

  // Show landing page only for logged-out users
  if (isAuthenticated) {
    return null; // Will redirect
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 md:p-24 bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 dark:from-primary-950 dark:via-primary-950 dark:to-accent-950/20">
      <div className="text-center max-w-2xl">
        <h1 className="text-5xl md:text-6xl font-display font-bold tracking-tight text-neutral-900 dark:text-neutral-50 mb-6">
          <span className="bg-gradient-to-r from-accent-600 via-accent-500 to-accent-700 bg-clip-text text-transparent">
            Episteme
          </span>
        </h1>
        <p className="text-xl md:text-2xl text-neutral-600 dark:text-neutral-400 mb-12 leading-relaxed">
          Workspace for rigorous decision-making
        </p>
        
        <div className="flex gap-4 justify-center">
          <Link href="/login">
            <Button size="lg">Sign In</Button>
          </Link>
        </div>

        {isDevMode && (
          <div className="mt-8 bg-warning-50 dark:bg-warning-950 border border-warning-200 dark:border-warning-800 rounded-lg p-4 max-w-md mx-auto">
            <p className="text-xs text-warning-800 dark:text-warning-200">
              <strong>🔧 Dev Mode Active</strong> - Authentication bypassed for local development
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
