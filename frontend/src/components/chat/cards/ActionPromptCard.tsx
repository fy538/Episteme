import { ActionPromptCard as CardType, CardAction } from '@/lib/types/cards';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

interface Props {
  card: CardType;
  onAction: (action: CardAction) => void;
}

const priorityConfig = {
  high: { 
    border: 'border-l-error-500', 
    icon: '🔴',
    bgClass: 'bg-error-50 dark:bg-error-900/20'
  },
  medium: { 
    border: 'border-l-warning-500', 
    icon: '🟡',
    bgClass: 'bg-warning-50 dark:bg-warning-900/20'
  },
  low: { 
    border: 'border-l-accent-500', 
    icon: '🟢',
    bgClass: 'bg-accent-50 dark:bg-accent-900/20'
  }
};

export function ActionPromptCard({ card, onAction }: Props) {
  const config = priorityConfig[card.priority];
  
  return (
    <Card className={`border-l-4 ${config.border} ${config.bgClass}`}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <span className="text-xl">{config.icon}</span>
          {card.heading}
        </CardTitle>
        <p className="text-sm text-neutral-700 dark:text-neutral-300 mt-1">
          {card.description}
        </p>
      </CardHeader>
      
      <CardContent>
        <div className="flex gap-2">
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
      </CardContent>
    </Card>
  );
}
