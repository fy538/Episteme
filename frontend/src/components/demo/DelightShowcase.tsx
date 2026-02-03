/**
 * Delight Features Showcase
 * Demo component showing all Phase 3 micro-interactions
 * 
 * Usage: Add to any page to test the new features
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Confetti, useConfetti } from '@/components/ui/confetti';
import { SwipeableItem } from '@/components/ui/swipeable-item';
import { DragReorder } from '@/components/ui/drag-reorder';
import { Pulse, Wobble, Bounce, Shake, Glow } from '@/components/ui/micro-interactions';
import { useMicroInteraction } from '@/components/ui/micro-interactions';

export function DelightShowcase() {
  const { trigger: confettiTrigger, shouldTrigger } = useConfetti();
  const [items, setItems] = useState([
    { id: '1', name: 'First Item' },
    { id: '2', name: 'Second Item' },
    { id: '3', name: 'Third Item' },
  ]);

  const pulseTrigger = useMicroInteraction();
  const wobbleTrigger = useMicroInteraction();
  const bounceTrigger = useMicroInteraction();
  const shakeTrigger = useMicroInteraction();
  const [isGlowing, setIsGlowing] = useState(false);

  return (
    <div className="max-w-4xl mx-auto p-8 space-y-8">
      <h1 className="text-3xl tracking-tight font-bold">Phase 3: Delight Features</h1>

      {/* Confetti */}
      <section className="space-y-4">
        <h2 className="text-xl font-display font-semibold tracking-tight">1. Confetti Celebration</h2>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Triggered on achievements (case completion, validation success)
        </p>
        <Button onClick={confettiTrigger}>
          🎉 Trigger Confetti
        </Button>
        <Confetti trigger={shouldTrigger} />
      </section>

      {/* Swipe to Delete */}
      <section className="space-y-4">
        <h2 className="text-xl font-display font-semibold tracking-tight">2. Swipe to Delete/Archive</h2>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Mobile-style swipe gestures (try swiping left or right)
        </p>
        <SwipeableItem
          onSwipeLeft={() => alert('Deleted!')}
          onSwipeRight={() => alert('Archived!')}
          leftAction={{
            icon: <span>📦</span>,
            color: '#0891b2',
            label: 'Archive',
          }}
          rightAction={{
            icon: <span>🗑️</span>,
            color: '#e11d48',
            label: 'Delete',
          }}
        >
          <div className="bg-white dark:bg-neutral-800 p-4 rounded-lg border border-neutral-200 dark:border-neutral-700">
            <p className="font-medium">Swipe me left or right!</p>
            <p className="text-sm text-neutral-500">Try on mobile for best experience</p>
          </div>
        </SwipeableItem>
      </section>

      {/* Drag to Reorder */}
      <section className="space-y-4">
        <h2 className="text-xl font-display font-semibold tracking-tight">3. Drag to Reorder</h2>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Reorder items by dragging (grab the items and move them)
        </p>
        <DragReorder
          items={items}
          onReorder={setItems}
          keyExtractor={(item) => item.id}
          renderItem={(item) => (
            <div className="bg-white dark:bg-neutral-800 p-4 mb-2 rounded-lg border border-neutral-200 dark:border-neutral-700">
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
                </svg>
                <span className="font-medium">{item.name}</span>
              </div>
            </div>
          )}
          className="space-y-2"
        />
      </section>

      {/* Micro-interactions */}
      <section className="space-y-4">
        <h2 className="text-xl font-display font-semibold tracking-tight">4. Micro-interactions</h2>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Small delightful animations for feedback
        </p>
        
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {/* Pulse */}
          <div className="text-center space-y-2">
            <Pulse trigger={pulseTrigger.trigger}>
              <div className="w-16 h-16 mx-auto bg-accent-500 rounded-lg flex items-center justify-center text-2xl">
                💫
              </div>
            </Pulse>
            <Button size="sm" onClick={pulseTrigger.fire}>
              Pulse
            </Button>
          </div>

          {/* Wobble */}
          <div className="text-center space-y-2">
            <Wobble trigger={wobbleTrigger.trigger}>
              <div className="w-16 h-16 mx-auto bg-warning-500 rounded-lg flex items-center justify-center text-2xl">
                🎯
              </div>
            </Wobble>
            <Button size="sm" onClick={wobbleTrigger.fire}>
              Wobble
            </Button>
          </div>

          {/* Bounce */}
          <div className="text-center space-y-2">
            <Bounce trigger={bounceTrigger.trigger}>
              <div className="w-16 h-16 mx-auto bg-success-500 rounded-lg flex items-center justify-center text-2xl">
                ⬆️
              </div>
            </Bounce>
            <Button size="sm" onClick={bounceTrigger.fire}>
              Bounce
            </Button>
          </div>

          {/* Shake */}
          <div className="text-center space-y-2">
            <Shake trigger={shakeTrigger.trigger}>
              <div className="w-16 h-16 mx-auto bg-error-500 rounded-lg flex items-center justify-center text-2xl">
                ⚠️
              </div>
            </Shake>
            <Button size="sm" onClick={shakeTrigger.fire}>
              Shake
            </Button>
          </div>

          {/* Glow */}
          <div className="text-center space-y-2">
            <Glow active={isGlowing} color="#14b8a6">
              <div className="w-16 h-16 mx-auto bg-accent-500 rounded-lg flex items-center justify-center text-2xl">
                ✨
              </div>
            </Glow>
            <Button
              size="sm"
              onClick={() => setIsGlowing(!isGlowing)}
            >
              {isGlowing ? 'Stop Glow' : 'Glow'}
            </Button>
          </div>
        </div>
      </section>

      {/* Usage Examples */}
      <section className="space-y-4 bg-neutral-50 dark:bg-neutral-900 p-6 rounded-lg">
        <h2 className="text-xl font-display font-semibold tracking-tight">When to Use Each Feature</h2>
        <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
          <li>
            <strong className="text-neutral-900 dark:text-neutral-100">Confetti:</strong> Case
            completed, inquiry validated, major milestone achieved
          </li>
          <li>
            <strong className="text-neutral-900 dark:text-neutral-100">Swipe:</strong> Delete
            conversations, archive threads (mobile-friendly)
          </li>
          <li>
            <strong className="text-neutral-900 dark:text-neutral-100">Drag to Reorder:</strong> Prioritize
            inquiries, organize cases
          </li>
          <li>
            <strong className="text-neutral-900 dark:text-neutral-100">Pulse:</strong> New signal
            detected, important update
          </li>
          <li>
            <strong className="text-neutral-900 dark:text-neutral-100">Wobble:</strong> Invalid
            input, action failed
          </li>
          <li>
            <strong className="text-neutral-900 dark:text-neutral-100">Bounce:</strong> Item added
            to list, success action
          </li>
          <li>
            <strong className="text-neutral-900 dark:text-neutral-100">Shake:</strong> Error,
            critical warning
          </li>
          <li>
            <strong className="text-neutral-900 dark:text-neutral-100">Glow:</strong> Active
            investigation, live data
          </li>
        </ul>
      </section>
    </div>
  );
}
