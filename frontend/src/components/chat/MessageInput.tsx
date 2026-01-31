/**
 * Message input component
 */

import { useState, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';

export function MessageInput({ 
  onSend, 
  disabled 
}: { 
  onSend: (content: string) => void;
  disabled?: boolean;
}) {
  const [input, setInput] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    // Submit on Enter (without shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-gray-200 p-4 bg-white">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          disabled={disabled}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        <Button type="submit" disabled={disabled || !input.trim()}>
          Send
        </Button>
      </div>
    </form>
  );
}
