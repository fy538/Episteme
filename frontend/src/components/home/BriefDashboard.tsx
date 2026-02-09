/**
 * BriefDashboard
 *
 * Action-oriented dashboard view for the home page. Toggleable alongside
 * the default home view. Shows 5 sections with mock data (UI placeholders):
 *
 *   1. Active Decisions — compact case status cards
 *   2. Action Queue — prioritized action items
 *   3. Recent Activity — timeline-style event feed
 *   4. Recent Threads — resume conversations
 *   5. Discover — personalized news/articles feed (vision placeholder)
 *
 * All data is currently hardcoded mock data. Each section accepts props
 * so real data can be wired in later via a useBriefDashboard hook.
 */

'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';

// ═══════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════

interface BriefDecision {
  id: string;
  title: string;
  stage: 'exploring' | 'investigating' | 'synthesizing' | 'ready';
  inquiries: { resolved: number; total: number };
  momentum: 'up' | 'steady' | 'down';
  updatedAt: string;
}

interface BriefAction {
  id: string;
  type: 'resolve' | 'research' | 'assumptions' | 'investigate' | 'criteria';
  title: string;
  caseName: string;
  variant: 'warning' | 'info' | 'success' | 'accent' | 'default';
}

interface BriefActivity {
  id: string;
  type: 'inquiry_resolved' | 'evidence_added' | 'research_started' | 'case_created';
  description: string;
  caseName: string;
  timestamp: string;
}

interface BriefThread {
  id: string;
  title: string;
  caseName?: string;
  timestamp: string;
  messageCount: number;
}

interface DiscoverItem {
  id: string;
  headline: string;
  summary: string;
  source: string;
  relatedCase?: string;
  gradientFrom: string;
  gradientTo: string;
}

// ═══════════════════════════════════════════════════════
// Mock Data
// ═══════════════════════════════════════════════════════

const MOCK_DECISIONS: BriefDecision[] = [
  { id: '1', title: 'Should we expand to EU market?', stage: 'investigating', inquiries: { resolved: 3, total: 5 }, momentum: 'up', updatedAt: '2h ago' },
  { id: '2', title: 'Pricing model restructure', stage: 'synthesizing', inquiries: { resolved: 4, total: 6 }, momentum: 'steady', updatedAt: '5h ago' },
  { id: '3', title: 'Build vs buy: analytics platform', stage: 'exploring', inquiries: { resolved: 0, total: 3 }, momentum: 'up', updatedAt: '1d ago' },
  { id: '4', title: 'Team restructuring Q3', stage: 'ready', inquiries: { resolved: 5, total: 5 }, momentum: 'steady', updatedAt: '2d ago' },
];

const MOCK_ACTIONS: BriefAction[] = [
  { id: '1', type: 'resolve', title: 'Ready to resolve: Market size estimation', caseName: 'EU Expansion', variant: 'warning' },
  { id: '2', type: 'research', title: 'Research completed: Competitor analysis', caseName: 'Pricing Model', variant: 'info' },
  { id: '3', type: 'assumptions', title: '2 untested high-risk assumptions', caseName: 'EU Expansion', variant: 'warning' },
  { id: '4', type: 'investigate', title: 'Continue investigating vendor options', caseName: 'Analytics Platform', variant: 'accent' },
  { id: '5', type: 'criteria', title: '3/4 decision criteria met', caseName: 'Team Restructuring', variant: 'success' },
];

const MOCK_ACTIVITY: BriefActivity[] = [
  { id: '1', type: 'inquiry_resolved', description: 'Resolved: "What is the regulatory landscape?"', caseName: 'EU Expansion', timestamp: '2h ago' },
  { id: '2', type: 'evidence_added', description: 'Added 3 evidence items to market sizing', caseName: 'EU Expansion', timestamp: '3h ago' },
  { id: '3', type: 'research_started', description: 'Started research: SaaS pricing benchmarks', caseName: 'Pricing Model', timestamp: '5h ago' },
  { id: '4', type: 'case_created', description: 'Created new decision case', caseName: 'Analytics Platform', timestamp: '8h ago' },
  { id: '6', type: 'evidence_added', description: 'Added competitor pricing data', caseName: 'Pricing Model', timestamp: '1d ago' },
  { id: '7', type: 'inquiry_resolved', description: 'Resolved: "What are the team skill gaps?"', caseName: 'Team Restructuring', timestamp: '2d ago' },
];

