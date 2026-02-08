/**
 * Advanced Tab — Debug options, skills, and danger zone
 *
 * Uses Accordion for collapsible skills section,
 * SettingsRow + Switch for debug toggles,
 * SettingsDangerZone + DangerAction for destructive actions.
 */

'use client';

import * as React from 'react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Accordion } from '@/components/ui/accordion';
import { SettingsGroup, SettingsRow, SettingsDangerZone, DangerAction } from '../SettingsSection';
import { skillsAPI } from '@/lib/api/skills';
import type { Skill } from '@/lib/types/skill';
import type { UserPreferences } from '@/lib/api/preferences';

interface AdvancedTabProps {
  preferences: Partial<UserPreferences>;
  onChange: (updates: Partial<UserPreferences>) => void;
}

const SCOPE_LABELS: Record<string, string> = {
  personal: 'Personal',
  team: 'Team',
  organization: 'Org',
  public: 'Public',
};

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
  draft: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
  archived: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500',
};

export function AdvancedTab({ preferences, onChange }: AdvancedTabProps) {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [showSkills, setShowSkills] = useState(false);
  const [loadingSkills, setLoadingSkills] = useState(false);

  const loadSkills = async () => {
    if (showSkills) {
      setShowSkills(false);
      return;
    }
    setLoadingSkills(true);
    try {
      const result = await skillsAPI.list();
      setSkills(result);
      setShowSkills(true);
    } catch (error) {
      console.error('Failed to load skills:', error);
    } finally {
      setLoadingSkills(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Skills Section - using Accordion */}
      <SettingsGroup
        title="Skills & Templates"
        description="Configure domain-specific templates for AI agents"
      >
        <Accordion
          items={[
            {
              id: 'skills',
              title: 'View Skills Configuration',
              content: (
                <div className="space-y-3">
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">
                    Skills are powerful but optional. Most users work great with organization defaults.
                  </p>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={loadSkills}
                      disabled={loadingSkills}
                    >
                      {loadingSkills ? 'Loading...' : showSkills ? 'Hide Skills' : 'View My Skills'}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={loadSkills}
                      disabled={loadingSkills}
                    >
                      Browse Templates
                    </Button>
                  </div>

                  {/* Inline skill list */}
                  {showSkills && (
                    <div className="space-y-2 pt-2">
                      {skills.length === 0 ? (
                        <p className="text-xs text-neutral-500 dark:text-neutral-400 italic">
                          No skills found. Skills are auto-seeded for your organization, or you can create custom ones from a case.
                        </p>
                      ) : (
                        skills.map(skill => (
                          <div
                            key={skill.id}
                            className="flex items-start gap-3 p-3 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900/50"
                          >
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200 truncate">
                                  {skill.name}
                                </span>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${STATUS_COLORS[skill.status] ?? STATUS_COLORS.draft}`}>
                                  {skill.status}
                                </span>
                              </div>
                              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                                {skill.description}
                              </p>
                              <div className="flex items-center gap-2 mt-1">
                                <span className="text-[10px] text-neutral-400 uppercase">
                                  {skill.domain}
                                </span>
                                <span className="text-[10px] text-neutral-400">
                                  {SCOPE_LABELS[skill.scope] ?? skill.scope}
                                </span>
                                {skill.applies_to_agents.length > 0 && (
                                  <span className="text-[10px] text-neutral-400">
                                    → {skill.applies_to_agents.join(', ')}
                                  </span>
                                )}
                              </div>
                            </div>
                            <span className="text-[10px] text-neutral-400 shrink-0">
                              v{skill.current_version}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  <div className="flex items-center gap-2 pt-1">
                    <Badge variant="neutral" className="text-xs">Optional</Badge>
                    <span className="text-xs text-neutral-500 dark:text-neutral-400">
                      Skills auto-inject domain knowledge into agents when activated for a case.
                    </span>
                  </div>
                </div>
              ),
            },
          ]}
          className="border border-neutral-200 dark:border-neutral-700 rounded-xl px-4"
        />
      </SettingsGroup>

      {/* Debug Options */}
      <SettingsGroup title="Debug Options" description="For troubleshooting and transparency" divider>
        <SettingsRow
          label="Show event IDs and correlation IDs"
          description="Display technical identifiers for debugging"
        >
          <Switch
            checked={preferences.show_debug_info ?? false}
            onCheckedChange={(checked) => onChange({ show_debug_info: checked })}
          />
        </SettingsRow>

        <SettingsRow
          label="Show AI prompts (transparency mode)"
          description="See the prompts sent to AI models"
        >
          <Switch
            checked={preferences.show_ai_prompts ?? false}
            onCheckedChange={(checked) => onChange({ show_ai_prompts: checked })}
          />
        </SettingsRow>
      </SettingsGroup>

      {/* Danger Zone */}
      <SettingsDangerZone>
        <DangerAction
          title="Reset all preferences"
          description="Restore all settings to their defaults"
          buttonLabel="Reset"
          variant="warning"
        />
      </SettingsDangerZone>
    </div>
  );
}
