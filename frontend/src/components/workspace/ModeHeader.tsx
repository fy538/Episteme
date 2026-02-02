/**
 * Mode header - breadcrumb trail + mode badge + quick actions for context awareness
 */

'use client';

import { ReactNode } from 'react';
import { Button } from '@/components/ui/button';

export type WorkspaceMode = 'chatting' | 'editing_brief' | 'researching' | 'reviewing_evidence' | 'viewing_document';

interface Breadcrumb {
  label: string;
  href?: string;
}

interface QuickAction {
  id: string;
  label: string;
  icon: ReactNode;
  onClick: () => void;
}

interface ModeHeaderProps {
  breadcrumbs: Breadcrumb[];
  mode: WorkspaceMode;
  modeLabel?: string;
  quickActions?: QuickAction[];
}

const MODE_STYLES: Record<WorkspaceMode, { bg: string; text: string; label: string }> = {
  chatting: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Chatting' },
  editing_brief: { bg: 'bg-green-100', text: 'text-green-700', label: 'Editing Brief' },
  researching: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Researching' },
  reviewing_evidence: { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Reviewing Evidence' },
  viewing_document: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Viewing Document' },
};

export function ModeHeader({ breadcrumbs, mode, modeLabel, quickActions }: ModeHeaderProps) {
  const modeStyle = MODE_STYLES[mode];
  const displayLabel = modeLabel || modeStyle.label;

  return (
    <div className="flex items-center justify-between px-6 py-3">
      {/* Breadcrumb Trail */}
      <nav className="flex items-center gap-2 text-sm">
        {breadcrumbs.map((crumb, idx) => (
          <div key={idx} className="flex items-center gap-2">
            {idx > 0 && (
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            )}
            {crumb.href ? (
              <a
                href={crumb.href}
                className="text-gray-600 hover:text-gray-900 transition-colors"
              >
                {crumb.label}
              </a>
            ) : (
              <span className="text-gray-900 font-medium">{crumb.label}</span>
            )}
          </div>
        ))}
      </nav>

      {/* Right side: Quick Actions + Mode Badge */}
      <div className="flex items-center gap-3">
        {/* Quick Actions */}
        {quickActions && quickActions.length > 0 && (
          <div className="flex items-center gap-2">
            {quickActions.map(action => (
              <Button
                key={action.id}
                size="sm"
                variant="ghost"
                onClick={action.onClick}
                className="text-neutral-700 hover:text-accent-600"
                title={action.label}
              >
                {action.icon}
                <span className="ml-1 hidden lg:inline">{action.label}</span>
              </Button>
            ))}
          </div>
        )}

        {/* Mode Badge */}
        <div className={`px-3 py-1 rounded-full text-xs font-medium ${modeStyle.bg} ${modeStyle.text}`}>
          {displayLabel}
        </div>
      </div>
    </div>
  );
}
