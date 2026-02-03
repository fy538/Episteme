/**
 * Animated Message List - Messages with staggered entrance animations
 * Wraps MessageList with framer-motion for smoother feel
 */

'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import type { Message as MessageType } from '@/lib/types/chat';
import type { CardAction } from '@/lib/types/cards';

interface AnimatedMessageProps {
  message: MessageType;
  index: number;
  children: React.ReactNode;
}

function AnimatedMessage({ message, index, children }: AnimatedMessageProps) {
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return <div>{children}</div>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{
        duration: 0.2,
        delay: index < 3 ? index * 0.05 : 0, // Only stagger first 3 messages
        ease: [0.22, 1, 0.36, 1],
      }}
      layout
    >
      {children}
    </motion.div>
  );
}

export { AnimatedMessage };
