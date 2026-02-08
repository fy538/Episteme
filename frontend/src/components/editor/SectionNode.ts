/**
 * SectionNode — TipTap Node extension for section markers.
 *
 * Parses `<!-- section:SECTION_ID -->` HTML comments in the editor content
 * and renders them as invisible anchor elements with `data-section-id`
 * attributes. This bridges the markdown content with the BriefSection
 * metadata layer, enabling the grounding gutter and section tracking.
 *
 * On serialization (save), renders back as the HTML comment to preserve
 * the backend contract.
 */

import { Node, mergeAttributes } from '@tiptap/core';

export interface SectionNodeAttributes {
  sectionId: string;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    sectionMarker: {
      insertSectionMarker: (sectionId: string) => ReturnType;
    };
  }
}

export const SectionNode = Node.create({
  name: 'sectionMarker',

  group: 'block',
  atom: true, // Not editable — acts as a structural anchor
  selectable: false,
  draggable: false,

  addAttributes() {
    return {
      sectionId: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-section-id'),
        renderHTML: (attributes) => ({
          'data-section-id': attributes.sectionId,
        }),
      },
    };
  },

  parseHTML() {
    return [
      {
        // Match the rendered div anchors
        tag: 'div[data-section-id]',
      },
      {
        // Match HTML comments in the content: <!-- section:ID -->
        // TipTap/ProseMirror doesn't natively parse comments, so we
        // handle this via a custom rule that matches a sentinel element.
        // The BriefEditor preprocesses the HTML to convert comments to divs.
        tag: 'div.section-marker',
        getAttrs: (element) => {
          const el = element as HTMLElement;
          return { sectionId: el.getAttribute('data-section-id') };
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        class: 'section-marker',
        style: 'height: 0; overflow: hidden; margin: 0; padding: 0; border: 0;',
        contenteditable: 'false',
      }),
    ];
  },

  addCommands() {
    return {
      insertSectionMarker:
        (sectionId: string) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs: { sectionId },
          });
        },
    };
  },
});

/**
 * Preprocesses HTML content to convert section comment markers into
 * parseable div elements before passing to TipTap.
 *
 * Converts: `<!-- section:sf-abc12345 -->` → `<div class="section-marker" data-section-id="sf-abc12345"></div>`
 */
export function preprocessSectionMarkers(html: string): string {
  return html.replace(
    /<!--\s*section:([\w-]+)\s*-->/g,
    '<div class="section-marker" data-section-id="$1"></div>'
  );
}

/**
 * Postprocesses HTML content to convert section marker divs back into
 * HTML comments for backend persistence.
 *
 * Converts: `<div class="section-marker" data-section-id="sf-abc12345"></div>` → `<!-- section:sf-abc12345 -->`
 */
export function postprocessSectionMarkers(html: string): string {
  return html.replace(
    /<div[^>]*class="section-marker"[^>]*data-section-id="([\w-]+)"[^>]*><\/div>/g,
    '<!-- section:$1 -->'
  );
}
