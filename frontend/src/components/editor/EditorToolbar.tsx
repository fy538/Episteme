/**
 * Editor toolbar - formatting controls
 */

import type { Editor } from '@tiptap/react';
import { Button } from '@/components/ui/button';

export function EditorToolbar({ editor }: { editor: Editor | null }) {
  if (!editor) return null;

  return (
    <div className="border-b border-gray-200 px-4 py-2 flex gap-1 bg-gray-50">
      <Button
        size="sm"
        variant="ghost"
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={editor.isActive('bold') ? 'bg-gray-200' : ''}
        title="Bold (Cmd+B)"
      >
        <span className="font-bold">B</span>
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => editor.chain().focus().toggleItalic().run()}
        className={editor.isActive('italic') ? 'bg-gray-200' : ''}
        title="Italic (Cmd+I)"
      >
        <span className="italic">I</span>
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        className={editor.isActive('heading', { level: 1 }) ? 'bg-gray-200' : ''}
        title="Heading 1"
      >
        H1
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        className={editor.isActive('heading', { level: 2 }) ? 'bg-gray-200' : ''}
        title="Heading 2"
      >
        H2
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        className={editor.isActive('bulletList') ? 'bg-gray-200' : ''}
        title="Bullet List"
      >
        •
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        className={editor.isActive('orderedList') ? 'bg-gray-200' : ''}
        title="Numbered List"
      >
        1.
      </Button>
      
      <div className="ml-auto flex items-center gap-2 text-xs text-gray-500">
        <span>Tip: Type [[  to cite documents</span>
      </div>
    </div>
  );
}
