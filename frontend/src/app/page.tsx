/**
 * Landing page
 */

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
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

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Episteme
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Workspace for rigorous decision-making
        </p>
        
        <div className="flex gap-4 justify-center">
          {isAuthenticated ? (
            <>
              <Link
                href="/chat"
                className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Start Chatting
              </Link>
              {!isDevMode && (
                <button
                  onClick={handleLogout}
                  className="inline-block px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  Logout
                </button>
              )}
            </>
          ) : (
            <Link
              href="/login"
              className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Sign In
            </Link>
          )}
        </div>

        {isDevMode && (
          <div className="mt-8 bg-yellow-50 border border-yellow-200 rounded-lg p-4 max-w-md mx-auto">
            <p className="text-xs text-yellow-800">
              <strong>🔧 Dev Mode Active</strong> - Authentication bypassed for local development
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
