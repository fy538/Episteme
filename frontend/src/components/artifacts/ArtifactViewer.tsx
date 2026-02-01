/**
 * Artifact Viewer Component
 * 
 * Displays artifact with block-based structure, citations, and versioning.
 */

'use client';

import { useState } from 'react';
import { type Artifact, type Block } from '@/lib/api/artifacts';
import { Textarea } from '@/components/ui/textarea';
import ReactMarkdown from 'react-markdown';

interface ArtifactViewerProps {
  artifact: Artifact;
  onEdit?: (blockId: string, content: string) => void;
  isEditing?: boolean;
}

export function ArtifactViewer({ artifact, onEdit, isEditing = false }: ArtifactViewerProps) {
  const [editingBlockId, setEditingBlockId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const handleStartEdit = (block: Block) => {
    setEditingBlockId(block.id);
    setEditContent(block.content);
  };

  const handleSaveEdit = (blockId: string) => {
    if (onEdit) {
      onEdit(blockId, editContent);
    }
    setEditingBlockId(null);
  };

  const handleCancelEdit = () => {
    setEditingBlockId(null);
    setEditContent('');
  };

  const renderBlock = (block: Block, index: number) => {
    const isCurrentlyEditing = editingBlockId === block.id;

    return (
      <div key={block.id} className="mb-4 group">
        {/* Block content */}
        <div className={`relative ${isEditing ? 'hover:bg-gray-50 rounded p-2' : ''}`}>
          {isCurrentlyEditing ? (
            /* Edit mode */
            <div>
              <Textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                aria-label="Edit artifact content"
                className="min-h-[100px] font-mono text-sm"
                autoFocus
              />
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => handleSaveEdit(block.id)}
                  className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                >
                  Save
                </button>
                <button
                  onClick={handleCancelEdit}
                  className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            /* View mode */
            <div className="relative">
              {block.type === 'heading' ? (
                <h2 className={`font-bold ${
                  block.level === 1 ? 'text-2xl' :
                  block.level === 2 ? 'text-xl' :
                  'text-lg'
                } text-gray-900`}>
                  {block.content}
                </h2>
              ) : block.type === 'paragraph' ? (
                <div className="text-gray-800 leading-relaxed">
                  <ReactMarkdown>{block.content}</ReactMarkdown>
                </div>
              ) : block.type === 'quote' ? (
                <blockquote className="border-l-4 border-gray-300 pl-4 italic text-gray-700">
                  {block.content}
                </blockquote>
              ) : (
                <p className="text-gray-800">{block.content}</p>
              )}

              {/* Edit button (if editing enabled) */}
              {isEditing && (
                <button
                  onClick={() => handleStartEdit(block)}
                  className="absolute -right-2 top-0 opacity-0 group-hover:opacity-100 px-2 py-1 bg-white border rounded text-xs text-gray-600 hover:bg-gray-50"
                >
                  Edit
                </button>
              )}

              {/* Citations */}
              {block.cites && block.cites.length > 0 && (
                <div className="mt-2 flex gap-1 flex-wrap">
                  {block.cites.map((citeId) => (
                    <span
                      key={citeId}
                      className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-50 text-blue-700 cursor-pointer hover:bg-blue-100"
                      title={`Citation: ${citeId}`}
                    >
                      📎 Source
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{artifact.title}</h1>
            <div className="flex gap-3 mt-2 text-sm text-gray-600">
              <span className="capitalize">{artifact.type}</span>
              <span>•</span>
              <span>v{artifact.version_count}</span>
              <span>•</span>
              <span>{artifact.input_signal_count} signals</span>
              <span>•</span>
              <span>{artifact.input_evidence_count} evidence</span>
            </div>
          </div>

          {artifact.is_published && (
            <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
              Published
            </span>
          )}
        </div>
      </div>

      {/* Blocks */}
      <div className="prose prose-lg max-w-none">
        {artifact.current_version_blocks.map((block, index) => renderBlock(block, index))}
      </div>

      {/* Footer */}
      <div className="mt-8 pt-6 border-t text-sm text-gray-500">
        <p>Generated by {artifact.generated_by}</p>
        <p className="mt-1">Last updated: {new Date(artifact.updated_at).toLocaleString()}</p>
      </div>
    </div>
  );
}
