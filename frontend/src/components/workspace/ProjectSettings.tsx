/**
 * Project Settings Modal
 * Configure project preferences and settings
 */

'use client';

import { useState } from 'react';
import { Dialog } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import type { Project } from '@/lib/types/project';

interface ProjectSettingsProps {
  project: Project;
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: Partial<Project>) => void;
}

export function ProjectSettings({
  project,
  isOpen,
  onClose,
  onSave,
}: ProjectSettingsProps) {
  const [title, setTitle] = useState(project.title);
  const [description, setDescription] = useState(project.description || '');
  const [autoValidate, setAutoValidate] = useState(true);
  const [backgroundResearch, setBackgroundResearch] = useState(true);
  const [gapDetection, setGapDetection] = useState(true);

  const handleSave = () => {
    onSave({
      title,
      description,
    });
    onClose();
  };

  return (
    <Dialog isOpen={isOpen} onClose={onClose}>
      <div className="bg-white dark:bg-primary-900 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-neutral-200 dark:border-neutral-800">
          <h2 className="text-xl font-bold text-primary-900 dark:text-primary-50">
            Project Settings
          </h2>
        </div>

        <div className="p-6 space-y-6">
          {/* General Settings */}
          <div>
            <h3 className="text-lg font-semibold text-primary-900 dark:text-primary-50 mb-4">
              General
            </h3>
            <div className="space-y-4">
              <div>
                <Label htmlFor="project-title">Project Name</Label>
                <Input
                  id="project-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="project-description">Description</Label>
                <Textarea
                  id="project-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="mt-1"
                  placeholder="What is this project about?"
                />
              </div>
            </div>
          </div>

          {/* Intelligence Settings */}
          <div>
            <h3 className="text-lg font-semibold text-primary-900 dark:text-primary-50 mb-4">
              Background Intelligence
            </h3>
            <div className="space-y-3">
              <Switch
                id="auto-validate"
                label="Auto-validate assumptions"
                checked={autoValidate}
                onCheckedChange={setAutoValidate}
              />
              <p className="text-xs text-neutral-600 dark:text-neutral-400 ml-12 -mt-2">
                Automatically research and validate assumptions in the background
              </p>
              
              <Switch
                id="background-research"
                label="Background research"
                checked={backgroundResearch}
                onCheckedChange={setBackgroundResearch}
              />
              <p className="text-xs text-neutral-600 dark:text-neutral-400 ml-12 -mt-2">
                Continuously research open questions and gaps
              </p>
              
              <Switch
                id="gap-detection"
                label="Gap detection"
                checked={gapDetection}
                onCheckedChange={setGapDetection}
              />
              <p className="text-xs text-neutral-600 dark:text-neutral-400 ml-12 -mt-2">
                Analyze case structure and detect weak points
              </p>
            </div>
          </div>

          {/* Danger Zone */}
          <div className="pt-4 border-t border-neutral-200 dark:border-neutral-800">
            <h3 className="text-lg font-semibold text-error-700 dark:text-error-400 mb-4">
              Danger Zone
            </h3>
            <div className="space-y-2">
              <Button variant="outline" className="w-full text-warning-700 border-warning-300 hover:bg-warning-50">
                Archive Project
              </Button>
              <Button variant="destructive" className="w-full">
                Delete Project
              </Button>
            </div>
          </div>
        </div>

        <div className="p-6 border-t border-neutral-200 dark:border-neutral-800 flex gap-3 justify-end">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Changes
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
