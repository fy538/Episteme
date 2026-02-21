/**
 * Companion section ranking — determines which sections are most relevant.
 *
 * Sections compete for visibility based on:
 * - Streaming: actively streaming content ranks highest
 * - Recency: content that just changed ranks high
 * - Content: sections with data outrank empty ones
 * - Pinning: user-pinned sections stay promoted
 * - Mode: case_state ranks high in case mode, zero in casual
 */

import type { ActionHint } from '@/lib/types/chat';
import type {
  ChatMode,
  BackgroundWorkItem,
  SessionReceipt,
  CaseState,
  ConversationStructure,
  ConversationEpisode,
} from '@/lib/types/companion';

export type CompanionSectionId =
  | 'thinking'
  | 'action_hints'
  | 'status'
  | 'receipts'
  | 'case_state'
  | 'conversation_structure'
  | 'episode_timeline';

export interface SectionRankingInput {
  thinking: { content: string; isStreaming: boolean };
  actionHints: ActionHint[];
  status: { inProgress: BackgroundWorkItem[]; justCompleted: BackgroundWorkItem[] };
  sessionReceipts: SessionReceipt[];
  caseState?: CaseState;
  conversationStructure?: ConversationStructure;
  episodeHistory?: ConversationEpisode[];
  mode: ChatMode;
  pinnedSection?: CompanionSectionId | null;
  lastUpdated: Partial<Record<CompanionSectionId, number>>;
  /** Number of completed assistant responses this session. Used for early-turn thinking boost. */
  turnCount?: number;
}

const SCORE_STREAMING = 100;
const SCORE_JUST_ARRIVED = 50;
const SCORE_PINNED = 30;
const SCORE_MODE_MATCH = 25;
const SCORE_HAS_CONTENT = 20;
const SCORE_EARLY_TURN_BOOST = 35;
const SCORE_STALE_PENALTY = -10;
const JUST_ARRIVED_MS = 5000;
const STALE_MS = 60000;

function hasContent(id: CompanionSectionId, input: SectionRankingInput): boolean {
  switch (id) {
    case 'thinking':
      return input.thinking.content.trim().length > 0 || input.thinking.isStreaming;
    case 'action_hints':
      return input.actionHints.length > 0;
    case 'status':
      return input.status.inProgress.length > 0 || input.status.justCompleted.length > 0;
    case 'receipts':
      return input.sessionReceipts.length > 0;
    case 'case_state':
      return input.caseState != null;
    case 'conversation_structure':
      return input.conversationStructure != null;
    case 'episode_timeline':
      return (input.episodeHistory ?? []).length > 0;
  }
}

export function rankSections(input: SectionRankingInput): CompanionSectionId[] {
  const now = Date.now();
  const allSections: CompanionSectionId[] = [
    'conversation_structure', 'episode_timeline', 'thinking', 'action_hints', 'status', 'receipts', 'case_state',
  ];

  const scored = allSections
    .filter(id => hasContent(id, input))
    .map(id => {
      let score = 0;

      // Streaming — only thinking can stream
      if (id === 'thinking' && input.thinking.isStreaming) {
        score += SCORE_STREAMING;
      }

      // Just arrived — content changed recently
      const lastUpdate = input.lastUpdated[id];
      if (lastUpdate && now - lastUpdate < JUST_ARRIVED_MS) {
        score += SCORE_JUST_ARRIVED;
      }

      // User pinned
      if (input.pinnedSection === id) {
        score += SCORE_PINNED;
      }

      // Mode match — case_state only relevant in case/inquiry_focus mode
      if (id === 'case_state' && (input.mode === 'case' || input.mode === 'inquiry_focus')) {
        score += SCORE_MODE_MATCH;
      }
      // Status is more relevant in case mode (background research)
      if (id === 'status' && input.mode !== 'casual') {
        score += SCORE_MODE_MATCH * 0.5;
      }
      // Conversation structure is always relevant and gets a boost
      if (id === 'conversation_structure') {
        score += SCORE_MODE_MATCH;
      }
      // Episode timeline is mildly relevant when present
      if (id === 'episode_timeline') {
        score += SCORE_MODE_MATCH * 0.5;
      }

      // Has content baseline
      score += SCORE_HAS_CONTENT;

      // Early-turn boost: keep thinking visible in first exchanges
      // so users see the companion is actively processing their input
      if (id === 'thinking' && input.turnCount != null && input.turnCount <= 2) {
        score += SCORE_EARLY_TURN_BOOST;
      }

      // Stale penalty — content unchanged for a while
      if (lastUpdate && now - lastUpdate > STALE_MS) {
        score += SCORE_STALE_PENALTY;
      }

      return { id, score };
    });

  scored.sort((a, b) => b.score - a.score);
  return scored.map(s => s.id);
}
