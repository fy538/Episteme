/**
 * Confetti celebration component
 * Triggers on significant achievements (case completion, validation, etc.)
 */

'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface ConfettiProps {
  trigger: boolean;
  onComplete?: () => void;
}

interface Particle {
  id: number;
  x: number;
  y: number;
  color: string;
  rotation: number;
  scale: number;
}

const COLORS = [
  '#14b8a6', // accent-500
  '#10b981', // success-500
  '#3b82f6', // info-500
  '#f59e0b', // warning-500
  '#ec4899', // pink-500
];

export function Confetti({ trigger, onComplete }: ConfettiProps) {
  const [particles, setParticles] = useState<Particle[]>([]);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    if (!trigger || prefersReducedMotion) return;

    // Generate particles
    const newParticles: Particle[] = Array.from({ length: 50 }, (_, i) => ({
      id: i,
      x: Math.random() * 100 - 50,
      y: -10,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      rotation: Math.random() * 360,
      scale: Math.random() * 0.5 + 0.5,
    }));

    setParticles(newParticles);

    // Clear after animation
    const timer = setTimeout(() => {
      setParticles([]);
      onComplete?.();
    }, 3000);

    return () => clearTimeout(timer);
  }, [trigger, prefersReducedMotion, onComplete]);

  if (prefersReducedMotion || particles.length === 0) return null;

  return (
    <div className="fixed inset-0 pointer-events-none z-[200] overflow-hidden">
      <AnimatePresence>
        {particles.map((particle) => (
          <motion.div
            key={particle.id}
            initial={{
              x: '50vw',
              y: '20vh',
              rotate: 0,
              opacity: 1,
              scale: particle.scale,
            }}
            animate={{
              x: `calc(50vw + ${particle.x}vw)`,
              y: '100vh',
              rotate: particle.rotation,
              opacity: 0,
            }}
            exit={{ opacity: 0 }}
            transition={{
              duration: 2 + Math.random(),
              ease: 'easeOut',
            }}
            className="absolute w-3 h-3 rounded-sm"
            style={{ backgroundColor: particle.color }}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

// Hook for triggering confetti
export function useConfetti() {
  const [shouldTrigger, setShouldTrigger] = useState(false);

  const trigger = () => {
    setShouldTrigger(true);
    setTimeout(() => setShouldTrigger(false), 100);
  };

  return { trigger, shouldTrigger };
}
