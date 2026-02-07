/**
 * Case workspace page - unified decision workspace
 * Layout: Case Nav (left) | Center View (brief/inquiry) | Chat Panel (right)
 *
 * State management extracted to useCaseWorkspace hook.
 */

'use client';

import { WorkspaceLayout } from '@/components/workspace/WorkspaceLayout';
import { ModeHeader } from '@/components/workspace/ModeHeader';
import { CaseNavigation } from '@/components/workspace/CaseNavigation';
import { CaseBriefView } from '@/components/workspace/CaseBriefView';
import { InquiryWorkspaceView } from '@/components/workspace/InquiryWorkspaceView';
import { InquiryDashboard } from '@/components/inquiries/InquiryDashboard';
import { ChatPanel } from '@/components/workspace/ChatPanel';
import { CompanionPanel } from '@/components/companion';
import { SettingsModal } from '@/components/settings/SettingsModal';
import { CommandPalette, useCommandPalette, type Command } from '@/components/ui/CommandPalette';
import { DiffViewer } from '@/components/ui/DiffViewer';
import { Button } from '@/components/ui/button';
import { ReadinessChecklist } from '@/components/readiness';
import { documentsAPI } from '@/lib/api/documents';
import { useCaseWorkspace } from '@/hooks/useCaseWorkspace';

