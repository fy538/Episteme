/**
 * Timeline Mapper
 *
 * Maps raw Event items from the event store into a structured tree
 * for the home page ActivityTimeline.
 *
 * Two output modes:
 * - mapEventsToTimeline(): flat list (legacy, kept for compatibility)
 * - buildTimelineTree():   clustered tree grouped by case + time proximity
 *
 * The tree builder uses correlation_id when available, otherwise
 * clusters child events under the nearest parent on the same case
 * within a 2-hour window.
 */

import type { EventItem } from '@/lib/api/events';

export type TimelineIcon = 'check' | 'plus' | 'zap' | 'refresh' | 'layers' | 'file';
export type TimelineAccent = 'success' | 'accent' | 'neutral';

export type TimelineLevel = 'parent' | 'child';

export interface TimelineEntry {
  id: string;
  timestamp: string;
  heading: string;
  caseTitle: string | null;
  caseId: string | null;
  icon: TimelineIcon;
  accent: TimelineAccent;
  eventType: string;
  /** 'parent' = case-level event, 'child' = inquiry-level event */
  level: TimelineLevel;
  correlationId?: string | null;
}

export interface TimelineCluster {
  id: string;
  parentEntry: TimelineEntry;
  children: TimelineEntry[];
  caseId: string | null;
  caseTitle: string | null;
  timestamp: string; // most recent timestamp in cluster
}

interface EventMapping {
  heading: (payload: Record<string, any>) => string;
  icon: TimelineIcon;
  accent: TimelineAccent;
  caseTitle: (payload: Record<string, any>) => string | null;
  level: TimelineLevel;
}

const EVENT_MAP: Record<string, EventMapping> = {
  CaseCreated: {
    heading: (p) => `Created ${p.title || 'new case'}`,
    icon: 'zap',
    accent: 'accent',
    caseTitle: () => null, // title already in heading
    level: 'parent',
  },
  CaseCreatedFromAnalysis: {
    heading: (p) => `Created ${p.analysis?.title || 'case'} from conversation`,
    icon: 'zap',
    accent: 'accent',
    caseTitle: () => null, // title already in heading
    level: 'parent',
  },
  InquiryCreated: {
    heading: (p) => `New inquiry: ${p.title || 'Untitled'}`,
    icon: 'plus',
    accent: 'neutral',
    caseTitle: (p) => p.case_title || null,
    level: 'child',
  },
  InquiryResolved: {
    heading: (p) => `Resolved: ${p.title || 'inquiry'}`,
    icon: 'check',
    accent: 'success',
    caseTitle: (p) => p.case_title || null,
    level: 'child',
  },
  BriefEvolved: {
    heading: (p) => {
      const n = p.sections_updated;
      return n ? `Brief updated (${n} ${n === 1 ? 'section' : 'sections'})` : 'Brief updated';
    },
    icon: 'refresh',
    accent: 'neutral',
    caseTitle: (p) => p.case_title || null,
    level: 'parent',
  },
  CaseScaffolded: {
    heading: () => 'Built case structure',
    icon: 'layers',
    accent: 'accent',
    caseTitle: (p) => p.case_title || null,
    level: 'parent',
  },
  WorkflowCompleted: {
    heading: (p) => `Research completed${p.title ? `: ${p.title}` : ''}`,
    icon: 'file',
    accent: 'neutral',
    caseTitle: (p) => p.case_title || null,
    level: 'parent',
  },
};

/** Map raw events to timeline entries, dropping unknown types */
export function mapEventsToTimeline(events: EventItem[]): TimelineEntry[] {
  const entries: TimelineEntry[] = [];

  for (const event of events) {
    const mapping = EVENT_MAP[event.type];
    if (!mapping) continue;

    entries.push({
      id: event.id,
      timestamp: event.timestamp,
      heading: mapping.heading(event.payload),
      caseTitle: mapping.caseTitle(event.payload),
      caseId: event.case_id,
      icon: mapping.icon,
      accent: mapping.accent,
      eventType: event.type,
      level: mapping.level,
      correlationId: event.correlation_id || null,
    });
  }

  return entries;
}

// --- Tree Builder ---

/** Max time gap (ms) for clustering child events under a parent */
const CLUSTER_WINDOW_MS = 2 * 60 * 60 * 1000; // 2 hours
const MAX_CLUSTERS = 8;

