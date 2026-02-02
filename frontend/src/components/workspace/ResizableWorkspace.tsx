/**
 * Resizable 3-panel workspace layout
 * 
 * Provides drag-to-resize panels with persistent sizing.
 * 
 * NOTE: Requires 'react-resizable-panels' package:
 *   npm install react-resizable-panels
 */

'use client';

import { ReactNode, useEffect, useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';

interface ResizableWorkspaceProps {
  leftPanel: ReactNode;
  centerPanel: ReactNode;
  rightPanel: ReactNode;
  rightPanelCollapsible?: boolean;
}

export function ResizableWorkspace({
  leftPanel,
  centerPanel,
  rightPanel,
  rightPanelCollapsible = true,
}: ResizableWorkspaceProps) {
  const [isRightCollapsed, setIsRightCollapsed] = useState(false);

  // Restore panel sizes from localStorage
  useEffect(() => {
    const savedCollapsed = localStorage.getItem('workspace-right-collapsed');
    if (savedCollapsed === 'true') {
      setIsRightCollapsed(true);
    }
  }, []);

  const handleRightCollapse = (collapsed: boolean) => {
    setIsRightCollapsed(collapsed);
    localStorage.setItem('workspace-right-collapsed', String(collapsed));
  };

  return (
    <PanelGroup direction="horizontal" className="flex-1">
      {/* Left Panel - Navigation */}
      <Panel
        defaultSize={20}
        minSize={15}
        maxSize={30}
        className="bg-neutral-50 border-r border-neutral-200"
        id="left-panel"
        order={1}
      >
        <div className="h-full overflow-y-auto">
          {leftPanel}
        </div>
      </Panel>

      {/* Resize Handle */}
      <PanelResizeHandle className="w-1 bg-neutral-200 hover:bg-accent-500 transition-colors cursor-col-resize" />

      {/* Center Panel - Main Content */}
      <Panel
        defaultSize={isRightCollapsed ? 80 : 60}
        minSize={40}
        className="bg-white"
        id="center-panel"
        order={2}
      >
        <div className="h-full overflow-y-auto">
          {centerPanel}
        </div>
      </Panel>

      {/* Resize Handle (only show if right panel not collapsed) */}
      {!isRightCollapsed && (
        <PanelResizeHandle className="w-1 bg-neutral-200 hover:bg-accent-500 transition-colors cursor-col-resize" />
      )}

      {/* Right Panel - Chat/Sidebar (Collapsible) */}
      {rightPanelCollapsible ? (
        <Panel
          defaultSize={isRightCollapsed ? 0 : 20}
          minSize={0}
          maxSize={40}
          collapsible
          className="bg-white border-l border-neutral-200"
          id="right-panel"
          order={3}
          onCollapse={handleRightCollapse}
        >
          {!isRightCollapsed && (
            <div className="h-full">
              {rightPanel}
            </div>
          )}
        </Panel>
      ) : (
        <Panel
          defaultSize={20}
          minSize={15}
          maxSize={40}
          className="bg-white border-l border-neutral-200"
          id="right-panel"
          order={3}
        >
          <div className="h-full">
            {rightPanel}
          </div>
        </Panel>
      )}
    </PanelGroup>
  );
}
