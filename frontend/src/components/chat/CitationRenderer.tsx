/**
 * CitationRenderer — post-processes rendered markdown to replace [N] markers
 * with interactive CitationBadge components.
 *
 * Wraps children (typically Streamdown output) and scans text nodes for [N]
 * patterns, replacing them with CitationBadge when source chunks are available.
 *
 * Runs as a post-processing wrapper rather than a remark plugin, since
 * Streamdown handles incomplete markdown during streaming. By the time this
 * component processes the tree, markdown links like [text](url) have already
 * been rendered into <a> elements, so [N] in text nodes are safe to match.
 *
 * Memoized to avoid re-traversal when content/chunks haven't changed.
 */

'use client';

import * as React from 'react';
import type { SourceChunk } from '@/lib/types/chat';
import { CitationBadge } from './CitationBadge';

interface CitationRendererProps {
  /** The raw markdown text content (used for memo comparison) */
  content: string;
  /** Source chunks keyed by index (0-indexed) */
  sourceChunks: SourceChunk[];
  /** Called when a citation badge is clicked */
  onCitationClick?: (chunk: SourceChunk) => void;
  /** Children to render (the Streamdown component) */
  children?: React.ReactNode;
}

/** Regex: standalone [N] not followed by ( to avoid matching markdown link text */
const CITATION_SPLIT = /(\[\d+\](?!\())/g;
const CITATION_TEST = /\[\d+\](?!\()/;
const CITATION_EXTRACT = /^\[(\d+)\]$/;

/**
 * Parse text content and replace [N] markers with CitationBadge components.
 * N is 1-indexed in the text but 0-indexed in the chunks array.
 */
function parseCitations(
  text: string,
  sourceChunks: SourceChunk[],
  onCitationClick?: (chunk: SourceChunk) => void
): React.ReactNode[] {
  if (!sourceChunks.length) return [text];

  const parts = text.split(CITATION_SPLIT);

  return parts.map((part, i) => {
    const match = part.match(CITATION_EXTRACT);
    if (match) {
      const citNum = parseInt(match[1], 10);
      const citIndex = citNum - 1; // Convert 1-indexed to 0-indexed
      const chunk = sourceChunks[citIndex];
      if (chunk) {
        return (
          <CitationBadge
            key={`cit-${citNum}`}
            index={citNum}
            chunk={chunk}
            onClick={onCitationClick}
          />
        );
      }
    }
    // Return plain text for non-citation parts or unmatched indices
    return part || null;
  });
}

/**
 * Recursively walks a React element tree and replaces text nodes containing
 * [N] patterns with CitationBadge components.
 */
function processNode(
  node: React.ReactNode,
  sourceChunks: SourceChunk[],
  onCitationClick?: (chunk: SourceChunk) => void,
): React.ReactNode {
  // Handle strings — parse for citations
  if (typeof node === 'string') {
    if (CITATION_TEST.test(node)) {
      return <>{parseCitations(node, sourceChunks, onCitationClick)}</>;
    }
    return node;
  }

  // Handle numbers, null, undefined, boolean
  if (node == null || typeof node === 'number' || typeof node === 'boolean') {
    return node;
  }

  // Handle arrays
  if (Array.isArray(node)) {
    return node.map((child, i) => {
      const processed = processNode(child, sourceChunks, onCitationClick);
      // Preserve existing keys when possible
      if (React.isValidElement(child) && child.key != null) {
        return processed;
      }
      return <React.Fragment key={i}>{processed}</React.Fragment>;
    });
  }

  // Handle React elements — recurse into children
  if (React.isValidElement(node)) {
    const element = node as React.ReactElement<{ children?: React.ReactNode }>;
    const children = element.props.children;

    if (children != null) {
      const processedChildren = processNode(children, sourceChunks, onCitationClick);
      return React.cloneElement(element, {}, processedChildren);
    }
    return element;
  }

  return node;
}

export const CitationRenderer = React.memo(
  function CitationRenderer({
    sourceChunks,
    onCitationClick,
    children,
  }: CitationRendererProps) {
    // If no sources, just render children as-is (no processing overhead)
    if (!sourceChunks.length) {
      return <>{children}</>;
    }

    // Walk the rendered tree and replace [N] markers
    return <>{processNode(children, sourceChunks, onCitationClick)}</>;
  },
  (prev, next) =>
    prev.content === next.content &&
    prev.sourceChunks === next.sourceChunks &&
    prev.onCitationClick === next.onCitationClick
);