export default function CaseWorkspacePage({
  params,
}: {
  params: { caseId: string };
}) {
  const ws = useCaseWorkspace({ caseId: params.caseId });
  const { isOpen: commandPaletteOpen, setIsOpen: setCommandPaletteOpen } = useCommandPalette();

  if (ws.loading || !ws.caseData) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-neutral-500">Loading workspace...</p>
      </div>
    );
  }

  // Determine mode and breadcrumbs
  const mode = ws.viewMode === 'inquiry' ? 'researching' : 'editing_brief';
  const modeLabel = ws.activeInquiry
    ? `Researching: ${ws.activeInquiry.title}`
    : 'Editing Brief';

  const breadcrumbs = [
    { label: 'Home', href: '/' },
    { label: ws.caseData.title },
    ...(ws.activeInquiry ? [{ label: ws.activeInquiry.title }] : []),
  ];

  // Define commands for palette
  const commands: Command[] = [
    {
      id: 'back-to-brief',
      label: 'Back to case brief',
      category: 'navigation',
      keywords: ['back', 'brief', 'case'],
      action: () => ws.handleBackToBrief(),
      shortcut: 'Esc',
    },
    {
      id: 'view-readiness',
      label: 'View decision readiness',
      category: 'navigation',
      keywords: ['readiness', 'checklist', 'ready', 'complete'],
      action: () => ws.setViewMode('readiness'),
      shortcut: 'Cmd+R',
    },
    {
      id: 'create-inquiry',
      label: 'Start new inquiry',
      category: 'actions',
      keywords: ['create', 'inquiry', 'question', 'new'],
      action: () => ws.handleStartInquiry(),
      shortcut: 'Cmd+I',
    },
    {
      id: 'create-case',
      label: 'Create new case',
      category: 'actions',
      keywords: ['create', 'case', 'new'],
      action: () => ws.handleCreateCase(),
      shortcut: 'Cmd+N',
    },
    {
      id: 'settings',
      label: 'Open settings',
      category: 'actions',
      keywords: ['settings', 'preferences', 'config'],
      action: () => ws.setSettingsOpen(true),
    },
    {
      id: 'detect-assumptions',
      label: 'Detect assumptions in brief',
      category: 'ai',
      keywords: ['assumptions', 'detect', 'analyze', 'ai'],
      action: async () => {
        if (ws.brief) {
          try {
            await documentsAPI.detectAssumptions(ws.brief.id);
            ws.loadWorkspace();
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
        console.log('Research generation not yet implemented');
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
            projects={ws.projects}
            cases={ws.allCases}
            activeCaseId={params.caseId}
            onCreateCase={ws.handleCreateCase}
            onOpenSettings={() => ws.setSettingsOpen(true)}
          />
        }
        centerView={
          ws.viewMode === 'brief' ? (
            <div key="brief" className="animate-fade-in">
              <CaseBriefView
                caseData={ws.caseData}
                brief={ws.brief}
                inquiries={ws.inquiries}
                onStartInquiry={ws.handleStartInquiry}
                onOpenInquiry={ws.handleOpenInquiry}
                onViewDashboard={() => ws.setViewMode('inquiry-dashboard')}
                onRefresh={ws.loadWorkspace}
              />
            </div>
          ) : ws.viewMode === 'readiness' ? (
            <div key="readiness" className="max-w-4xl mx-auto p-8 animate-fade-in">
              <div className="mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h1 className="text-2xl tracking-tight font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                      Decision Readiness
                    </h1>
                    <p className="text-neutral-600 dark:text-neutral-400">
                      Complete these items before deciding with confidence
                    </p>
                  </div>
                  <Button variant="outline" onClick={ws.handleBackToBrief}>
                    Back to Brief
                  </Button>
                </div>
              </div>

              <ReadinessChecklist
                caseId={params.caseId}
                items={ws.checklistItems}
                progress={ws.checklistProgress}
                onRefresh={ws.loadChecklist}
              />
            </div>
          ) : ws.viewMode === 'inquiry-dashboard' ? (
            <div key="inquiry-dashboard" className="max-w-4xl mx-auto p-8 animate-fade-in">
              <div className="mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h1 className="text-2xl tracking-tight font-semibold text-neutral-900 mb-2">
                      Investigation Dashboard
                    </h1>
                    <p className="text-neutral-600">
                      Overview of all inquiries and investigation progress
                    </p>
                  </div>
                  <Button variant="outline" onClick={ws.handleBackToBrief}>
                    Back to Brief
                  </Button>
                </div>
              </div>

              <InquiryDashboard
                caseId={params.caseId}
                onStartInquiry={(inquiryId) => {
                  ws.handleOpenInquiry(inquiryId);
                }}
                onViewInquiry={(inquiryId) => {
                  ws.handleOpenInquiry(inquiryId);
                }}
              />
            </div>
          ) : ws.activeInquiry ? (
            <div key={`inquiry-${ws.activeInquiry.id}`} className="animate-fade-in">
              <InquiryWorkspaceView
                caseId={params.caseId}
                inquiry={ws.activeInquiry}
                onBack={ws.handleBackToBrief}
                onRefresh={ws.loadWorkspace}
                briefId={ws.brief?.id}
                briefContent={ws.brief?.content_markdown || ''}
              />
            </div>
          ) : null
        }
        rightPanel={
          <div className="flex flex-col h-full">
            {/* Companion panel — stacked above chat */}
            {ws.companionPosition === 'sidebar' && (
              <CompanionPanel
                thinking={ws.companionState.thinking}
                mode={ws.chatMode.mode.mode}
                position="sidebar"
                actionHints={ws.actionHints}
                signals={ws.signals}
                status={ws.companionState.status}
                sessionReceipts={ws.companionState.sessionReceipts}
                caseState={ws.companionState.caseState}
                rankedSections={ws.rankedSections}
                pinnedSection={ws.pinnedSection}
                onPinSection={ws.setPinnedSection}
                onActionHint={(hint) => {
                  switch (hint.type) {
                    case 'suggest_inquiry':
                      ws.handleStartInquiry();
                      break;
                    case 'suggest_evidence':
                      break;
                    case 'suggest_resolution':
                      if (hint.data?.inquiryId) {
                        ws.handleOpenInquiry(hint.data.inquiryId as string);
                      }
                      break;
                  }
                }}
                onDismissCompleted={ws.dismissCompleted}
                onViewCase={ws.handleBackToBrief}
                onViewInquiries={() => ws.setViewMode('inquiry-dashboard')}
                onTogglePosition={ws.toggleCompanion}
                onClose={() => ws.setCompanionPosition('hidden')}
              />
            )}
            {/* Chat panel */}
            <div className="flex-1 min-h-0">
              <ChatPanel
                threadId={ws.threadId}
                contextLabel={`Chat about: ${ws.caseData.title}`}
                briefId={ws.brief?.id}
                onIntegrationPreview={ws.setIntegrationPreview}
                streamCallbacks={ws.streamCallbacks}
                mode={ws.chatMode.mode}
                onExitFocus={ws.chatMode.exitFocus}
              />
            </div>
          </div>
        }
      />

      <SettingsModal isOpen={ws.settingsOpen} onClose={() => ws.setSettingsOpen(false)} />

      <CommandPalette
        commands={commands}
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
      />

      {/* Integration Preview Modal */}
      {ws.integrationPreview && ws.brief && (
        <DiffViewer
          original={ws.brief.content_markdown || ''}
          proposed={ws.integrationPreview.updated_content}
          title="Add to Brief"
          onAccept={async (content) => {
            await documentsAPI.update(ws.brief!.id, { content_markdown: content });
            ws.setIntegrationPreview(null);
            ws.loadWorkspace();
          }}
          onReject={() => ws.setIntegrationPreview(null)}
          onClose={() => ws.setIntegrationPreview(null)}
        />
      )}
    </>
  );
}
