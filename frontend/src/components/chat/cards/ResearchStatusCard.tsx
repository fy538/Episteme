import { ResearchStatusCard as CardType, CardAction } from '@/lib/types/cards';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';
import { CostSummary } from '@/components/workflow/CostSummary';

interface Props {
  card: CardType;
  onAction: (action: CardAction) => void;
}

const stepStatusIcons = {
  pending: '⏳',
  in_progress: '▶️',
  completed: '✅',
  failed: '❌'
};

export function ResearchStatusCard({ card, onAction }: Props) {
  const isRunning = card.status === 'running';
  
  return (
    <Card className={`border-l-4 ${isRunning ? 'border-l-accent-500' : 'border-l-neutral-500'}`}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          {isRunning && <Spinner size="sm" />}
          <span className="text-2xl">🤖</span>
          {card.heading}
        </CardTitle>
        {card.description && (
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
            {card.description}
          </p>
        )}
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Progress Steps */}
        {card.progress_steps.length > 0 && (
          <div className="space-y-2">
            {card.progress_steps.map((step, idx) => (
              <div 
                key={idx}
                className="flex items-start gap-2 text-sm"
              >
                <span className="shrink-0">{stepStatusIcons[step.status]}</span>
                <div className="flex-1">
                  <div className="font-medium">{step.label}</div>
                  {step.details && (
                    <div className="text-xs text-neutral-600 dark:text-neutral-400 mt-0.5">
                      {step.details}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Results Preview */}
        {card.results_preview && (
          <div className="p-3 rounded bg-neutral-50 dark:bg-neutral-800 text-sm">
            <div className="font-medium mb-1">Preview:</div>
            <div className="text-neutral-700 dark:text-neutral-300">
              {card.results_preview}
            </div>
          </div>
        )}
        
        {/* Cost summary (shown when workflow completes with correlation_id) */}
        {card.status === 'completed' && card.metadata?.correlation_id && (
          <CostSummary correlationId={card.metadata.correlation_id} compact />
        )}

        {/* Actions */}
        {card.actions.length > 0 && (
          <div className="flex gap-2 pt-2 border-t">
            {card.actions.map((action) => (
              <Button
                key={action.id}
                variant={action.variant === 'danger' ? 'destructive' : action.variant === 'primary' ? 'default' : 'outline'}
                size="sm"
                onClick={() => onAction(action)}
              >
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
