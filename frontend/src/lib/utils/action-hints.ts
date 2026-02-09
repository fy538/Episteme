/**
 * Shared action hint display helpers.
 *
 * Used by ChatPanel (and any future chat surfaces) to render
 * AI-suggested action hint buttons with icons and labels.
 */

export function getActionHintIcon(type: string): string {
  switch (type) {
    case 'suggest_case': return '📋';
    case 'suggest_inquiry': return '🔍';
    case 'suggest_resolution': return '✅';
    default: return '💡';
  }
}

export function getActionHintLabel(type: string, data: Record<string, unknown>): string {
  switch (type) {
    case 'suggest_case':
      return (data.suggested_title as string) || 'Create case';
    case 'suggest_inquiry':
      return (data.suggested_title as string) || 'Start inquiry';
    case 'suggest_resolution':
      return 'Resolve inquiry';
    default:
      return 'Take action';
  }
}
