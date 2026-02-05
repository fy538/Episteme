/**
 * AI & Behavior Tab - Model selection, agent behavior, and structure discovery
 */

'use client';

import * as React from 'react';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
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
  },
  {
    id: 'anthropic:claude-sonnet-4-5',
    name: 'Claude 4.5 Sonnet',
    provider: 'anthropic',
    description: 'Best for complex tasks and agents',
    speed: 'medium',
    cost: 'medium',
  },
  {
    id: 'anthropic:claude-opus-4-5',
    name: 'Claude 4.5 Opus',
    provider: 'anthropic',
    description: 'Maximum intelligence',
    speed: 'medium',
    cost: 'high',
  },
  {
    id: 'openai:gpt-4o-mini',
    name: 'GPT-4o Mini',
    provider: 'openai',
    description: 'Fast and affordable',
    speed: 'fast',
    cost: 'low',
  },
  {
    id: 'openai:gpt-4o',
    name: 'GPT-4o',
    provider: 'openai',
    description: 'Most capable OpenAI model',
    speed: 'medium',
    cost: 'high',
  },
];

export function AITab({ preferences, onChange }: AITabProps) {
  return (
    <div className="space-y-8">
      {/* Chat Model */}
      <section>
        <Label className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Chat Model</Label>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
          Choose the AI model for conversations
        </p>

        <div className="space-y-2">
          {AVAILABLE_MODELS.map((model) => (
            <label
              key={model.id}
              className={`block p-4 border-2 rounded-lg cursor-pointer transition-all ${
                preferences.chat_model === model.id
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                  : 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'
              }`}
            >
              <div className="flex items-start">
                <input
                  type="radio"
                  name="chat_model"
                  value={model.id}
                  checked={preferences.chat_model === model.id}
                  onChange={(e) => onChange({ chat_model: e.target.value })}
                  className="mt-1 mr-3"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-neutral-900 dark:text-neutral-100">{model.name}</span>
                    <Badge variant={model.provider === 'anthropic' ? 'default' : 'success'} className="text-xs">
                      {model.provider}
                    </Badge>
                  </div>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-2">{model.description}</p>
                  <div className="flex gap-4 text-xs text-neutral-500 dark:text-neutral-500">
                    <span>Speed: {model.speed}</span>
                    <span>Cost: {model.cost}</span>
                  </div>
                </div>
              </div>
            </label>
          ))}
        </div>
      </section>

      {/* Structure Discovery - consolidated from WorkspaceTab */}
      <section className="border-t border-neutral-200 dark:border-neutral-700 pt-6">
        <Label className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Structure Discovery</Label>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
          Control how the system detects and suggests creating cases and inquiries
        </p>

        <div className="space-y-4">
          {/* Auto-detect toggle */}
          <div className="p-3 border border-neutral-200 dark:border-neutral-700 rounded-lg">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={preferences.structure_auto_detect ?? true}
                onChange={(e) => onChange({ structure_auto_detect: e.target.checked })}
                className="mt-0.5 w-4 h-4 rounded border-neutral-300 dark:border-neutral-600 text-primary-600"
              />
              <div>
                <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  Auto-detect decision points
                </span>
                <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
                  AI will suggest creating structure when it detects decision-making conversations
                </p>
              </div>
            </label>
          </div>

          {/* Auto-create items */}
          <div className="space-y-3 pl-1">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={preferences.auto_create_inquiries ?? true}
                onChange={(e) => onChange({ auto_create_inquiries: e.target.checked })}
                className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600 text-primary-600"
              />
              <span className="text-sm text-neutral-900 dark:text-neutral-100">
                Auto-create inquiries from questions
              </span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={preferences.auto_detect_assumptions ?? true}
                onChange={(e) => onChange({ auto_detect_assumptions: e.target.checked })}
                className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600 text-primary-600"
              />
              <span className="text-sm text-neutral-900 dark:text-neutral-100">
                Auto-detect assumptions
              </span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={preferences.auto_generate_titles ?? true}
                onChange={(e) => onChange({ auto_generate_titles: e.target.checked })}
                className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600 text-primary-600"
              />
              <span className="text-sm text-neutral-900 dark:text-neutral-100">
                Auto-generate titles for cases and inquiries
              </span>
            </label>
          </div>

          {/* Signal Highlighting */}
          <div className="pt-2">
            <Label className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Inline Signal Highlighting</Label>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-3">
              Highlight detected signals directly in chat messages
            </p>
            <div className="flex flex-wrap gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={preferences.highlight_assumptions ?? true}
                  onChange={(e) => onChange({ highlight_assumptions: e.target.checked })}
                  className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600"
                />
                <span className="text-sm text-neutral-700 dark:text-neutral-300">Assumptions</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={preferences.highlight_questions ?? true}
                  onChange={(e) => onChange({ highlight_questions: e.target.checked })}
                  className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600"
                />
                <span className="text-sm text-neutral-700 dark:text-neutral-300">Questions</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={preferences.highlight_evidence ?? true}
                  onChange={(e) => onChange({ highlight_evidence: e.target.checked })}
                  className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600"
                />
                <span className="text-sm text-neutral-700 dark:text-neutral-300">Evidence</span>
              </label>
            </div>
          </div>
        </div>
      </section>

      {/* Agent Behavior */}
      <section className="border-t border-neutral-200 dark:border-neutral-700 pt-6">
        <Label className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Agent Behavior</Label>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
          Control how AI agents are suggested and triggered
        </p>

        <div className="space-y-4">
          {/* Detection Interval */}
          <div>
            <Label className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Detection Frequency</Label>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-2">
              How often to check for agent needs
            </p>
            <div className="grid grid-cols-3 gap-2">
              {[
                { value: 5, label: 'Low' },
                { value: 3, label: 'Medium' },
                { value: 1, label: 'High' },
              ].map((option) => (
                <label
                  key={option.value}
                  className={`block p-2 text-center border rounded-md cursor-pointer transition-all text-sm ${
                    preferences.agent_check_interval === option.value
                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                      : 'border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800'
                  }`}
                >
                  <input
                    type="radio"
                    name="agent_interval"
                    value={option.value}
                    checked={preferences.agent_check_interval === option.value}
                    onChange={(e) => onChange({ agent_check_interval: parseInt(e.target.value) })}
                    className="sr-only"
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </div>

          {/* Min Confidence */}
          <div>
            <Label htmlFor="min-confidence" className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Minimum Confidence</Label>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-2">
              Only suggest agents above this threshold
            </p>
            <div className="flex items-center gap-2">
              <Input
                id="min-confidence"
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={preferences.agent_min_confidence || 0.75}
                onChange={(e) => onChange({ agent_min_confidence: parseFloat(e.target.value) })}
                className="w-20"
              />
              <span className="text-sm text-neutral-600 dark:text-neutral-400">
                ({((preferences.agent_min_confidence || 0.75) * 100).toFixed(0)}%)
              </span>
            </div>
          </div>

          {/* Auto-run */}
          <div className="p-3 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-md">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={preferences.agent_auto_run ?? false}
                onChange={(e) => onChange({ agent_auto_run: e.target.checked })}
                className="mt-0.5 w-4 h-4 rounded border-warning-300 dark:border-warning-700"
              />
              <div>
                <span className="text-sm font-medium text-warning-900 dark:text-warning-200">
                  Auto-run agents (when confidence {'>'} 0.95)
                </span>
                <p className="text-xs text-warning-700 dark:text-warning-400 mt-1">
                  Experimental: Agents will run automatically without confirmation
                </p>
              </div>
            </label>
          </div>
        </div>
      </section>
    </div>
  );
}
