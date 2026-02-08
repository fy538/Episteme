/**
 * AI & Behavior Tab — Model selection, structure discovery, agent behavior
 *
 * Uses SettingsCard for model selection, SettingsRow + Switch for toggles,
 * and segmented buttons for detection frequency.
 */

'use client';

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';
import { SettingsGroup, SettingsRow, SettingsCard, SettingsCardGrid } from '../SettingsSection';
import type { UserPreferences } from '@/lib/api/preferences';

interface AITabProps {
  preferences: Partial<UserPreferences>;
  onChange: (updates: Partial<UserPreferences>) => void;
}

const AVAILABLE_MODELS = [
  {
    id: 'anthropic:claude-haiku-4-5',
    name: 'Claude 4.5 Haiku',
    provider: 'anthropic',
    description: 'Fastest, best for real-time chat',
    speed: 'fast',
    cost: 'low',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  {
    id: 'anthropic:claude-sonnet-4-5',
    name: 'Claude 4.5 Sonnet',
    provider: 'anthropic',
    description: 'Best for complex tasks and agents',
    speed: 'medium',
    cost: 'medium',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
  {
    id: 'anthropic:claude-opus-4-5',
    name: 'Claude 4.5 Opus',
    provider: 'anthropic',
    description: 'Maximum intelligence',
    speed: 'medium',
    cost: 'high',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
      </svg>
    ),
  },
  {
    id: 'openai:gpt-4o-mini',
    name: 'GPT-4o Mini',
    provider: 'openai',
    description: 'Fast and affordable',
    speed: 'fast',
    cost: 'low',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  {
    id: 'openai:gpt-4o',
    name: 'GPT-4o',
    provider: 'openai',
    description: 'Most capable OpenAI model',
    speed: 'medium',
    cost: 'high',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
];

const FREQUENCY_OPTIONS = [
  { value: 5, label: 'Low' },
  { value: 3, label: 'Medium' },
  { value: 1, label: 'High' },
];

export function AITab({ preferences, onChange }: AITabProps) {
  return (
    <div className="space-y-8">
      {/* Chat Model */}
      <SettingsGroup title="Chat Model" description="Choose the AI model for conversations">
        <div className="space-y-2">
          {AVAILABLE_MODELS.map((model) => (
            <SettingsCard
              key={model.id}
              active={preferences.chat_model === model.id}
              onClick={() => onChange({ chat_model: model.id })}
              icon={model.icon}
              title={model.name}
              description={model.description}
              meta={
                <Badge variant={model.provider === 'anthropic' ? 'default' : 'success'} className="text-[10px]">
                  {model.provider}
                </Badge>
              }
            >
              <div className="flex gap-3 text-[10px] text-neutral-500 dark:text-neutral-400 mt-1 uppercase tracking-wider">
                <span>Speed: {model.speed}</span>
                <span>Cost: {model.cost}</span>
              </div>
            </SettingsCard>
          ))}
        </div>
      </SettingsGroup>

      {/* Structure Discovery */}
      <SettingsGroup title="Structure Discovery" description="Control how the system detects and suggests creating cases and inquiries" divider>
        <SettingsRow
          label="Auto-detect decision points"
          description="AI suggests creating structure when it detects decision-making conversations"
        >
          <Switch
            checked={preferences.structure_auto_detect ?? true}
            onCheckedChange={(checked) => onChange({ structure_auto_detect: checked })}
          />
        </SettingsRow>

        <SettingsRow
          label="Auto-create inquiries"
          description="Create inquiries from detected questions"
        >
          <Switch
            checked={preferences.auto_create_inquiries ?? true}
            onCheckedChange={(checked) => onChange({ auto_create_inquiries: checked })}
          />
        </SettingsRow>

        <SettingsRow
          label="Auto-detect assumptions"
          description="Flag assumptions in conversations"
        >
          <Switch
            checked={preferences.auto_detect_assumptions ?? true}
            onCheckedChange={(checked) => onChange({ auto_detect_assumptions: checked })}
          />
        </SettingsRow>

        <SettingsRow
          label="Auto-generate titles"
          description="Generate titles for cases and inquiries"
        >
          <Switch
            checked={preferences.auto_generate_titles ?? true}
            onCheckedChange={(checked) => onChange({ auto_generate_titles: checked })}
          />
        </SettingsRow>
      </SettingsGroup>

      {/* Signal Highlighting */}
      <SettingsGroup title="Signal Highlighting" description="Highlight detected signals directly in chat messages" divider>
        <SettingsRow label="Assumptions" description="Highlight assumption signals">
          <Switch
            checked={preferences.highlight_assumptions ?? true}
            onCheckedChange={(checked) => onChange({ highlight_assumptions: checked })}
          />
        </SettingsRow>
        <SettingsRow label="Questions" description="Highlight question signals">
          <Switch
            checked={preferences.highlight_questions ?? true}
            onCheckedChange={(checked) => onChange({ highlight_questions: checked })}
          />
        </SettingsRow>
        <SettingsRow label="Evidence" description="Highlight evidence signals">
          <Switch
            checked={preferences.highlight_evidence ?? true}
            onCheckedChange={(checked) => onChange({ highlight_evidence: checked })}
          />
        </SettingsRow>
      </SettingsGroup>

      {/* Agent Behavior */}
      <SettingsGroup title="Agent Behavior" description="Control how AI agents are suggested and triggered" divider>
        {/* Detection Frequency - segmented control */}
        <SettingsRow
          label="Detection frequency"
          description="How often to check for agent needs"
        >
          <div className="flex rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
            {FREQUENCY_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => onChange({ agent_check_interval: option.value })}
                className={cn(
                  'px-3 py-1.5 text-xs font-medium transition-colors',
                  'first:border-r last:border-l border-neutral-200 dark:border-neutral-700',
                  preferences.agent_check_interval === option.value
                    ? 'bg-accent-600 text-white'
                    : 'bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700'
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </SettingsRow>

        {/* Min Confidence */}
        <SettingsRow
          label="Minimum confidence"
          description="Only suggest agents above this threshold"
        >
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min="0"
              max="1"
              step="0.05"
              value={preferences.agent_min_confidence || 0.75}
              onChange={(e) => onChange({ agent_min_confidence: parseFloat(e.target.value) })}
              className="w-20"
            />
            <span className="text-xs text-neutral-500 dark:text-neutral-400">
              ({((preferences.agent_min_confidence || 0.75) * 100).toFixed(0)}%)
            </span>
          </div>
        </SettingsRow>

        {/* Auto-run */}
        <div className="mx-4 -mx-4 px-4 py-3 rounded-lg bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-warning-900 dark:text-warning-200">
                Auto-run agents
              </p>
              <p className="text-xs text-warning-700 dark:text-warning-400 mt-0.5">
                Experimental: Agents run automatically when confidence {'>'} 0.95
              </p>
            </div>
            <Switch
              checked={preferences.agent_auto_run ?? false}
              onCheckedChange={(checked) => onChange({ agent_auto_run: checked })}
            />
          </div>
        </div>
      </SettingsGroup>
    </div>
  );
}