/**
 * Build a clustered tree from flat events.
 *
 * Strategy:
 * 1. Convert events to entries
 * 2. Group by correlation_id when present
 * 3. For uncorrelated events, cluster children under the nearest
 *    parent on the same case within CLUSTER_WINDOW_MS
 * 4. Orphan children become standalone clusters
 */
export function buildTimelineTree(events: EventItem[]): TimelineCluster[] {
  const entries = mapEventsToTimeline(events);
  if (entries.length === 0) return [];

  // Phase 1: Group by correlation_id
  const correlationGroups = new Map<string, TimelineEntry[]>();
  const uncorrelated: TimelineEntry[] = [];

  for (const entry of entries) {
    if (entry.correlationId) {
      const group = correlationGroups.get(entry.correlationId) || [];
      group.push(entry);
      correlationGroups.set(entry.correlationId, group);
    } else {
      uncorrelated.push(entry);
    }
  }

  // Phase 2: Build clusters from correlation groups
  const clusters: TimelineCluster[] = [];

  for (const [, group] of correlationGroups) {
    // Pick the first parent-level entry as cluster parent, or first entry
    const parentIdx = group.findIndex(e => e.level === 'parent');
    const parent = parentIdx >= 0 ? group[parentIdx] : group[0];
    const children = group.filter(e => e.id !== parent.id);

    clusters.push({
      id: parent.id,
      parentEntry: parent,
      children,
      caseId: parent.caseId,
      caseTitle: parent.caseTitle || children.find(c => c.caseTitle)?.caseTitle || null,
      timestamp: group[0].timestamp, // newest in group (entries are newest-first)
    });
  }

  // Phase 3: Cluster uncorrelated entries by case_id + time proximity
  // Parents create new clusters; children attach to nearest matching cluster
  const pendingChildren: TimelineEntry[] = [];

  for (const entry of uncorrelated) {
    if (entry.level === 'parent') {
      clusters.push({
        id: entry.id,
        parentEntry: entry,
        children: [],
        caseId: entry.caseId,
        caseTitle: entry.caseTitle,
        timestamp: entry.timestamp,
      });
    } else {
      pendingChildren.push(entry);
    }
  }

  // Attach pending children to nearest cluster on same case within time window
  for (const child of pendingChildren) {
    const childTime = new Date(child.timestamp).getTime();
    let bestCluster: TimelineCluster | null = null;
    let bestGap = Infinity;

    for (const cluster of clusters) {
      if (cluster.caseId && cluster.caseId === child.caseId) {
        const clusterTime = new Date(cluster.timestamp).getTime();
        const gap = Math.abs(childTime - clusterTime);
        if (gap < CLUSTER_WINDOW_MS && gap < bestGap) {
          bestGap = gap;
          bestCluster = cluster;
        }
      }
    }

    if (bestCluster) {
      bestCluster.children.push(child);
      // Propagate case title if missing
      if (!bestCluster.caseTitle && child.caseTitle) {
        bestCluster.caseTitle = child.caseTitle;
      }
    } else {
      // Orphan child becomes standalone cluster
      clusters.push({
        id: child.id,
        parentEntry: child,
        children: [],
        caseId: child.caseId,
        caseTitle: child.caseTitle,
        timestamp: child.timestamp,
      });
    }
  }

  // Phase 4: Sort clusters newest-first and cap
  clusters.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  return clusters.slice(0, MAX_CLUSTERS);
}

// --- Placeholder Data ---

/**
 * Generate realistic placeholder clusters for UI development.
 * Returns tree data that exercises all visual states:
 * parent-only, parent+children, collapsed children, multiple day groups.
 */
