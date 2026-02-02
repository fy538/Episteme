/**
 * Project Switcher - quick navigation between projects
 * Keyboard shortcut: Cmd+Shift+P
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import type { Project } from '@/lib/types/project';

interface ProjectSwitcherProps {
  projects: Project[];
  currentProjectId?: string;
  onProjectSelect?: (projectId: string) => void;
  onCreateProject?: () => void;
}

export function ProjectSwitcher({
  projects,
  currentProjectId,
  onProjectSelect,
  onCreateProject,
}: ProjectSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  // Filter projects by search
  const filteredProjects = search.trim()
    ? projects.filter(p =>
        p.title.toLowerCase().includes(search.toLowerCase()) ||
        p.description?.toLowerCase().includes(search.toLowerCase())
      )
    : projects;

  // Sort: current first, then by updated_at
  const sortedProjects = [...filteredProjects].sort((a, b) => {
    if (a.id === currentProjectId) return -1;
    if (b.id === currentProjectId) return 1;
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Cmd/Ctrl+Shift+P to open
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'p') {
        e.preventDefault();
        setIsOpen(true);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setSearch('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Arrow key navigation
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, sortedProjects.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const selectedProject = sortedProjects[selectedIndex];
        if (selectedProject) {
          handleSelectProject(selectedProject.id);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        setIsOpen(false);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, sortedProjects, selectedIndex]);

  function handleSelectProject(projectId: string) {
    if (onProjectSelect) {
      onProjectSelect(projectId);
    } else {
      router.push(`/workspace/projects/${projectId}`);
    }
    setIsOpen(false);
  }

  const currentProject = projects.find(p => p.id === currentProjectId);

  if (!isOpen) {
    return (
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(true)}
        className="gap-2 text-neutral-700 hover:text-neutral-900"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
        <span className="max-w-[150px] truncate">
          {currentProject?.title || 'Select Project'}
        </span>
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </Button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black bg-opacity-25">
      <div className="w-full max-w-lg bg-white rounded-lg shadow-2xl overflow-hidden">
        {/* Search Input */}
        <div className="p-4 border-b border-neutral-200">
          <Input
            ref={inputRef}
            type="text"
            placeholder="Search projects... (Cmd+Shift+P)"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setSelectedIndex(0);
            }}
            className="w-full"
          />
        </div>

        {/* Project List */}
        <div className="max-h-96 overflow-y-auto">
          {sortedProjects.length === 0 ? (
            <div className="p-8 text-center text-neutral-500">
              <p>No projects found</p>
              {onCreateProject && (
                <Button
                  onClick={() => {
                    setIsOpen(false);
                    onCreateProject();
                  }}
                  className="mt-4"
                >
                  Create Project
                </Button>
              )}
            </div>
          ) : (
            <div>
              {sortedProjects.map((project, index) => (
                <button
                  key={project.id}
                  onClick={() => handleSelectProject(project.id)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={cn(
                    'w-full text-left px-4 py-3 border-l-4 transition-colors',
                    index === selectedIndex
                      ? 'bg-accent-50 border-accent-600'
                      : 'border-transparent hover:bg-neutral-50',
                    project.id === currentProjectId && 'bg-accent-50'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-neutral-900 truncate">
                        {project.title}
                        {project.id === currentProjectId && (
                          <span className="ml-2 text-xs text-accent-600">(current)</span>
                        )}
                      </p>
                      {project.description && (
                        <p className="text-sm text-neutral-500 truncate">
                          {project.description}
                        </p>
                      )}
                    </div>
                    {project.is_archived && (
                      <span className="text-xs text-neutral-400">Archived</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {onCreateProject && sortedProjects.length > 0 && (
          <div className="p-3 border-t border-neutral-200 bg-neutral-50">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setIsOpen(false);
                onCreateProject();
              }}
              className="w-full justify-start text-neutral-600"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Create New Project
            </Button>
          </div>
        )}
      </div>

      {/* Backdrop */}
      <div
        className="fixed inset-0 -z-10"
        onClick={() => setIsOpen(false)}
      />
    </div>
  );
}
