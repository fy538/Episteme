/**
 * EdgeMarkerDefs — SVG marker definitions for edge arrows.
 *
 * Rendered once inside the ReactFlow SVG layer.
 * Each edge type has its own colored arrowhead marker.
 */

'use client';

export function EdgeMarkerDefs() {
  return (
    <svg className="absolute w-0 h-0">
      <defs>
        {/* Supports arrow — emerald */}
        <marker
          id="supports-arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981" />
        </marker>

        {/* Contradicts arrow — rose */}
        <marker
          id="contradicts-arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#f43f5e" />
        </marker>

        {/* Depends arrow — slate */}
        <marker
          id="depends-arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" />
        </marker>
      </defs>
    </svg>
  );
}
