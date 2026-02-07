/**
 * Unified workspace layout - the core shell for case-centric work
 * 
 * Layout: Left Nav | Center View | Right Chat Panel
 */

'use client';

import { ReactNode } from 'react';

interface WorkspaceLayoutProps {
  leftPanel: ReactNode;
  centerView: ReactNode;
  rightPanel: ReactNode;
  header: ReactNode;
}

export function WorkspaceLayout({
  leftPanel,
  centerView,
  rightPanel,
  header,
}: WorkspaceLayoutProps) {
  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header: Breadcrumb + Mode Badge */}
      <div className="border-b border-neutral-200 bg-white">
        {header}
      </div>

      {/* Main workspace area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Cases & Projects Navigation */}
        <div className="w-64 border-r border-neutral-200 bg-neutral-50 overflow-y-auto flex flex-col">
          {leftPanel}
        </div>

        {/* Center: Adaptive view (Brief, Inquiry, Document) */}
        <div className="flex-1 overflow-y-auto">
          {centerView}
        </div>

        {/* Right: AI Chat Panel (Cursor-style, collapsible) */}
        <div className="border-l border-neutral-200 bg-white transition-all duration-200 ease-out">
          {rightPanel}
        </div>
      </div>
    </div>
  );
}
