/**
 * Demo page for Phase 3 features
 * Visit /demo to see all the new micro-interactions
 */

'use client';

import { DelightShowcase } from '@/components/demo/DelightShowcase';

export default function DemoPage() {
  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-primary-950 py-8">
      <DelightShowcase />
    </div>
  );
}
