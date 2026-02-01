/**
 * AI & Agents Tab - Model selection and agent behavior
 */

'use client';

import * as React from 'react';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
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
    description: 'Fastest, best for real-time chat ($1/$5 per MTok)',
    speed: 'fast',
    cost: 'low',
  },
  {
    id: 'anthropic:claude-sonnet-4-5',
    name: 'Claude 4.5 Sonnet',
    provider: 'anthropic',
    description: 'Best for complex tasks, coding, agents ($3/$15 per MTok)',
    speed: 'medium',
    cost: 'medium',
  },
  {
    id: 'anthropic:claude-opus-4-5',
    name: 'Claude 4.5 Opus',
    provider: 'anthropic',
    description: 'Maximum intelligence ($5/$25 per MTok)',
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
  const [showAdvanced, setShowAdvanced] = React.useState(false);
  const selectedModelConfig = AVAILABLE_MODELS.find(m => m.id === preferences.chat_model);

  return (
    <div className="space-y-6">
      {/* Chat Model */}
      <div>
        <Label className="text-base font-semibold">Chat Model</Label>
        <p className="text-sm text-neutral-600 mb-3">
          Choose the AI model for conversations
        </p>
        
        <div className="space-y-2">
          {AVAILABLE_MODELS.map((model) => (
            <label
              key={model.id}
              className={`block p-4 border-2 rounded-lg cursor-pointer transition-all ${
                preferences.chat_model === model.id
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-neutral-200 hover:border-neutral-300'
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
                    <span className="font-medium text-neutral-900">{model.name}</span>
                    <Badge variant={model.provider === 'anthropic' ? 'default' : 'success'} className="text-xs">
                      {model.provider}
                    </Badge>
                  </div>
                  <p className="text-sm text-neutral-600 mb-2">{model.description}</p>
                  <div className="flex gap-4 text-xs text-neutral-500">
                    <span>Speed: {model.speed}</span>
                    <span>Cost: {model.cost}</span>
                  </div>
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Agent Behavior */}
      <div>
        <Label className="text-base font-semibold">Agent Behavior</Label>
        <p className="text-sm text-neutral-600 mb-3">
          Control how and when AI agents are suggested
        </p>
        
        <div className="space-y-4">
          {/* Inflection Sensitivity */}
          <div>
            <Label htmlFor="agent-interval">Detection Sensitivity</Label>
            <p className="text-xs text-neutral-500 mb-2">
              How often to check for agent needs
            </p>
            <div className="space-y-2">
              {[
                { value: 5, label: 'Low (every 5 turns)', description: 'Fewer suggestions' },
                { value: 3, label: 'Medium (every 3 turns)', description: 'Balanced' },
                { value: 1, label: 'High (every turn)', description: 'More suggestions' },
              ].map((option) => (
                <label
                  key={option.value}
                  className={`block p-3 border rounded-md cursor-pointer ${
                    preferences.agent_check_interval === option.value
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-neutral-200 hover:bg-neutral-50'
                  }`}
                >
                  <div className="flex items-center">
                    <input
                      type="radio"
                      name="agent_interval"
                      value={option.value}
                      checked={preferences.agent_check_interval === option.value}
                      onChange={(e) => onChange({ agent_check_interval: parseInt(e.target.value) })}
                      className="mr-2"
                    />
                    <div>
                      <p className="text-sm font-medium text-neutral-900">{option.label}</p>
                      <p className="text-xs text-neutral-600">{option.description}</p>
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Min Confidence */}
          <div>
            <Label htmlFor="min-confidence">Minimum Confidence</Label>
            <p className="text-xs text-neutral-500 mb-2">
              Only suggest agents when confidence is above this threshold
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
                className="w-24"
              />
              <span className="text-sm text-neutral-600">
                ({((preferences.agent_min_confidence || 0.75) * 100).toFixed(0)}%)
              </span>
            </div>
          </div>

          {/* Auto-run (Advanced) */}
          <div className="p-3 bg-warning-50 border border-warning-200 rounded-md">
            <label className="flex items-start gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={preferences.agent_auto_run ?? false}
                onChange={(e) => onChange({ agent_auto_run: e.target.checked })}
                className="rounded border-warning-300 mt-0.5"
              />
              <div>
                <span className="text-sm font-medium text-warning-900">
                  Auto-run agents (when confidence {'>'} 0.95)
                </span>
                <p className="text-xs text-warning-700 mt-1">
                  ⚠️ Experimental: Agents will run automatically without confirmation
                </p>
              </div>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
