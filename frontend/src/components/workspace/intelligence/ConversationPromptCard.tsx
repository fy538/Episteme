/**
 * Conversation Prompt Card
 * Suggests conversation topics to explore
 */

import { IntelligenceCard } from './IntelligenceCard';
import { Button } from '@/components/ui/button';

export function ConversationPromptCard() {
  return (
    <IntelligenceCard
      icon={
        <svg className="w-5 h-5 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      }
      title="Let's strengthen your damages argument"
      description="I noticed your damages calculation needs more support. Your current evidence is circumstantial - want to explore concrete methodologies together?"
      variant="info"
      actions={
        <>
          <Button size="sm" variant="default">
            Start Chat
          </Button>
          <Button size="sm" variant="outline">
            Not Now
          </Button>
        </>
      }
    >
      <div className="text-sm text-neutral-700 dark:text-neutral-300">
        <p className="font-medium mb-1">Suggested topics:</p>
        <ul className="list-disc list-inside space-y-0.5 text-xs">
          <li>Lost profits calculation methods</li>
          <li>Comparable case damages</li>
          <li>Expert witness requirements</li>
        </ul>
      </div>
    </IntelligenceCard>
  );
}
