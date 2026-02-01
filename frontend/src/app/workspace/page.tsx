/**
 * Workspace Dashboard - Central hub for all work
 * Answers: "What should I work on now?"
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import { GlobalHeader } from '@/components/layout/GlobalHeader';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { authAPI } from '@/lib/api/auth';
import type { Case, Inquiry } from '@/lib/types/case';
import { cn } from '@/lib/utils';

export default function WorkspaceDashboard() {
  const router = useRouter();
  const [cases, setCases] = useState<Case[]>([]);
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [loading, setLoading] = useState(true);
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

  // Load dashboard data
  useEffect(() => {
    async function loadDashboard() {
      if (!authReady) return;

      try {
        const casesResp = await casesAPI.listCases();
        
        // Sort by most recent
        const sortedCases = casesResp.sort((a, b) => 
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        );
        
        setCases(sortedCases.slice(0, 5)); // Top 5 recent
        
        // Load inquiries for active cases
        const allInquiries: Inquiry[] = [];
        for (const c of sortedCases.slice(0, 3)) {
          try {
            const inquiries = await inquiriesAPI.getByCase(c.id);
            allInquiries.push(...inquiries.filter(i => i.status === 'open' || i.status === 'investigating'));
          } catch (err) {
            console.error('Failed to load inquiries for case', c.id);
          }
        }
        setInquiries(allInquiries.slice(0, 3)); // Top 3 pending
      } catch (error) {
        console.error('Failed to load dashboard:', error);
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, [authReady]);

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
        breadcrumbs={[{ label: 'Workspace' }]}
        showNav={true}
      />

      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Welcome Header */}
          <div>
            <h1 className="text-3xl font-bold text-primary-900 dark:text-primary-50 mb-2">
              Decision Confidence Center
            </h1>
            <p className="text-primary-600 dark:text-primary-400">
              Where do you need more epistemic grounding?
            </p>
          </div>

          {/* Epistemic Health Overview - The North Star Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-primary-600 dark:text-primary-400">Active Decisions</p>
                    <p className="text-3xl font-bold text-primary-900 dark:text-primary-50 mt-1">
                      {cases.filter(c => c.status === 'active').length}
                    </p>
                  </div>
                  <svg className="w-10 h-10 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-primary-600 dark:text-primary-400">Untested Assumptions</p>
                    <p className="text-3xl font-bold text-warning-600 mt-1">
                      {inquiries.filter(i => i.status === 'open').length}
                    </p>
                  </div>
                  <svg className="w-10 h-10 text-warning-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-primary-600 dark:text-primary-400">Active Research</p>
                    <p className="text-3xl font-bold text-accent-600 mt-1">
                      {inquiries.filter(i => i.status === 'investigating').length}
                    </p>
                  </div>
                  <svg className="w-10 h-10 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-primary-600 dark:text-primary-400">Validated Insights</p>
                    <p className="text-3xl font-bold text-success-600 mt-1">
                      {inquiries.filter(i => i.status === 'resolved').length}
                    </p>
                  </div>
                  <svg className="w-10 h-10 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Attention Required */}
            <div className="lg:col-span-2 space-y-6">
              {/* Blind Spots & Risks */}
              <Card className="border-warning-200 dark:border-warning-800">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-warning-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <CardTitle>Blind Spots & Untested Assumptions</CardTitle>
                  </div>
                  <CardDescription>
                    Critical questions that could undermine your decisions
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {inquiries.filter(i => i.status === 'open').length === 0 ? (
                    <div className="text-center py-6 text-success-600">
                      <svg className="w-8 h-8 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="font-medium">No untested assumptions - good epistemic hygiene!</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {inquiries.filter(i => i.status === 'open').slice(0, 3).map(inq => (
                        <div
                          key={inq.id}
                          className="p-3 bg-warning-50 dark:bg-warning-950 border border-warning-200 dark:border-warning-800 rounded-lg hover:border-warning-400 dark:hover:border-warning-600 transition-colors cursor-pointer"
                        >
                          <h4 className="font-medium text-sm text-primary-900 dark:text-primary-50 mb-1">
                            {inq.title}
                          </h4>
                          <p className="text-xs text-warning-800 dark:text-warning-200">
                            ⚠️ Needs investigation to build confidence
                          </p>
                        </div>
                      ))}
                      {inquiries.filter(i => i.status === 'open').length > 3 && (
                        <Link href="/workspace/inquiries">
                          <Button variant="outline" size="sm" className="w-full mt-2">
                            View {inquiries.filter(i => i.status === 'open').length - 3} more untested assumptions
                          </Button>
                        </Link>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Active Investigations */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <svg className="w-5 h-5 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        <CardTitle>Active Investigations</CardTitle>
                      </div>
                      <CardDescription className="mt-1">
                        Research in progress - building confidence
                      </CardDescription>
                    </div>
                    <Link href="/workspace/inquiries">
                      <Button variant="ghost" size="sm">View All</Button>
                    </Link>
                  </div>
                </CardHeader>
                <CardContent>
                  {inquiries.filter(i => i.status === 'investigating').length === 0 ? (
                    <div className="text-center py-6 text-primary-500">
                      <p>No active investigations</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {inquiries.filter(i => i.status === 'investigating').slice(0, 3).map(inq => (
                        <div key={inq.id} className="p-3 border border-neutral-200 dark:border-neutral-800 rounded-lg hover:border-accent-500 dark:hover:border-accent-600 transition-colors">
                          <div className="flex items-center gap-2 mb-1">
                            <Spinner size="sm" className="text-accent-600" />
                            <h4 className="font-medium text-sm text-primary-900 dark:text-primary-50">
                              {inq.title}
                            </h4>
                          </div>
                          <p className="text-xs text-primary-600 dark:text-primary-400">
                            Investigating - gathering evidence
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Decision-Ready Cases */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Cases by Confidence Level</CardTitle>
                      <CardDescription>
                        Where do you have epistemic grounding?
                      </CardDescription>
                    </div>
                    <Link href="/workspace/cases">
                      <Button variant="ghost" size="sm">View All</Button>
                    </Link>
                  </div>
                </CardHeader>
                <CardContent>
                  {cases.length === 0 ? (
                    <div className="text-center py-8 text-primary-500">
                      <p>No cases yet</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {cases.map(c => {
                        const confidenceLevel = c.confidence != null ? c.confidence : 0;
                        const isHighConfidence = confidenceLevel >= 0.7;
                        const isMediumConfidence = confidenceLevel >= 0.4 && confidenceLevel < 0.7;
                        
                        return (
                          <Link
                            key={c.id}
                            href={`/workspace/cases/${c.id}`}
                            className="block p-4 rounded-lg border border-neutral-200 dark:border-neutral-800 hover:border-accent-500 dark:hover:border-accent-600 transition-colors group"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <div className="flex-1 min-w-0">
                                <h3 className="font-semibold text-primary-900 dark:text-primary-50 group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors truncate">
                                  {c.title}
                                </h3>
                                <div className="flex items-center gap-2 mt-1">
                                  <div className="flex-1 h-2 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden">
                                    <div 
                                      className={`h-full ${
                                        isHighConfidence ? 'bg-success-600' :
                                        isMediumConfidence ? 'bg-warning-600' :
                                        'bg-error-600'
                                      }`}
                                      style={{ width: `${confidenceLevel * 100}%` }}
                                    />
                                  </div>
                                  <span className="text-xs text-primary-600 dark:text-primary-400 w-12 text-right">
                                    {Math.round(confidenceLevel * 100)}%
                                  </span>
                                </div>
                              </div>
                            </div>
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Right: Quick Actions */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Quick Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Button onClick={() => router.push('/chat')} className="w-full justify-start">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    Explore a Decision
                  </Button>
                  <Button variant="outline" onClick={() => router.push('/workspace/cases')} className="w-full justify-start">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                    </svg>
                    All Cases
                  </Button>
                  <Button variant="outline" onClick={() => router.push('/workspace/inquiries')} className="w-full justify-start">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    All Inquiries
                  </Button>
                </CardContent>
              </Card>

              <Card className="bg-accent-50 dark:bg-accent-950 border-accent-200 dark:border-accent-800">
                <CardHeader>
                  <CardTitle className="text-accent-900 dark:text-accent-100">
                    Epistemic Practice
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-accent-800 dark:text-accent-200 space-y-2">
                  <p>
                    <strong>Good decision-making</strong> requires:
                  </p>
                  <ul className="space-y-1 text-xs">
                    <li>• Surface assumptions early</li>
                    <li>• Test them rigorously</li>
                    <li>• Update beliefs with evidence</li>
                    <li>• Track confidence honestly</li>
                  </ul>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Getting Started (if no cases) */}
          {cases.length === 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Get Started with Episteme</CardTitle>
                <CardDescription>
                  Start a conversation and let AI help you structure your decision
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 border border-neutral-200 dark:border-neutral-800 rounded-lg">
                    <div className="text-accent-600 mb-2">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                    </div>
                    <h3 className="font-semibold text-primary-900 dark:text-primary-50 mb-1">
                      1. Start a Conversation
                    </h3>
                    <p className="text-sm text-primary-600 dark:text-primary-400">
                      Chat with AI about your decision. Explore the problem space.
                    </p>
                  </div>

                  <div className="p-4 border border-neutral-200 dark:border-neutral-800 rounded-lg">
                    <div className="text-accent-600 mb-2">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                    </div>
                    <h3 className="font-semibold text-primary-900 dark:text-primary-50 mb-1">
                      2. Create a Case
                    </h3>
                    <p className="text-sm text-primary-600 dark:text-primary-400">
                      AI will suggest creating a structured case when ready.
                    </p>
                  </div>

                  <div className="p-4 border border-neutral-200 dark:border-neutral-800 rounded-lg">
                    <div className="text-accent-600 mb-2">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </div>
                    <h3 className="font-semibold text-primary-900 dark:text-primary-50 mb-1">
                      3. Research & Validate
                    </h3>
                    <p className="text-sm text-primary-600 dark:text-primary-400">
                      Create inquiries to investigate assumptions and gather evidence.
                    </p>
                  </div>

                  <div className="p-4 border border-neutral-200 dark:border-neutral-800 rounded-lg">
                    <div className="text-accent-600 mb-2">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h3 className="font-semibold text-primary-900 dark:text-primary-50 mb-1">
                      4. Make Your Decision
                    </h3>
                    <p className="text-sm text-primary-600 dark:text-primary-400">
                      Build confidence through rigorous analysis and validation.
                    </p>
                  </div>
                </div>

                <div className="pt-4">
                  <Button onClick={() => router.push('/chat')} className="w-full">
                    Start Your First Conversation
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  );
}
