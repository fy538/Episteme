/**
 * Case navigation sidebar - projects, cases, quick actions
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import type { Case } from '@/lib/types/case';
import type { Project } from '@/lib/types/project';

interface CaseNavigationProps {
  projects: Project[];
  cases: Case[];
  activeCaseId?: string;
  onCreateCase: () => void;
  onOpenSettings: () => void;
}

export function CaseNavigation({
  projects,
  cases,
  activeCaseId,
  onCreateCase,
  onOpenSettings,
}: CaseNavigationProps) {
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());

  const toggleProject = (projectId: string) => {
    setExpandedProjects(prev => {
      const next = new Set(prev);
      if (next.has(projectId)) {
        next.delete(projectId);
      } else {
        next.add(projectId);
      }
      return next;
    });
  };

  // Group cases by project
  const casesByProject = cases.reduce((acc, c) => {
    const projectId = c.project || 'no-project';
    if (!acc[projectId]) acc[projectId] = [];
    acc[projectId].push(c);
    return acc;
  }, {} as Record<string, Case[]>);

  const casesWithoutProject = casesByProject['no-project'] || [];
  const projectsWithCases = projects.filter(p => casesByProject[p.id]?.length > 0);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-white">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Workspace</h2>
        <Button onClick={onCreateCase} size="sm" className="w-full">
          + New Case
        </Button>
      </div>

      {/* Cases & Projects */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Cases without project */}
        {casesWithoutProject.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Recent Cases
            </h3>
            <div className="space-y-1">
              {casesWithoutProject.map(c => (
                <Link
                  key={c.id}
                  href={`/cases/${c.id}`}
                  className={`block px-3 py-2 text-sm rounded-lg transition-colors ${
                    activeCaseId === c.id
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {c.title}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Projects with cases */}
        {projectsWithCases.map(project => {
          const isExpanded = expandedProjects.has(project.id);
          const projectCases = casesByProject[project.id] || [];

          return (
            <div key={project.id}>
              <button
                onClick={() => toggleProject(project.id)}
                className="flex items-center justify-between w-full text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 hover:text-gray-700"
              >
                <span>{project.title}</span>
                <svg
                  className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
              
              {isExpanded && (
                <div className="space-y-1">
                  {projectCases.map(c => (
                    <Link
                      key={c.id}
                      href={`/cases/${c.id}`}
                      className={`block px-3 py-2 text-sm rounded-lg transition-colors ${
                        activeCaseId === c.id
                          ? 'bg-blue-50 text-blue-700 font-medium'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      {c.title}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Settings - Bottom */}
      <div className="p-4 border-t border-gray-200">
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="font-medium">Settings</span>
        </button>
      </div>
    </div>
  );
}
