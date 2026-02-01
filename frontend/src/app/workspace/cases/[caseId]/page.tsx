/**
 * Case workspace page - unified decision workspace
 * Layout: Case Nav (left) | Center View (brief/inquiry) | Chat Panel (right)
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { WorkspaceLayout } from '@/components/workspace/WorkspaceLayout';
import { ModeHeader } from '@/components/workspace/ModeHeader';
import { CaseNavigation } from '@/components/workspace/CaseNavigation';
import { CaseBriefView } from '@/components/workspace/CaseBriefView';
import { InquiryWorkspaceView } from '@/components/workspace/InquiryWorkspaceView';
import { ChatPanel } from '@/components/workspace/ChatPanel';
import { SettingsModal } from '@/components/settings/SettingsModal';
import { CommandPalette, useCommandPalette, type Command } from '@/components/ui/CommandPalette';
import { DiffViewer } from '@/components/ui/DiffViewer';
import { casesAPI } from '@/lib/api/cases';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { documentsAPI } from '@/lib/api/documents';
import { chatAPI } from '@/lib/api/chat';
import type { Case, CaseDocument, Inquiry } from '@/lib/types/case';
import type { Project } from '@/lib/types/project';

type ViewMode = 'brief' | 'inquiry' | 'document';

export default function CaseWorkspacePage({
  params,
}: {
  params: { caseId: string };
}) {
  const router = useRouter();
  const [caseData, setCase] = useState<Case | null>(null);
  const [brief, setBrief] = useState<CaseDocument | null>(null);
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [allCases, setAllCases] = useState<Case[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [threadId, setThreadId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  
  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('brief');
  const [activeInquiryId, setActiveInquiryId] = useState<string | null>(null);
  
  // Command palette
  const { isOpen: commandPaletteOpen, setIsOpen: setCommandPaletteOpen } = useCommandPalette();
  
  // Integration preview state
  const [integrationPreview, setIntegrationPreview] = useState<any>(null);

  useEffect(() => {
    loadWorkspace();
  }, [params.caseId]);

  async function loadWorkspace() {
    setLoading(true);
    try {
      // Load case data
      const [caseResp, inqs, docs, allCasesResp] = await Promise.all([
        casesAPI.getCase(params.caseId),
        inquiriesAPI.getByCase(params.caseId),
        documentsAPI.getByCase(params.caseId),
        casesAPI.listCases(),
      ]);

      setCase(caseResp);
      setInquiries(inqs);
      setAllCases(allCasesResp);

      // Find main brief
      const mainBrief = docs.find(d => d.id === caseResp.main_brief);
      setBrief(mainBrief || null);

      // Get or create thread for this case
      if (caseResp.linked_thread) {
        setThreadId(caseResp.linked_thread);
      } else {
        // Create a new thread for this case
        const thread = await chatAPI.createThread(`Chat: ${caseResp.title}`);
        setThreadId(thread.id);
        
        // Link thread to case
        await chatAPI.updateThread(thread.id, { primary_case: caseResp.id });
        
        // Update case with linked thread
        await casesAPI.updateCase(caseResp.id, { linked_thread: thread.id });
      }

      // Load projects (for navigation)
      try {
        const projectsResp = await projectsAPI.listProjects();
        setProjects(projectsResp);
      } catch (error) {
        console.error('Failed to load projects:', error);
        setProjects([]);
      }
    } catch (error) {
      console.error('Failed to load workspace:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateCase() {
    try {
      const newCase = await casesAPI.createCase('New Case');
      router.push(`/workspace/cases/${newCase.case.id}`);
    } catch (error) {
      console.error('Failed to create case:', error);
    }
  }

  async function handleStartInquiry() {
    if (!caseData) return;
    
    try {
      const inquiry = await inquiriesAPI.create({
        case: caseData.id,
        title: 'New Inquiry',
        status: 'open',
      });
      
      setActiveInquiryId(inquiry.id);
      setViewMode('inquiry');
      await loadWorkspace();
    } catch (error) {
      console.error('Failed to create inquiry:', error);
    }
  }

  function handleOpenInquiry(inquiryId: string) {
    setActiveInquiryId(inquiryId);
    setViewMode('inquiry');
  }

  function handleBackToBrief() {
    setViewMode('brief');
    setActiveInquiryId(null);
  }

  if (loading || !caseData) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-500">Loading workspace...</p>
      </div>
    );
  }

  // Determine mode and breadcrumbs
  const activeInquiry = activeInquiryId 
    ? inquiries.find(i => i.id === activeInquiryId)
    : null;

  const mode = viewMode === 'inquiry' ? 'researching' : 'editing_brief';
  const modeLabel = activeInquiry 
    ? `Researching: ${activeInquiry.title}`
    : 'Editing Brief';

  const breadcrumbs = [
    { label: 'Workspace', href: '/workspace' },
    { label: caseData.title },
  ];

  if (activeInquiry) {
    breadcrumbs.push({ label: activeInquiry.title });
  }

  // Define commands for palette
  const commands: Command[] = [
    // Navigation
    {
      id: 'back-to-brief',
      label: 'Back to case brief',
      category: 'navigation',
      keywords: ['back', 'brief', 'case'],
      action: () => handleBackToBrief(),
      shortcut: 'Esc',
    },
    // Actions
    {
      id: 'create-inquiry',
      label: 'Start new inquiry',
      category: 'actions',
      keywords: ['create', 'inquiry', 'question', 'new'],
      action: () => handleStartInquiry(),
      shortcut: 'Cmd+I',
    },
    {
      id: 'create-case',
      label: 'Create new case',
      category: 'actions',
      keywords: ['create', 'case', 'new'],
      action: () => handleCreateCase(),
      shortcut: 'Cmd+N',
    },
    {
      id: 'settings',
      label: 'Open settings',
      category: 'actions',
      keywords: ['settings', 'preferences', 'config'],
      action: () => setSettingsOpen(true),
    },
    // AI Actions
    {
      id: 'detect-assumptions',
      label: 'Detect assumptions in brief',
      category: 'ai',
      keywords: ['assumptions', 'detect', 'analyze', 'ai'],
      action: async () => {
        if (brief) {
          try {
            const detected = await documentsAPI.detectAssumptions(brief.id);
            // Assumptions will be displayed in CaseBriefView
            loadWorkspace();
          } catch (error) {
            console.error('Failed to detect assumptions:', error);
          }
        }
      },
    },
    {
      id: 'generate-research',
      label: 'Generate research',
      category: 'ai',
      keywords: ['research', 'generate', 'ai'],
      action: () => {
        // TODO: Implement research generation
        alert('Research generation coming soon!');
      },
    },
  ];

  return (
    <>
      <WorkspaceLayout
        header={
          <ModeHeader
            breadcrumbs={breadcrumbs}
            mode={mode}
            modeLabel={modeLabel}
          />
        }
        leftPanel={
          <CaseNavigation
            projects={projects}
            cases={allCases}
            activeCaseId={params.caseId}
            onCreateCase={handleCreateCase}
            onOpenSettings={() => setSettingsOpen(true)}
          />
        }
        centerView={
          viewMode === 'brief' ? (
            <CaseBriefView
              caseData={caseData}
              brief={brief}
              inquiries={inquiries}
              onStartInquiry={handleStartInquiry}
              onOpenInquiry={handleOpenInquiry}
              onRefresh={loadWorkspace}
            />
          ) : activeInquiry ? (
            <InquiryWorkspaceView
              caseId={params.caseId}
              inquiry={activeInquiry}
              onBack={handleBackToBrief}
              onRefresh={loadWorkspace}
              briefId={brief?.id}
              briefContent={brief?.content_markdown || ''}
            />
          ) : null
        }
        rightPanel={
          <ChatPanel
            threadId={threadId}
            contextLabel={`Chat about: ${caseData.title}`}
            briefId={brief?.id}
            onIntegrationPreview={setIntegrationPreview}
          />
        }
      />

      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
      
      <CommandPalette
        commands={commands}
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
      />
      
      {/* Integration Preview Modal */}
      {integrationPreview && brief && (
        <DiffViewer
          original={brief.content_markdown || ''}
          proposed={integrationPreview.updated_content}
          title="Add to Brief"
          onAccept={async (content) => {
            await documentsAPI.update(brief.id, { content_markdown: content });
            setIntegrationPreview(null);
            loadWorkspace();
          }}
          onReject={() => setIntegrationPreview(null)}
          onClose={() => setIntegrationPreview(null)}
        />
      )}
    </>
  );
}
