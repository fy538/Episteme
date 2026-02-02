import { AssumptionValidatorCard as CardType, CardAction } from '@/lib/types/cards';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

interface Props {
  card: CardType;
  onAction: (action: CardAction) => void;
}

const statusConfig = {
  pending: { color: 'secondary' as const, icon: '⏳', label: 'Pending' },
  validated: { color: 'success' as const, icon: '✅', label: 'Validated' },
  refuted: { color: 'error' as const, icon: '❌', label: 'Refuted' },
  uncertain: { color: 'warning' as const, icon: '⚠️', label: 'Uncertain' }
};

export function AssumptionValidatorCard({ card, onAction }: Props) {
  return (
    <Card className="border-l-4 border-l-warning-500">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <span className="text-2xl">🔬</span>
          {card.heading}
        </CardTitle>
        {card.description && (
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
            {card.description}
          </p>
        )}
      </CardHeader>
      
      <CardContent className="space-y-3">
        {card.assumptions.map((assumption, idx) => {
          const config = statusConfig[assumption.status];
          
          return (
            <div 
              key={assumption.id}
              className="p-3 rounded-lg border border-neutral-200 dark:border-neutral-700 space-y-2"
            >
              <div className="flex items-start gap-2">
                <span className="text-lg shrink-0">{config.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">
                    {idx + 1}. {assumption.text}
                  </p>
                  <Badge variant={config.color} className="mt-1 text-xs">
                    {config.label}
                    {assumption.confidence && ` (${Math.round(assumption.confidence * 100)}%)`}
                  </Badge>
                </div>
              </div>
              
              {/* Supporting/Contradicting Evidence */}
              {(assumption.supporting_evidence.length > 0 || assumption.contradicting_evidence.length > 0) && (
                <div className="pl-7 space-y-1 text-xs">
                  {assumption.supporting_evidence.length > 0 && (
                    <div className="text-success-700 dark:text-success-400">
                      ✓ {assumption.supporting_evidence.length} supporting
                    </div>
                  )}
                  {assumption.contradicting_evidence.length > 0 && (
                    <div className="text-error-700 dark:text-error-400">
                      ✗ {assumption.contradicting_evidence.length} contradicting
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        
        {/* Actions */}
        {card.actions.length > 0 && (
          <div className="flex gap-2 pt-2 border-t">
            {card.actions.map((action) => (
              <Button
                key={action.id}
                variant={action.variant === 'primary' ? 'default' : 'secondary'}
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
