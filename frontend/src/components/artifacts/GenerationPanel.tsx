/**
 * Generation Panel Component
 * 
 * UI for generating artifacts (research, critique, brief).
 */

'use client';

import { useState } from 'react';
import { artifactsAPI } from '@/lib/api/artifacts';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface GenerationPanelProps {
  caseId: string;
  onGenerated?: (artifactId: string) => void;
}

export function GenerationPanel({ caseId, onGenerated }: GenerationPanelProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationType, setGenerationType] = useState<'research' | 'critique' | 'brief' | null>(null);
  const [topic, setTopic] = useState('');
  const [selectedSignalId, setSelectedSignalId] = useState('');

  const handleGenerateResearch = async () => {
    if (!topic.trim()) return;

    setIsGenerating(true);
    setGenerationType('research');

    try {
      const result = await artifactsAPI.generateResearch(caseId, topic);
      console.log('Research generation started:', result.task_id);
      
      // Poll for completion (simplified)
      setTimeout(() => {
        setIsGenerating(false);
        setGenerationType(null);
        setTopic('');
        onGenerated?.(result.task_id);  // In real implementation, poll for actual artifact_id
      }, 3000);
    } catch (error) {
      console.error('Failed to generate research:', error);
      setIsGenerating(false);
      setGenerationType(null);
    }
  };

  const handleGenerateCritique = async () => {
    if (!selectedSignalId) return;

    setIsGenerating(true);
    setGenerationType('critique');

    try {
      const result = await artifactsAPI.generateCritique(caseId, selectedSignalId);
      console.log('Critique generation started:', result.task_id);
      
      setTimeout(() => {
        setIsGenerating(false);
        setGenerationType(null);
        onGenerated?.(result.task_id);
      }, 3000);
    } catch (error) {
      console.error('Failed to generate critique:', error);
      setIsGenerating(false);
      setGenerationType(null);
    }
  };

  const handleGenerateBrief = async () => {
    setIsGenerating(true);
    setGenerationType('brief');

    try {
      const result = await artifactsAPI.generateBrief(caseId);
      console.log('Brief generation started:', result.task_id);
      
      setTimeout(() => {
        setIsGenerating(false);
        setGenerationType(null);
        onGenerated?.(result.task_id);
      }, 3000);
    } catch (error) {
      console.error('Failed to generate brief:', error);
      setIsGenerating(false);
      setGenerationType(null);
    }
  };

  return (
    <div className="bg-white rounded-lg border p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4">AI Generation</h3>

      {/* Research */}
      <div className="mb-6">
        <h4 className="font-medium mb-2">Research Report</h4>
        <p className="text-sm text-neutral-600 mb-3">
          Generate comprehensive research on a topic (with web search)
        </p>
        <div className="space-y-1 mb-2">
          <Label htmlFor="research-topic">Research Topic</Label>
          <Input
            id="research-topic"
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Research topic..."
            disabled={isGenerating}
          />
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleGenerateResearch}
            disabled={isGenerating || !topic.trim()}
          >
            {isGenerating && generationType === 'research' ? 'Generating...' : 'Research'}
          </Button>
        </div>
      </div>

      {/* Critique */}
      <div className="mb-6">
        <h4 className="font-medium mb-2">Red-Team / Critique</h4>
        <p className="text-sm text-gray-600 mb-3">
          Challenge assumptions and find counterarguments
        </p>
        <button
          onClick={handleGenerateCritique}
          disabled={isGenerating}
          className="px-4 py-2 bg-red-600 text-white rounded text-sm hover:bg-red-700 disabled:opacity-50"
        >
          {isGenerating && generationType === 'critique' ? 'Generating...' : 'Red-Team Position'}
        </button>
      </div>

      {/* Brief */}
      <div>
        <h4 className="font-medium mb-2">Decision Brief</h4>
        <p className="text-sm text-gray-600 mb-3">
          Synthesize position with evidence into stakeholder brief
        </p>
        <button
          onClick={handleGenerateBrief}
          disabled={isGenerating}
          className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
        >
          {isGenerating && generationType === 'brief' ? 'Generating...' : 'Generate Brief'}
        </button>
      </div>

      {/* Progress indicator */}
      {isGenerating && (
        <div className="mt-4 p-3 bg-blue-50 rounded">
          <p className="text-sm text-blue-800">
            Generating {generationType}... This may take 10-30 seconds.
          </p>
          <div className="mt-2 w-full bg-blue-200 rounded-full h-2">
            <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
          </div>
        </div>
      )}
    </div>
  );
}
