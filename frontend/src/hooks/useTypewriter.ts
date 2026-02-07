/**
 * useTypewriter Hook
 *
 * Animates placeholder text with a typewriter effect:
 * 1. Types characters in one at a time (~40ms per char)
 * 2. Holds the full text (~5s)
 * 3. Deletes characters backwards (~25ms per char)
 * 4. Brief pause (~400ms), then next phrase
 *
 * Falls back to instant swap when user prefers reduced motion.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

type Phase = 'typing' | 'holding' | 'deleting' | 'pausing';

const TYPE_SPEED_MS = 40;
const DELETE_SPEED_MS = 25;
const HOLD_DURATION_MS = 5000;
const PAUSE_DURATION_MS = 400;

interface UseTypewriterOptions {
  phrases: string[];
  /** Skip animation, just rotate instantly */
  disabled?: boolean;
  /** Instant rotation interval when disabled (ms) */
  fallbackInterval?: number;
}

export function useTypewriter({
  phrases,
  disabled = false,
  fallbackInterval = 8000,
}: UseTypewriterOptions): string {
  const [phraseIndex, setPhraseIndex] = useState(0);
  const [displayText, setDisplayText] = useState('');
  const [phase, setPhase] = useState<Phase>('typing');
  const charIndex = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const currentPhrase = phrases[phraseIndex] || '';

  // Fallback: instant rotation (reduced motion or disabled)
  useEffect(() => {
    if (!disabled) return;

    setDisplayText(phrases[0] || '');
    const timer = setInterval(() => {
      setPhraseIndex(prev => (prev + 1) % phrases.length);
    }, fallbackInterval);

    return () => clearInterval(timer);
  }, [disabled, phrases, fallbackInterval]);

  // Update display text when phraseIndex changes in disabled mode
  useEffect(() => {
    if (!disabled) return;
    setDisplayText(phrases[phraseIndex] || '');
  }, [disabled, phraseIndex, phrases]);

  // Typewriter animation loop
  useEffect(() => {
    if (disabled) return;

    function tick() {
      switch (phase) {
        case 'typing': {
          if (charIndex.current < currentPhrase.length) {
            charIndex.current += 1;
            setDisplayText(currentPhrase.slice(0, charIndex.current));
            timerRef.current = setTimeout(tick, TYPE_SPEED_MS);
          } else {
            // Done typing — hold
            setPhase('holding');
          }
          break;
        }
        case 'holding': {
          timerRef.current = setTimeout(() => setPhase('deleting'), HOLD_DURATION_MS);
          break;
        }
        case 'deleting': {
          if (charIndex.current > 0) {
            charIndex.current -= 1;
            setDisplayText(currentPhrase.slice(0, charIndex.current));
            timerRef.current = setTimeout(tick, DELETE_SPEED_MS);
          } else {
            // Done deleting — pause then advance
            setPhase('pausing');
          }
          break;
        }
        case 'pausing': {
          timerRef.current = setTimeout(() => {
            setPhraseIndex(prev => (prev + 1) % phrases.length);
            setPhase('typing');
          }, PAUSE_DURATION_MS);
          break;
        }
      }
    }

    tick();

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [phase, currentPhrase, phrases.length, disabled]);

  // Reset charIndex when phrase changes
  useEffect(() => {
    if (disabled) return;
    charIndex.current = 0;
    setDisplayText('');
  }, [phraseIndex, disabled]);

  return displayText;
}