export function generatePlaceholderTree(): TimelineCluster[] {
  const now = new Date();
  const h = (hours: number) => new Date(now.getTime() - hours * 3600000).toISOString();
  const d = (days: number) => new Date(now.getTime() - days * 86400000).toISOString();

  let id = 0;
  const makeEntry = (
    overrides: Partial<TimelineEntry> & Pick<TimelineEntry, 'heading' | 'icon' | 'accent' | 'eventType' | 'level' | 'timestamp'>
  ): TimelineEntry => ({
    id: `placeholder-${++id}`,
    caseTitle: null,
    caseId: null,
    correlationId: null,
    ...overrides,
  });

  return [
    // Cluster 1: Case created with 3 child inquiries (today, 2h ago)
    {
      id: 'cluster-1',
      timestamp: h(2),
      caseId: 'case-1',
      caseTitle: 'Market Entry Analysis',
      parentEntry: makeEntry({
        heading: 'Created "Market Entry Analysis"',
        icon: 'zap',
        accent: 'accent',
        eventType: 'CaseCreated',
        level: 'parent',
        timestamp: h(2),
        caseId: 'case-1',
      }),
      children: [
        makeEntry({
          heading: 'New inquiry: Competitor pricing strategy',
          icon: 'plus',
          accent: 'neutral',
          eventType: 'InquiryCreated',
          level: 'child',
          timestamp: h(2),
          caseId: 'case-1',
          caseTitle: 'Market Entry Analysis',
        }),
        makeEntry({
          heading: 'New inquiry: Market sizing estimates',
          icon: 'plus',
          accent: 'neutral',
          eventType: 'InquiryCreated',
          level: 'child',
          timestamp: h(1.5),
          caseId: 'case-1',
          caseTitle: 'Market Entry Analysis',
        }),
        makeEntry({
          heading: 'Research completed: Competitive landscape',
          icon: 'file',
          accent: 'neutral',
          eventType: 'WorkflowCompleted',
          level: 'child',
          timestamp: h(1),
          caseId: 'case-1',
          caseTitle: 'Market Entry Analysis',
        }),
      ],
    },

    // Cluster 2: Standalone resolved inquiry (today, 4h ago)
    {
      id: 'cluster-2',
      timestamp: h(4),
      caseId: 'case-2',
      caseTitle: 'Supply Chain Decision',
      parentEntry: makeEntry({
        heading: 'Resolved: Supply chain risk assessment',
        icon: 'check',
        accent: 'success',
        eventType: 'InquiryResolved',
        level: 'parent',
        timestamp: h(4),
        caseId: 'case-2',
        caseTitle: 'Supply Chain Decision',
      }),
      children: [],
    },

    // Cluster 3: Brief update with structure build (today, 5h ago)
    {
      id: 'cluster-3',
      timestamp: h(5),
      caseId: 'case-3',
      caseTitle: 'Product Launch Brief',
      parentEntry: makeEntry({
        heading: 'Brief updated (3 sections)',
        icon: 'refresh',
        accent: 'neutral',
        eventType: 'BriefEvolved',
        level: 'parent',
        timestamp: h(5),
        caseId: 'case-3',
        caseTitle: 'Product Launch Brief',
      }),
      children: [
        makeEntry({
          heading: 'Built case structure',
          icon: 'layers',
          accent: 'accent',
          eventType: 'CaseScaffolded',
          level: 'child',
          timestamp: h(5),
          caseId: 'case-3',
          caseTitle: 'Product Launch Brief',
        }),
      ],
    },

    // Cluster 4: Case with many inquiries (yesterday)
    {
      id: 'cluster-4',
      timestamp: d(1),
      caseId: 'case-4',
      caseTitle: 'Hiring Decision',
      parentEntry: makeEntry({
        heading: 'Created "Hiring Decision"',
        icon: 'zap',
        accent: 'accent',
        eventType: 'CaseCreated',
        level: 'parent',
        timestamp: d(1),
        caseId: 'case-4',
      }),
      children: [
        makeEntry({
          heading: 'New inquiry: Compensation benchmarks',
          icon: 'plus',
          accent: 'neutral',
          eventType: 'InquiryCreated',
          level: 'child',
          timestamp: d(1),
          caseId: 'case-4',
          caseTitle: 'Hiring Decision',
        }),
        makeEntry({
          heading: 'New inquiry: Team fit assessment',
          icon: 'plus',
          accent: 'neutral',
          eventType: 'InquiryCreated',
          level: 'child',
          timestamp: d(1),
          caseId: 'case-4',
          caseTitle: 'Hiring Decision',
        }),
        makeEntry({
          heading: 'Research completed: Role market analysis',
          icon: 'file',
          accent: 'neutral',
          eventType: 'WorkflowCompleted',
          level: 'child',
          timestamp: d(1),
          caseId: 'case-4',
          caseTitle: 'Hiring Decision',
        }),
      ],
    },

    // Cluster 5: Standalone (yesterday)
    {
      id: 'cluster-5',
      timestamp: d(1.2),
      caseId: 'case-2',
      caseTitle: 'Supply Chain Decision',
      parentEntry: makeEntry({
        heading: 'Resolved: Logistics cost comparison',
        icon: 'check',
        accent: 'success',
        eventType: 'InquiryResolved',
        level: 'parent',
        timestamp: d(1.2),
        caseId: 'case-2',
        caseTitle: 'Supply Chain Decision',
      }),
      children: [],
    },
  ];
}
