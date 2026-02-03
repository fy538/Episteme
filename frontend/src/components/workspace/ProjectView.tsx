/**
 * Project View - Shows detailed view of a single project
 * Displays cases, inquiries, and chat threads for this project
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { NoCasesEmpty, NoInquiriesEmpty, NoConversationsEmpty } from '@/components/ui/empty-state';
import type { Project } from '@/lib/types/project';
import type { Case, Inquiry } from '@/lib/types/case';
import type { ChatThread } from '@/lib/types/chat';
import { AIProjectSummary } from './AIProjectSummary';
import { ResearchCompleteCard } from './intelligence/ResearchCompleteCard';
import { ConversationPromptCard } from './intelligence/ConversationPromptCard';
import { AttentionNeededCard } from './intelligence/AttentionNeededCard';
import { CaseCardExpanded } from './CaseCardExpanded';
import { InquiryList } from './InquiryList';
import { ConversationList } from './ConversationList';
import { DocumentsList } from './DocumentsList';
import { EditableDescription } from './EditableDescription';
import { ProjectSettings } from './ProjectSettings';

interface ProjectViewProps {
  project: Project;
  cases: Case[];
  inquiries: Inquiry[];
  threads: ChatThread[];
  onCreateCase: () => void;
  onCreateInquiry?: () => void;
  onStartChat?: () => void;
  onUploadDocument?: () => void;
  onUpdateProject?: (data: Partial<Project>) => void;
}

export function ProjectView({
  project,
  cases,
  inquiries,
  threads,
  onCreateCase,
  onCreateInquiry,
  onStartChat,
  onUploadDocument,
  onUpdateProject,
}: ProjectViewProps) {
  const router = useRouter();
  const [selectedTab, setSelectedTab] = useState<'overview' | 'cases' | 'inquiries' | 'threads' | 'documents'>('overview');
  const [showSettings, setShowSettings] = useState(false);

  const activeCases = cases.filter(c => c.status === 'active');
  const draftCases = cases.filter(c => c.status === 'draft');
  const openInquiries = inquiries.filter(i => i.status === 'open' || i.status === 'investigating');

  const handleSaveDescription = (description: string) => {
    if (onUpdateProject) {
      onUpdateProject({ description });
    }
  };

  const handleSaveSettings = (data: Partial<Project>) => {
    if (onUpdateProject) {
      onUpdateProject(data);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Project Header with Settings and Start Chat */}
      <div>
        <div className="flex flex-col md:flex-row items-start justify-between gap-4 mb-2">
          <div className="flex-1 min-w-0 w-full md:w-auto">
            <h1 className="text-2xl md:text-3xl tracking-tight font-bold text-primary-900 dark:text-primary-50 mb-2">
              {project.title}
            </h1>
            {/* Editable Description */}
            <EditableDescription
              description={project.description || ''}
              onSave={handleSaveDescription}
              placeholder="Click to add project description..."
            />
          </div>
          <div className="flex gap-2 shrink-0 w-full md:w-auto">
            <Button variant="outline" onClick={() => setShowSettings(true)} className="flex-1 md:flex-none">
              <svg className="w-4 h-4 md:mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
              </svg>
              <span className="hidden md:inline">Edit Project</span>
            </Button>
            {onStartChat && (
              <Button onClick={onStartChat} className="flex-1 md:flex-none">
                <svg className="w-4 h-4 md:mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span className="hidden md:inline">Start Chat</span>
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Project Settings Modal */}
      <ProjectSettings
        project={project}
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        onSave={handleSaveSettings}
      />

      {/* Tabs */}
      <Tabs defaultValue="overview" onValueChange={(v) => setSelectedTab(v as any)}>
        <TabsList className="w-full md:w-auto overflow-x-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="cases">Cases</TabsTrigger>
          <TabsTrigger value="inquiries">Inquiries</TabsTrigger>
          <TabsTrigger value="threads">Chats</TabsTrigger>
          <TabsTrigger value="documents">Docs</TabsTrigger>
        </TabsList>

        {/* Tab Content */}
        <TabsContent value="overview" className="mt-6">
          <div className="space-y-6">
            {/* AI Project Summary */}
            <AIProjectSummary
              projectName={project.title}
              onCreateCase={onCreateCase}
              onCreateInquiry={onCreateInquiry}
              onUploadDocument={onUploadDocument}
              onAskAI={onStartChat}
            />

            {/* Intelligence Feed */}
            <div>
              <h3 className="text-lg font-semibold text-primary-900 dark:text-primary-50 mb-4">
                What Needs Your Attention
              </h3>
              <div className="space-y-4">
                <AttentionNeededCard />
                <ResearchCompleteCard />
              </div>
            </div>

            {/* AI Suggestions */}
            <div>
              <h3 className="text-lg font-semibold text-primary-900 dark:text-primary-50 mb-4">
                AI Suggestions
              </h3>
              <div className="space-y-4">
                <ConversationPromptCard />
              </div>
            </div>

            {/* Recent Activity (Mixed) */}
            <div>
              <h3 className="text-lg font-semibold text-primary-900 dark:text-primary-50 mb-4">
                Recent Activity
              </h3>
              <div className="space-y-2">
                {[...cases, ...threads]
                  .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
                  .slice(0, 6)
                  .map((item) => {
                    if ('status' in item) {
                      return (
                        <Link
                          key={item.id}
                          href={`/workspace/cases/${item.id}`}
                          className="block p-3 rounded-lg border border-neutral-200 dark:border-neutral-800 hover:border-accent-500 transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <svg className="w-4 h-4 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                            </svg>
                            <span className="font-medium text-sm flex-1 truncate">{item.title}</span>
                            <Badge variant="success" className="text-xs">Case</Badge>
                          </div>
                        </Link>
                      );
                    } else {
                      return (
                        <Link
                          key={item.id}
                          href={`/chat?thread=${item.id}`}
                          className="block p-3 rounded-lg border border-neutral-200 dark:border-neutral-800 hover:border-accent-500 transition-colors"
                        >
                          <div className="flex items-center gap-2">
                            <svg className="w-4 h-4 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                            <span className="font-medium text-sm flex-1 truncate">{item.title}</span>
                            <Badge variant="default" className="text-xs">Chat</Badge>
                          </div>
                        </Link>
                      );
                    }
                  })}
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="cases" className="mt-6">
          <div className="space-y-4">
            {cases.length === 0 ? (
              <NoCasesEmpty onCreate={onCreateCase} />
            ) : (
              <div className="space-y-3">
                {cases.map((c) => (
                  <CaseCardExpanded
                    key={c.id}
                    case={c}
                    inquiries={inquiries.filter(inq => inq.case === c.id)}
                    threads={threads.filter(t => t.primary_case === c.id)}
                    onOpenCase={() => router.push(`/workspace/cases/${c.id}`)}
                    onCreateInquiry={onCreateInquiry}
                    onStartChat={onStartChat}
                    onUploadDoc={onUploadDocument}
                  />
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="inquiries" className="mt-6">
          <InquiryList
            inquiries={inquiries}
            cases={cases}
            onCreateInquiry={onCreateInquiry}
          />
        </TabsContent>

        <TabsContent value="threads" className="mt-6">
          <ConversationList
            threads={threads}
            cases={cases}
            onStartChat={onStartChat}
          />
        </TabsContent>

        <TabsContent value="documents" className="mt-6">
          <DocumentsList
            cases={cases}
            onUploadDocument={onUploadDocument}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