const MOCK_THREADS: BriefThread[] = [
  { id: '1', title: 'Should we pivot our EU strategy given new tariffs?', caseName: 'EU Expansion', timestamp: '2h ago', messageCount: 12 },
  { id: '2', title: 'Research on SaaS pricing models in 2025', caseName: 'Pricing Model', timestamp: '1d ago', messageCount: 8 },
  { id: '3', title: 'Comparing analytics vendors: Amplitude vs Mixpanel', timestamp: '2d ago', messageCount: 15 },
];

const MOCK_DISCOVER: DiscoverItem[] = [
  { id: '1', headline: 'EU Digital Markets Act: What it means for SaaS expansion', summary: 'New compliance requirements and market opportunities emerging from recent regulatory changes.', source: 'TechPolicy Review', relatedCase: 'EU Expansion', gradientFrom: 'from-blue-500/20', gradientTo: 'to-purple-500/20' },
  { id: '2', headline: 'The state of SaaS pricing in 2025', summary: 'Usage-based pricing continues to gain ground, but hybrid models show strongest retention.', source: 'SaaS Weekly', relatedCase: 'Pricing Model', gradientFrom: 'from-emerald-500/20', gradientTo: 'to-teal-500/20' },
  { id: '3', headline: 'Build vs buy in the age of AI: A framework', summary: 'How AI is changing the calculus for build-versus-buy decisions in analytics and data platforms.', source: 'a16z Insights', relatedCase: 'Analytics Platform', gradientFrom: 'from-orange-500/20', gradientTo: 'to-red-500/20' },
];

// ═══════════════════════════════════════════════════════
// Stage config
// ═══════════════════════════════════════════════════════

const STAGE_STYLES: Record<BriefDecision['stage'], { label: string; bg: string; text: string }> = {
  exploring: { label: 'Exploring', bg: 'bg-neutral-100 dark:bg-neutral-800', text: 'text-neutral-600 dark:text-neutral-400' },
  investigating: { label: 'Investigating', bg: 'bg-info-100 dark:bg-info-900/30', text: 'text-info-700 dark:text-info-300' },
  synthesizing: { label: 'Synthesizing', bg: 'bg-warning-100 dark:bg-warning-900/30', text: 'text-warning-700 dark:text-warning-300' },
  ready: { label: 'Ready', bg: 'bg-success-100 dark:bg-success-900/30', text: 'text-success-700 dark:text-success-300' },
};

const MOMENTUM_ICONS: Record<BriefDecision['momentum'], { icon: string; color: string }> = {
  up: { icon: '\u25b2', color: 'text-success-500' },
  steady: { icon: '\u25b6', color: 'text-neutral-400' },
  down: { icon: '\u25bc', color: 'text-warning-500' },
};

const ACTION_ICONS: Record<BriefAction['type'], string> = {
  resolve: '\u26a1',
  research: '\ud83d\udcca',
  assumptions: '\u26a0\ufe0f',
  investigate: '\ud83d\udd0d',
  criteria: '\u2705',
};

const ACTIVITY_ICONS: Record<BriefActivity['type'], { icon: string; color: string }> = {
  inquiry_resolved: { icon: '\ud83d\udfe2', color: 'bg-success-500' },
  evidence_added: { icon: '\ud83d\udcc4', color: 'bg-info-500' },
  research_started: { icon: '\ud83d\udd2c', color: 'bg-accent-500' },
  case_created: { icon: '\u2728', color: 'bg-neutral-500' },
};

