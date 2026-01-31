/**
 * Case workspace page - shows document tree and main content area
 */

'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { DocumentTree } from '@/components/workspace/DocumentTree';
import { DocumentUpload } from '@/components/documents/DocumentUpload';
import { Button } from '@/components/ui/button';
import { EvidenceList } from '@/components/evidence/EvidenceList';
import { GenerationPanel } from '@/components/artifacts/GenerationPanel';
import { ArtifactViewer } from '@/components/artifacts/ArtifactViewer';
import { casesAPI } from '@/lib/api/cases';
import { documentsAPI } from '@/lib/api/documents';
import { artifactsAPI } from '@/lib/api/artifacts';
import type { Case, CaseDocument } from '@/lib/types/case';
import type { Artifact } from '@/lib/types/artifact';

export default function CaseWorkspacePage({
  params,
}: {
  params: { caseId: string };
}) {
  const [caseData, setCase] = useState<Case | null>(null);
  const [documents, setDocuments] = useState<CaseDocument[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'evidence' | 'artifacts'>('overview');

  useEffect(() => {
    async function load() {
      try {
        const [c, docs, arts] = await Promise.all([
          casesAPI.getCase(params.caseId),
          documentsAPI.getByCase(params.caseId),
          artifactsAPI.list(params.caseId),
        ]);
        setCase(c);
        setDocuments(docs);
        setArtifacts(arts);
      } catch (error) {
        console.error('Failed to load case:', error);
      } finally {
        setLoading(false);
      }
    }
    load();

    // Refresh periodically
    const interval = setInterval(load, 10000); // Every 10s
    return () => clearInterval(interval);
  }, [params.caseId]);

  if (loading) {
    return <div className="p-8">Loading case...</div>;
  }

  if (!caseData) {
    return <div className="p-8 text-red-600">Case not found</div>;
  }

  const mainBrief = documents.find(d => d.id === caseData.main_brief);

  return (
    <div className="flex h-screen bg-white">
      {/* Left: Document tree */}
      <div className="w-72 border-r border-gray-200 bg-gray-50 overflow-y-auto">
        <div className="p-4 border-b border-gray-200 bg-white">
          <Link href="/chat" className="text-sm text-blue-600 hover:text-blue-700 mb-2 block">
            ← Back to Chat
          </Link>
          <h2 className="text-lg font-semibold text-gray-900">
            {caseData.title}
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            {caseData.status} • {caseData.stakes} stakes
          </p>
        </div>

        <div className="p-4">
          <DocumentTree documents={documents} caseId={params.caseId} />
          
          {/* Document Upload */}
          <div className="mt-6 pt-6 border-t">
            <DocumentUpload
              caseId={params.caseId}
              projectId={caseData.project || ''}
              onUploaded={() => {
                // Refresh documents list
                documentsAPI.getByCase(params.caseId).then(setDocuments);
              }}
            />
          </div>
        </div>
      </div>

      {/* Center: Main content area */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Tabs */}
        <div className="border-b border-gray-200 bg-white">
          <div className="flex gap-4 px-6">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-3 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'overview'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('evidence')}
              className={`py-3 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'evidence'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Evidence
            </button>
            <button
              onClick={() => setActiveTab('artifacts')}
              className={`py-3 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'artifacts'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Artifacts {artifacts.length > 0 && `(${artifacts.length})`}
            </button>
          </div>
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === 'overview' && (
            <div className="p-6">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                {caseData.title}
              </h3>
              <p className="text-gray-600 mb-6">
                {caseData.position || 'No position set yet'}
              </p>

              {mainBrief && (
                <div className="mb-6">
                  <Link href={`/cases/${params.caseId}/documents/${mainBrief.id}`}>
                    <Button>
                      Open Case Brief
                    </Button>
                  </Link>
                </div>
              )}

              <div className="max-w-2xl">
                <h4 className="font-semibold text-gray-700 mb-3">
                  Documents in this case:
                </h4>
                <ul className="space-y-2 text-sm text-gray-600">
                  {documents.map(doc => (
                    <li key={doc.id} className="flex items-center gap-2">
                      <span>•</span>
                      <Link 
                        href={`/cases/${params.caseId}/documents/${doc.id}`}
                        className="text-blue-600 hover:text-blue-700"
                      >
                        {doc.title}
                      </Link>
                      <span className="text-xs text-gray-500">
                        ({doc.document_type.replace('_', ' ')})
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="p-6">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">
                Evidence from Documents
              </h3>
              <p className="text-gray-600 mb-6">
                Facts, metrics, and benchmarks extracted from uploaded documents.
              </p>
              <EvidenceList caseId={params.caseId} />
            </div>
          )}

          {activeTab === 'artifacts' && (
            <div className="p-6">
              <h3 className="text-xl font-semibold text-gray-900 mb-4">
                AI-Generated Artifacts
              </h3>
              
              {/* Generation Panel */}
              <div className="mb-8">
                <GenerationPanel 
                  caseId={params.caseId}
                  onGenerated={() => {
                    // Refresh artifacts list
                    artifactsAPI.list(params.caseId).then(setArtifacts);
                  }}
                />
              </div>

              {/* Artifacts List */}
              {artifacts.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <p>No artifacts yet.</p>
                  <p className="text-sm mt-2">Use the generation panel above to create research, critiques, or briefs.</p>
                </div>
              ) : (
                <div className="space-y-8">
                  {artifacts.map(artifact => (
                    <div key={artifact.id} className="border-t pt-8">
                      <ArtifactViewer 
                        artifact={artifact}
                        onEdit={async (blockId, content) => {
                          await artifactsAPI.editBlock(artifact.id, blockId, content);
                          // Refresh
                          const updated = await artifactsAPI.get(artifact.id);
                          setArtifacts(prev => 
                            prev.map(a => a.id === updated.id ? updated : a)
                          );
                        }}
                        isEditing={true}
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
      </div>
    </div>
  );
}
