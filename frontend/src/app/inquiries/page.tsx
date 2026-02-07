/**
 * Inquiries List Page - Browse all research across cases
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/ui/status-badge';
import { Spinner } from '@/components/ui/spinner';
import { GlobalHeader } from '@/components/layout/GlobalHeader';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { authAPI } from '@/lib/api/auth';
import type { Case, Inquiry } from '@/lib/types/case';

interface InquiryWithCase extends Inquiry {
  caseTitle?: string;
}

export default function InquiriesListPage() {
  const router = useRouter();
  const [inquiries, setInquiries] = useState<InquiryWithCase[]>([]);
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

  // Load inquiries
  useEffect(() => {
    async function loadInquiries() {
      if (!authReady) return;

      try {
        const casesResp = await casesAPI.listCases();
        setCases(casesResp);

        // Load inquiries for each case
        const allInquiries: InquiryWithCase[] = [];
        for (const c of casesResp) {
          try {
            const inqs = await inquiriesAPI.getByCase(c.id);
            allInquiries.push(...inqs.map(inq => ({
              ...inq,
              caseTitle: c.title
            })));
          } catch (err) {
            console.error('Failed to load inquiries for case', c.id);
          }
        }
        setInquiries(allInquiries);
      } catch (error) {
        console.error('Failed to load inquiries:', error);
      } finally {
        setLoading(false);
      }
    }

    loadInquiries();
  }, [authReady]);

  // Filter inquiries
  const filteredInquiries = inquiries
    .filter(inq => {
      if (statusFilter !== 'all' && inq.status !== statusFilter) return false;
      if (search && !inq.title.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    })
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());

  const stats = {
    total: inquiries.length,
    open: inquiries.filter(i => i.status === 'open').length,
    investigating: inquiries.filter(i => i.status === 'investigating').length,
    resolved: inquiries.filter(i => i.status === 'resolved').length,
  };

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
          { label: 'Home', href: '/' },
          { label: 'Inquiries' }
        ]}
        showNav={true}
      />

      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Header with Stats */}
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl tracking-tight font-bold text-primary-900 dark:text-primary-50">
                Research Inquiries
              </h1>
              <p className="text-primary-600 dark:text-primary-400 mt-1">
                All investigations across your cases
              </p>
            </div>
            <div className="flex gap-3">
              <div className="text-center px-4 py-2 bg-white dark:bg-primary-900 border border-neutral-200 dark:border-neutral-800 rounded-lg">
                <div className="text-2xl tracking-tight font-bold text-primary-900 dark:text-primary-50">{stats.open}</div>
                <div className="text-xs text-primary-600 dark:text-primary-400">Open</div>
              </div>
              <div className="text-center px-4 py-2 bg-white dark:bg-primary-900 border border-neutral-200 dark:border-neutral-800 rounded-lg">
                <div className="text-2xl tracking-tight font-bold text-accent-600">{stats.investigating}</div>
                <div className="text-xs text-primary-600 dark:text-primary-400">Investigating</div>
              </div>
              <div className="text-center px-4 py-2 bg-white dark:bg-primary-900 border border-neutral-200 dark:border-neutral-800 rounded-lg">
                <div className="text-2xl tracking-tight font-bold text-success-600">{stats.resolved}</div>
                <div className="text-xs text-primary-600 dark:text-primary-400">Resolved</div>
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="flex gap-3">
            <Input
              placeholder="Search inquiries..."
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
              <option value="open">Open</option>
              <option value="investigating">Investigating</option>
              <option value="resolved">Resolved</option>
              <option value="archived">Archived</option>
            </Select>
          </div>

          {/* Inquiries List */}
          {filteredInquiries.length === 0 ? (
            <Card>
              <CardContent className="text-center py-12">
                <svg className="w-12 h-12 mx-auto text-primary-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <p className="text-primary-600 dark:text-primary-400 mb-4">
                  {search ? 'No inquiries match your search' : 'No research inquiries yet'}
                </p>
                {!search && (
                  <Button onClick={() => router.push('/')}>
                    Start a Conversation
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {filteredInquiries.map(inq => (
                <Card key={inq.id} className="hover:border-accent-500 dark:hover:border-accent-600 transition-colors cursor-pointer">
                  <CardHeader>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <StatusBadge 
                            status={
                              inq.status === 'resolved' ? 'validated' :
                              inq.status === 'investigating' ? 'investigating' :
                              'untested'
                            } 
                          />
                          {inq.caseTitle && (
                            <span className="text-xs text-primary-500 dark:text-primary-400">
                              {inq.caseTitle}
                            </span>
                          )}
                        </div>
                        
                        <CardTitle className="text-lg mb-2">{inq.title}</CardTitle>
                        
                        {inq.description && (
                          <p className="text-sm text-primary-600 dark:text-primary-400 line-clamp-2">
                            {inq.description}
                          </p>
                        )}

                        {inq.conclusion && (
                          <div className="mt-3 p-3 bg-success-50 dark:bg-success-950 border border-success-200 dark:border-success-800 rounded-md">
                            <p className="text-sm text-success-800 dark:text-success-200 font-medium">
                              Conclusion: {inq.conclusion}
                            </p>
                          </div>
                        )}
                      </div>

                      <div className="text-right text-xs text-primary-500 dark:text-primary-400 whitespace-nowrap">
                        {new Date(inq.updated_at).toLocaleDateString()}
                      </div>
                    </div>
                  </CardHeader>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
