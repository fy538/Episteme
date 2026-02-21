/**
 * GenericView — Fallback JSON renderer for unknown structure types.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';

export const GenericView = memo(function GenericView({
  content,
}: {
  content: Record<string, unknown>;
}) {
  return (
    <pre className={cn('text-[10px] overflow-x-auto', theme.thinking.textMuted)}>
      {JSON.stringify(content, null, 2)}
    </pre>
  );
});
