/**
 * TipTap extension for highlighting assumptions in brief
 */

import { Mark } from '@tiptap/core';

export interface AssumptionAttributes {
  assumptionId: string;
  status: 'untested' | 'investigating' | 'validated';
  riskLevel: 'low' | 'medium' | 'high';
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    assumption: {
      setAssumption: (attributes: AssumptionAttributes) => ReturnType;
      unsetAssumption: () => ReturnType;
    };
  }
}

export const AssumptionMark = Mark.create({
  name: 'assumption',

  addAttributes() {
    return {
      assumptionId: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-assumption-id'),
        renderHTML: (attributes) => ({
          'data-assumption-id': attributes.assumptionId,
        }),
      },
      status: {
        default: 'untested',
        parseHTML: (element) => element.getAttribute('data-status'),
        renderHTML: (attributes) => ({
          'data-status': attributes.status,
        }),
      },
      riskLevel: {
        default: 'medium',
        parseHTML: (element) => element.getAttribute('data-risk'),
        renderHTML: (attributes) => ({
          'data-risk': attributes.riskLevel,
        }),
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'span[data-assumption-id]',
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      {
        ...HTMLAttributes,
        class: `assumption assumption-${HTMLAttributes['data-status']} cursor-pointer`,
      },
      0,
    ];
  },

  addCommands() {
    return {
      setAssumption:
        (attributes: AssumptionAttributes) =>
        ({ commands }) => {
          return commands.setMark(this.name, attributes);
        },
      unsetAssumption:
        () =>
        ({ commands }) => {
          return commands.unsetMark(this.name);
        },
    };
  },
});