const VARIANT_STYLES: Record<BriefAction['variant'], { bg: string; border: string }> = {
  warning: { bg: 'bg-warning-50/50 dark:bg-warning-900/10', border: 'border-warning-200 dark:border-warning-800' },
  info: { bg: 'bg-info-50/50 dark:bg-info-900/10', border: 'border-info-200 dark:border-info-800' },
  success: { bg: 'bg-success-50/50 dark:bg-success-900/10', border: 'border-success-200 dark:border-success-800' },
  accent: { bg: 'bg-accent-50/50 dark:bg-accent-900/10', border: 'border-accent-200 dark:border-accent-800' },
  default: { bg: 'bg-neutral-50 dark:bg-neutral-900/50', border: 'border-neutral-200 dark:border-neutral-800' },
};

// ═══════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════

export function BriefDashboard() {
  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 pb-12">
      {/* Row 1: Active Decisions + Action Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ActiveDecisionsSection decisions={MOCK_DECISIONS} />
        <ActionQueueSection actions={MOCK_ACTIONS} />
      </div>

      {/* Row 2: Recent Activity + Recent Threads */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentActivitySection activities={MOCK_ACTIVITY} />
        <RecentThreadsSection threads={MOCK_THREADS} />
      </div>

      {/* Row 3: Discover (full width) */}
      <DiscoverSection items={MOCK_DISCOVER} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════
// Section 1: Active Decisions
// ═══════════════════════════════════════════════════════

function ActiveDecisionsSection({ decisions }: { decisions: BriefDecision[] }) {
  return (
    <section>
      <SectionHeader title="Active Decisions" count={decisions.length} />
      <div className="space-y-2">
        {decisions.map((d) => {
          const stage = STAGE_STYLES[d.stage];
          const momentum = MOMENTUM_ICONS[d.momentum];
          const progress = d.inquiries.total > 0
            ? Math.round((d.inquiries.resolved / d.inquiries.total) * 100)
            : 0;

          return (
            <Link
              key={d.id}
              href={`/cases/${d.id}`}
              className={cn(
                'block rounded-lg border p-3',
                'border-neutral-200 dark:border-neutral-800',
                'bg-white dark:bg-neutral-900/50',
                'hover:border-accent-300 dark:hover:border-accent-700',
                'transition-colors duration-150'
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-neutral-900 dark:text-neutral-100 truncate">
                    {d.title}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded', stage.bg, stage.text)}>
                      {stage.label}
                    </span>
                    <span className="text-[10px] text-neutral-500 dark:text-neutral-400">
                      {d.inquiries.resolved}/{d.inquiries.total} inquiries
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={cn('text-[10px]', momentum.color)}>{momentum.icon}</span>
                  <span className="text-[10px] text-neutral-400">{d.updatedAt}</span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mt-2 h-1 rounded-full bg-neutral-100 dark:bg-neutral-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-accent-500 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════
// Section 2: Action Queue
// ═══════════════════════════════════════════════════════

function ActionQueueSection({ actions }: { actions: BriefAction[] }) {
  return (
    <section>
      <SectionHeader title="Action Queue" count={actions.length} />
      <div className="space-y-1.5">
        {actions.map((a) => {
          const styles = VARIANT_STYLES[a.variant];
          return (
            <div
              key={a.id}
              className={cn(
                'flex items-start gap-2 rounded-lg border p-2.5 cursor-pointer',
                styles.bg, styles.border,
                'hover:shadow-sm transition-all duration-150'
              )}
            >
              <span className="text-sm shrink-0 mt-0.5">{ACTION_ICONS[a.type]}</span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-neutral-900 dark:text-neutral-100 line-clamp-1">
                  {a.title}
                </p>
                <p className="text-[10px] text-neutral-500 dark:text-neutral-400 mt-0.5">
                  {a.caseName}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════
// Section 3: Recent Activity
// ═══════════════════════════════════════════════════════

function RecentActivitySection({ activities }: { activities: BriefActivity[] }) {
  return (
    <section>
      <SectionHeader title="Recent Activity" />
      <div className="relative pl-4">
        {/* Timeline line */}
        <div className="absolute left-[7px] top-2 bottom-2 w-px bg-neutral-200 dark:bg-neutral-800" />

        <div className="space-y-3">
          {activities.map((a) => {
            const config = ACTIVITY_ICONS[a.type];
            return (
              <div key={a.id} className="flex items-start gap-3 relative">
                {/* Timeline dot */}
                <div className={cn(
                  'absolute left-[-13px] top-1 w-2 h-2 rounded-full border-2 border-white dark:border-neutral-950',
                  config.color
                )} />

                <div className="min-w-0 flex-1">
                  <p className="text-xs text-neutral-700 dark:text-neutral-300 line-clamp-1">
                    {a.description}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-neutral-500 dark:text-neutral-400">{a.timestamp}</span>
                    <span className="text-[10px] text-accent-600 dark:text-accent-400">{a.caseName}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════
// Section 4: Recent Threads
// ═══════════════════════════════════════════════════════

function RecentThreadsSection({ threads }: { threads: BriefThread[] }) {
  return (
    <section>
      <SectionHeader title="Recent Threads" />
      <div className="space-y-2">
        {threads.map((t) => (
          <Link
            key={t.id}
            href={`/chat/${t.id}`}
            className={cn(
              'block rounded-lg border p-3',
              'border-neutral-200 dark:border-neutral-800',
              'bg-white dark:bg-neutral-900/50',
              'hover:border-accent-300 dark:hover:border-accent-700',
              'transition-colors duration-150'
            )}
          >
            <p className="text-xs font-medium text-neutral-900 dark:text-neutral-100 line-clamp-1">
              {t.title}
            </p>
            <div className="flex items-center gap-2 mt-1.5">
              {t.caseName && (
                <span className="text-[10px] font-medium text-accent-600 dark:text-accent-400 bg-accent-50 dark:bg-accent-900/30 px-1.5 py-0.5 rounded">
                  {t.caseName}
                </span>
              )}
              <span className="text-[10px] text-neutral-400">{t.timestamp}</span>
              <span className="text-[10px] text-neutral-400">{t.messageCount} msgs</span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════
// Section 5: Discover
// ═══════════════════════════════════════════════════════

function DiscoverSection({ items }: { items: DiscoverItem[] }) {
  return (
    <section>
      <SectionHeader title="Discover" subtitle="Curated for your decisions" />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {items.map((item) => (
          <div
            key={item.id}
            className={cn(
              'rounded-lg border overflow-hidden cursor-pointer group',
              'border-neutral-200 dark:border-neutral-800',
              'hover:border-accent-300 dark:hover:border-accent-700',
              'hover:shadow-sm transition-all duration-150'
            )}
          >
            {/* Gradient thumbnail placeholder */}
            <div className={cn(
              'h-20 bg-gradient-to-br',
              item.gradientFrom, item.gradientTo,
              'dark:opacity-60'
            )} />

            <div className="p-3">
              <p className="text-xs font-medium text-neutral-900 dark:text-neutral-100 line-clamp-2 group-hover:text-accent-700 dark:group-hover:text-accent-300 transition-colors">
                {item.headline}
              </p>
              <p className="text-[10px] text-neutral-500 dark:text-neutral-400 mt-1 line-clamp-2">
                {item.summary}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[10px] text-neutral-400">{item.source}</span>
                {item.relatedCase && (
                  <span className="text-[10px] text-accent-600 dark:text-accent-400">
                    Related: {item.relatedCase}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════
// Shared Components
// ═══════════════════════════════════════════════════════

function SectionHeader({ title, count, subtitle }: { title: string; count?: number; subtitle?: string }) {
  return (
    <div className="flex items-baseline justify-between mb-3">
      <div className="flex items-baseline gap-2">
        <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          {title}
        </h3>
        {count !== undefined && (
          <span className="text-[11px] text-neutral-400">{count}</span>
        )}
      </div>
      {subtitle && (
        <span className="text-[10px] text-neutral-400">{subtitle}</span>
      )}
    </div>
  );
}
