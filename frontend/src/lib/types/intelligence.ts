/**
 * Intelligence Types
 *
 * These types power the hierarchical intelligence system that surfaces
 * the ONE most important action at each level (Home → Project → Case)
 */

// The types of AI actions we can surface
export type IntelligenceType =
  | 'tension'        // Sources disagree on something important
  | 'blind_spot'     // Missing analysis that should be addressed
  | 'explore'        // New angle or cross-case connection to consider
  | 'research_ready' // Research completed, needs review/integration
  | 'ready'          // Case/inquiry ready for decision
  | 'continue'       // Resume previous work
  | 'stale';         // Not touched recently, might need attention

// Priority determines visual treatment and ordering
export type IntelligencePriority =
  | 'blocking'   // Must address before proceeding
  | 'important'  // Should address soon
  | 'suggested'; // Nice to consider

// The scope this intelligence applies to
export type IntelligenceScope = 'home' | 'project' | 'case' | 'inquiry';

/**
 * A single intelligence item - something the AI wants to surface
 */
export interface IntelligenceItem {
  id: string;
  type: IntelligenceType;
  priority: IntelligencePriority;
  scope: IntelligenceScope;

  // Core content
  title: string;
  description: string;

  // Context breadcrumb - where does this come from?
  projectId?: string;
  projectTitle?: string;
  caseId?: string;
  caseTitle?: string;
  inquiryId?: string;
  inquiryTitle?: string;

  // Type-specific data
  tension?: TensionData;
  blindSpot?: BlindSpotData;
  exploration?: ExplorationData;
  research?: ResearchReadyData;

  // Metadata
  createdAt: string;
  updatedAt?: string;
  dismissed?: boolean;
  dismissedAt?: string;
}

/**
 * Data for tension type - when sources disagree
 */
export interface TensionData {
  sourceA: {
    id: string;
    name: string;
    content: string;
    implication?: string;
  };
  sourceB: {
    id: string;
    name: string;
    content: string;
    implication?: string;
  };
  impact?: string; // How this affects the case
}

/**
 * Data for blind spot type - missing analysis
 */
export interface BlindSpotData {
  area: string;
  impact: string;
  suggestedAction: 'research' | 'discuss' | 'add_inquiry';
  suggestedPrompt?: string; // Pre-filled prompt for research/chat
}

/**
 * Data for exploration type - suggested question or connection
 */
export interface ExplorationData {
  question: string;
  context: string;
  connectionType?: 'cross_case' | 'cross_inquiry' | 'new_angle';
  relatedCaseIds?: string[];
  relatedInquiryIds?: string[];
}

/**
 * Data for research ready type - completed research to review
 */
export interface ResearchReadyData {
  documentId: string;
  documentTitle: string;
  findingsCount: number;
  generatedAt: string;
  suggestedLinks?: {
    inquiryId: string;
    inquiryTitle: string;
    relevance: string;
  }[];
}

/**
 * Activity item for "while you were away" feed
 */
export interface ActivityItem {
  id: string;
  type: 'research_complete' | 'blind_spot_surfaced' | 'tension_detected' |
        'inquiry_resolved' | 'case_ready' | 'document_uploaded';
  title: string;
  description: string;

  // Context
  projectId?: string;
  projectTitle?: string;
  caseId?: string;
  caseTitle?: string;
  inquiryId?: string;
  inquiryTitle?: string;

  // When
  timestamp: string;

  // Is this new since last visit?
  isNew: boolean;
}

/**
 * Readiness status for a case
 */
export interface CaseReadiness {
  caseId: string;
  caseTitle: string;

  // Breakdown
  inquiries: {
    total: number;
    resolved: number;
    investigating: number;
    open: number;
  };

  // Blockers
  tensionsCount: number;
  blindSpotsCount: number;

  // Status
  isReady: boolean;

  // The most important blocker (if any)
  topBlocker?: IntelligenceItem;

  // All blockers for detailed view
  blockers: IntelligenceItem[];
}

/**
 * Readiness status for a project (aggregated from cases)
 */
export interface ProjectReadiness {
  projectId: string;
  projectTitle: string;

  // Case summary
  cases: {
    total: number;
    ready: number;
    inProgress: number;
    blocked: number;
  };

  // The most important action across all cases
  topAction: IntelligenceItem | null;

  // Exploration suggestion for this project
  exploration: IntelligenceItem | null;

  // Per-case readiness
  caseReadiness: CaseReadiness[];
}

/**
 * The complete intelligence state for a given scope
 */
export interface IntelligenceState {
  scope: IntelligenceScope;

  // The ONE thing to focus on
  topAction: IntelligenceItem | null;

  // For project/home: exploration prompt
  exploration: IntelligenceItem | null;

  // Recent activity
  activity: ActivityItem[];

  // All items (for detailed views)
  allItems: IntelligenceItem[];

  // Loading state
  isLoading: boolean;

  // Last updated
  lastUpdated: string;
}

/**
 * Brief generation context settings
 */
export interface BriefContextSettings {
  // What to include
  inquiryIds: string[];
  sourceIds: string[];

  // Focus type
  focus: 'balanced' | 'risk' | 'recommendation' | 'executive';

  // Custom instructions
  customInstructions?: string;
}

/**
 * Continue state - where the user left off
 */
export interface ContinueState {
  // What they were working on
  type: 'case' | 'inquiry' | 'chat' | 'document';

  // IDs
  projectId?: string;
  caseId?: string;
  inquiryId?: string;
  threadId?: string;
  documentId?: string;

  // Display info
  title: string;
  subtitle?: string;
  lastActivity: string;

  // What's new since they left
  newItems?: number;
  newItemsSummary?: string;
}
