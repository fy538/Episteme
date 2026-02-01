/**
 * Cases List Page - Browse all cases
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import { GlobalHeader } from '@/components/layout/GlobalHeader';
import { casesAPI } from '@/lib/api/cases';
import { authAPI } from '@/lib/api/auth';
import type { Case } from '@/lib/types/case';

export default function CasesListPage() {
  const router = useRouter();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [authReady, setAuthReady] = useState(false);

  // Check auth
  useEffect(() => {
    async function checkAuth() {
      const isDevMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
      if (isDevMode) {
        setAuthReady(true);
        return;
      }

      const ok = await authAPI.ensureAuthenticated();
      if (!ok) {
        router.push('/login');
        return;
      }
      setAuthReady(true);
    }
    checkAuth();
  }, [router]);

  // Load cases
  useEffect(() => {
    async function loadCases() {
      if (!authReady) return;

      try {
        const casesResp = await casesAPI.listCases();
        // Filter by status locally
        const filtered = statusFilter === 'all' 
          ? casesResp 
          : casesResp.filter(c => c.status === statusFilter);
        setCases(filtered);
      } catch (error) {
        console.error('Failed to load cases:', error);
      } finally {
        setLoading(false);
      }
    }

    loadCases();
  }, [authReady, statusFilter]);

  // Filter cases by search
  const filteredCases = cases.filter(c =>
    c.title.toLowerCase().includes(search.toLowerCase())
  );

  // Sort by most recent
  const sortedCases = [...filteredCases].sort((a, b) =>
    new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  );

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" className="text-accent-600" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-neutral-50 dark:bg-primary-950">
      <GlobalHeader
        breadcrumbs={[
          { label: 'Workspace', href: '/workspace' },
          { label: 'Cases' }
        ]}
        showNav={true}
      />

      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-primary-900 dark:text-primary-50">
                Cases
              </h1>
              <p className="text-primary-600 dark:text-primary-400 mt-1">
                {sortedCases.length} {sortedCases.length === 1 ? 'case' : 'cases'}
              </p>
            </div>
            <Button onClick={() => router.push('/chat')}>
              + New Case
            </Button>
          </div>

          {/* Filters */}
          <div className="flex gap-3">
            <Input
              placeholder="Search cases..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-md"
            />
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-48"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="draft">Draft</option>
              <option value="archived">Archived</option>
            </Select>
          </div>

          {/* Cases Grid */}
          {sortedCases.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-neutral-300 dark:border-neutral-700 rounded-lg">
              <svg className="w-12 h-12 mx-auto text-primary-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-primary-600 dark:text-primary-400 mb-4">
                {search ? 'No cases match your search' : 'No cases yet'}
              </p>
              {!search && (
                <Button onClick={() => router.push('/chat')}>
                  Start Your First Case
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sortedCases.map(c => (
                <Link
                  key={c.id}
                  href={`/workspace/cases/${c.id}`}
                  className="group"
                >
                  <div className="h-full p-6 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-primary-900 hover:border-accent-500 dark:hover:border-accent-600 transition-all hover:shadow-md">
                    <div className="flex items-start justify-between mb-3">
                      <Badge
                        variant={
                          c.status === 'active' ? 'success' :
                          c.status === 'draft' ? 'warning' :
                          'neutral'
                        }
                      >
                        {c.status}
                      </Badge>
                      {c.confidence != null && (
                        <span className="text-xs text-primary-500 dark:text-primary-400">
                          {Math.round(c.confidence * 100)}% confidence
                        </span>
                      )}
                    </div>

                    <h3 className="font-semibold text-primary-900 dark:text-primary-50 mb-2 group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors line-clamp-2">
                      {c.title}
                    </h3>

                    <p className="text-sm text-primary-600 dark:text-primary-400 line-clamp-2 mb-3">
                      {c.position || 'No position statement yet'}
                    </p>

                    <div className="text-xs text-primary-500 dark:text-primary-500">
                      Updated {new Date(c.updated_at).toLocaleDateString()}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
