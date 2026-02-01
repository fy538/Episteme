/**
 * Advanced Tab - Skills, debug options, experimental features
 */

'use client';

import * as React from 'react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { UserPreferences } from '@/lib/api/preferences';

interface AdvancedTabProps {
  preferences: Partial<UserPreferences>;
  onChange: (updates: Partial<UserPreferences>) => void;
}

export function AdvancedTab({ preferences, onChange }: AdvancedTabProps) {
  const [showSkills, setShowSkills] = React.useState(false);

  return (
    <div className="space-y-6">
      {/* Skills Section (Collapsed by default) */}
      <div className="border border-neutral-200 rounded-lg">
        <button
          onClick={() => setShowSkills(!showSkills)}
          className="w-full p-4 flex items-center justify-between text-left hover:bg-neutral-50 transition-colors"
        >
          <div>
            <h3 className="text-base font-semibold text-neutral-900">
              Skills & Templates
              <Badge variant="neutral" className="ml-2 text-xs">
                Optional
              </Badge>
            </h3>
            <p className="text-sm text-neutral-600 mt-1">
              Configure domain-specific templates for AI agents
            </p>
          </div>
          <svg
            className={`w-5 h-5 text-neutral-400 transition-transform ${
              showSkills ? 'rotate-180' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        
        {showSkills && (
          <div className="p-4 border-t border-neutral-200 bg-neutral-50">
            <p className="text-sm text-neutral-600 mb-3">
              Skills are powerful but optional. Most users work great with organization defaults.
            </p>
            <div className="flex gap-2">
              <Button size="sm" variant="outline">
                View My Skills
              </Button>
              <Button size="sm" variant="ghost">
                Browse Templates
              </Button>
            </div>
            <p className="text-xs text-neutral-500 mt-3">
              💡 Tip: Skills auto-inject domain knowledge into agents when activated for a case.
            </p>
          </div>
        )}
      </div>

      {/* Notifications */}
      <div>
        <Label className="text-base font-semibold">Notifications</Label>
        <p className="text-sm text-neutral-600 mb-3">
          Control what you get notified about
        </p>
        <div className="space-y-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.email_notifications ?? false}
              onChange={(e) => onChange({ email_notifications: e.target.checked })}
              className="rounded border-neutral-300"
            />
            <span className="text-sm text-neutral-900">
              Email notifications
            </span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.notify_on_inquiry_resolved ?? true}
              onChange={(e) => onChange({ notify_on_inquiry_resolved: e.target.checked })}
              className="rounded border-neutral-300"
            />
            <span className="text-sm text-neutral-900">
              Notify when inquiry is resolved
            </span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.notify_on_agent_complete ?? true}
              onChange={(e) => onChange({ notify_on_agent_complete: e.target.checked })}
              className="rounded border-neutral-300"
            />
            <span className="text-sm text-neutral-900">
              Notify when agent completes
            </span>
          </label>
        </div>
      </div>

      {/* Debug Options */}
      <div className="border-t border-neutral-200 pt-6">
        <Label className="text-base font-semibold">Debug Options</Label>
        <p className="text-sm text-neutral-600 mb-3">
          For troubleshooting and transparency
        </p>
        <div className="space-y-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.show_debug_info ?? false}
              onChange={(e) => onChange({ show_debug_info: e.target.checked })}
              className="rounded border-neutral-300"
            />
            <span className="text-sm text-neutral-900">
              Show event IDs and correlation IDs
            </span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.show_ai_prompts ?? false}
              onChange={(e) => onChange({ show_ai_prompts: e.target.checked })}
              className="rounded border-neutral-300"
            />
            <span className="text-sm text-neutral-900">
              Show AI prompts (transparency mode)
            </span>
          </label>
        </div>
      </div>
    </div>
  );
}
