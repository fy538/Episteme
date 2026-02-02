import { SignalExtractionCard as CardType, CardAction } from '@/lib/types/cards';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

interface Props {
  card: CardType;
  onAction: (action: CardAction) => void;
}

const signalTypeColors = {
  assumption: 'warning' as const,
  question: 'accent' as const,
  evidence: 'success' as const,
  claim: 'primary' as const
};

const signalTypeIcons = {
  assumption: '💭',
  question: '❓',
  evidence: '📋',
  claim: '⚖️'
};

export function SignalExtractionCard({ card, onAction }: Props) {
  return (
    <Card className="border-l-4 border-l-accent-500">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <span className="text-2xl">🔍</span>
          {card.heading}
        </CardTitle>
        {card.description && (
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
            {card.description}
          </p>
        )}
      </CardHeader>
      
      <CardContent className="space-y-4">
        {card.signals.map((signalGroup) => (
          <div key={signalGroup.type} className="space-y-2">
            <div className="flex items-center gap-2">
              <span>{signalTypeIcons[signalGroup.type]}</span>
              <h4 className="font-medium text-sm capitalize">
                {signalGroup.type}s ({signalGroup.items.length})
              </h4>
            </div>
            
            <div className="space-y-1.5 pl-6">
              {signalGroup.items.map((item) => (
                <div 
                  key={item.id}
                  className="flex items-start gap-2 p-2 rounded bg-neutral-50 dark:bg-neutral-800"
                >
                  <div className="flex-1">
                    <p className="text-sm">{item.text}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge 
                        variant={signalTypeColors[signalGroup.type]}
                        className="text-xs"
                      >
                        {Math.round(item.confidence * 100)}% confidence
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {item.status}
                      </Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
        
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
