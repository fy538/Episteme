/**
 * TipTap mark extension for rendering inline suggestion diffs.
 *
 * Suggestion types:
 * - "replace": red strikethrough on old text, green highlight on new text
 * - "delete": red strikethrough
 * - "add": green highlight (inserted at cursor)
 * - "cite" / "clarify": blue underline
 *
 * Each mark carries a suggestionId so the editor can map marks to
 * suggestion objects for accept/reject actions.
 */

import { Mark } from '@tiptap/core';

export type SuggestionMarkType = 'delete' | 'replace_old' | 'replace_new' | 'add' | 'cite' | 'clarify';

export interface SuggestionMarkAttributes {
  suggestionId: string;
  type: SuggestionMarkType;
  /** For replace_new marks, the new content to insert on accept */
  newContent?: string;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    suggestion: {
      setSuggestion: (attributes: SuggestionMarkAttributes) => ReturnType;
      unsetSuggestion: () => ReturnType;
    };
  }
}

export const SuggestionMark = Mark.create({
  name: 'suggestion',

  // Allow multiple marks on the same text
  inclusive: false,
  excludes: '',

  addAttributes() {
    return {
      suggestionId: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-suggestion-id'),
        renderHTML: (attributes) => ({
          'data-suggestion-id': attributes.suggestionId,
        }),
      },
      type: {
        default: 'replace_old',
        parseHTML: (element) => element.getAttribute('data-suggestion-type'),
        renderHTML: (attributes) => ({
          'data-suggestion-type': attributes.type,
        }),
      },
      newContent: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-new-content'),
        renderHTML: (attributes) => {
          if (!attributes.newContent) return {};
          return { 'data-new-content': attributes.newContent };
        },
      },
    };
  },

  parseHTML() {
    return [{ tag: 'span[data-suggestion-id]' }];
  },

  renderHTML({ HTMLAttributes }) {
    const type = HTMLAttributes['data-suggestion-type'] as SuggestionMarkType;

    const classMap: Record<SuggestionMarkType, string> = {
      delete: 'suggestion-mark suggestion-delete line-through bg-red-100 text-red-700 cursor-pointer',
      replace_old: 'suggestion-mark suggestion-replace-old line-through bg-red-100 text-red-700 cursor-pointer',
      replace_new: 'suggestion-mark suggestion-replace-new bg-green-100 text-green-800 cursor-pointer',
      add: 'suggestion-mark suggestion-add bg-green-100 text-green-800 cursor-pointer',
      cite: 'suggestion-mark suggestion-cite underline decoration-blue-400 cursor-pointer',
      clarify: 'suggestion-mark suggestion-clarify underline decoration-amber-400 cursor-pointer',
    };

    return [
      'span',
      {
        ...HTMLAttributes,
        class: classMap[type] || 'suggestion-mark cursor-pointer',
      },
      0,
    ];
  },

  addCommands() {
    return {
      setSuggestion:
        (attributes: SuggestionMarkAttributes) =>
        ({ commands }) => {
          return commands.setMark(this.name, attributes);
        },
      unsetSuggestion:
        () =>
        ({ commands }) => {
          return commands.unsetMark(this.name);
        },
    };
  },
});
