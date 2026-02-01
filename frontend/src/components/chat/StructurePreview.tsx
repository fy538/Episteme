/**
 * Structure Preview - Floating card that suggests creating structure
 * 
 * Appears when AI detects that conversation would benefit from
 * case/inquiry structure. Non-blocking, progressively revealed.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardHeader, CardContent, CardFooter, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface StructureSuggestion {
  ready: boolean;
  confidence: number;
  structure_type: 'decision_case' | 'research_project' | 'comparison' | 'none';
  suggested_inquiries: string[];
  detected_assumptions: string[];
  reasoning: string;
  context_summary: string;
  dismissed?: boolean;
}

interface StructurePreviewProps {
  suggestion: StructureSuggestion;
  onAccept: () => void;
  onDismiss: () => void;
  onConfigure?: () => void;
}

export function StructurePreview({
  suggestion,
  onAccept,
  onDismiss,
  onConfigure
}: StructurePreviewProps) {
  if (!suggestion || suggestion.dismissed || !suggestion.ready) {
    return null;
  }

  const structureTypeLabel = {
    decision_case: 'Decision Case',
    research_project: 'Research Project',
    comparison: 'Comparison Analysis',
    none: 'Structure'
  }[suggestion.structure_type];

  const structureIcon = {
    decision_case: '⚖️',
    research_project: '🔬',
    comparison: '⚡',
    none: '📋'
  }[suggestion.structure_type];

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className="fixed bottom-24 right-6 w-[420px] z-50"
      >
        <Card className="shadow-2xl border-accent-200 dark:border-accent-800">
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2 flex-1">
                <span className="text-2xl">{structureIcon}</span>
                <div>
                  <CardTitle className="text-base">
                    {structureTypeLabel} Detected
                  </CardTitle>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                    {suggestion.context_summary}
                  </p>
                </div>
              </div>
              <Badge 
                variant={suggestion.confidence > 0.85 ? 'success' : 'warning'}
                className="shrink-0"
              >
                {Math.round(suggestion.confidence * 100)}% confident
              </Badge>
            </div>
          </CardHeader>
          
          <CardContent className="space-y-4">
            {/* Suggested Inquiries */}
            {suggestion.suggested_inquiries.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2 flex items-center gap-2">
                  <span>🔍</span>
                  Key Questions ({suggestion.suggested_inquiries.length})
                </h4>
                <ul className="space-y-1.5">
                  {suggestion.suggested_inquiries.slice(0, 4).map((inquiry, i) => (
                    <li 
                      key={i}
                      className="text-sm text-neutral-600 dark:text-neutral-400 pl-4 relative before:content-['•'] before:absolute before:left-0 before:text-accent-500"
                    >
                      {inquiry}
                    </li>
                  ))}
                </ul>
                {suggestion.suggested_inquiries.length > 4 && (
                  <p className="text-xs text-neutral-500 mt-1 pl-4">
                    +{suggestion.suggested_inquiries.length - 4} more
                  </p>
                )}
              </div>
            )}
            
            {/* Detected Assumptions */}
            {suggestion.detected_assumptions.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2 flex items-center gap-2">
                  <span>⚠️</span>
                  Assumptions to Validate ({suggestion.detected_assumptions.length})
                </h4>
                <ul className="space-y-1.5">
                  {suggestion.detected_assumptions.slice(0, 3).map((assumption, i) => (
                    <li 
                      key={i}
                      className="text-sm text-neutral-600 dark:text-neutral-400 pl-4 relative before:content-['⚠️'] before:absolute before:left-0 before:text-xs"
                    >
                      {assumption}
                    </li>
                  ))}
                </ul>
                {suggestion.detected_assumptions.length > 3 && (
                  <p className="text-xs text-neutral-500 mt-1 pl-4">
                    +{suggestion.detected_assumptions.length - 3} more
                  </p>
                )}
              </div>
            )}

            {/* Reasoning */}
            <div className="text-xs text-neutral-500 dark:text-neutral-400 pt-2 border-t border-neutral-200 dark:border-neutral-700">
              <span className="font-medium">Why: </span>
              {suggestion.reasoning}
            </div>
          </CardContent>
          
          <CardFooter className="flex gap-2 border-t border-neutral-200 dark:border-neutral-700 pt-4">
            <Button 
              onClick={onAccept}
              variant="primary"
              className="flex-1"
            >
              Create Case
            </Button>
            <Button 
              onClick={onDismiss}
              variant="secondary"
            >
              Not Now
            </Button>
            {onConfigure && (
              <Button 
                onClick={onConfigure}
                variant="ghost"
                className="px-3"
                title="Configure structure detection"
              >
                ⚙️
              </Button>
            )}
          </CardFooter>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}
