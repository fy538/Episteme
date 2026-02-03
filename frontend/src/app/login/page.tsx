/**
 * Login page
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { authAPI } from '@/lib/api/auth';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authAPI.login({ email, password });
      // Redirect to workspace on success
      router.push('/workspace');
    } catch (err) {
      console.error('Login failed:', err);
      setError(err instanceof Error ? err.message : 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl tracking-tight font-bold text-neutral-900 mb-2">
            Welcome to Episteme
          </h1>
          <p className="text-neutral-600">
            Sign in to access your workspace
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-error-50 border border-error-200 text-error-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            <div className="space-y-1">
              <Label htmlFor="email" required>Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                placeholder="you@example.com"
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="password" required>Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-neutral-600">
            <Link href="/" className="text-accent-600 hover:text-accent-700">
              ← Back to home
            </Link>
          </div>
        </div>

        {/* Dev mode notice */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-4 bg-warning-50 border border-warning-200 rounded-lg p-4">
            <p className="text-xs text-warning-800">
              <strong>Dev Mode:</strong> Add <code className="bg-warning-100 px-1 rounded">NEXT_PUBLIC_DEV_MODE=true</code> to <code className="bg-warning-100 px-1 rounded">.env.local</code> to bypass login locally.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
