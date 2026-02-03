/**
 * Document Upload Component
 * 
 * Handles file uploads for documents (PDF, DOCX, TXT).
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { documentsAPI } from '@/lib/api/documents';

interface DocumentUploadProps {
  caseId: string;
  projectId: string;
  onUploaded?: (documentId: string) => void;
}

export function DocumentUpload({ caseId, projectId, onUploaded }: DocumentUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [pasteMode, setPasteMode] = useState(false);
  const [pastedText, setPastedText] = useState('');
  const [title, setTitle] = useState('');

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    try {
      // For now, read as text (full file upload would need FormData + backend changes)
      const text = await file.text();
      
      const document = await documentsAPI.create({
        title: title || file.name,
        source_type: 'text',
        content_text: text,
        project_id: projectId,
        case_id: caseId,
      });

      onUploaded?.(document.id);
      setTitle('');
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setUploading(false);
    }
  };

  const handlePaste = async () => {
    if (!pastedText.trim() || !title.trim()) {
      alert('Please provide both title and content');
      return;
    }

    setUploading(true);
    try {
      const document = await documentsAPI.create({
        title,
        source_type: 'text',
        content_text: pastedText,
        project_id: projectId,
        case_id: caseId,
      });

      onUploaded?.(document.id);
      setPastedText('');
      setTitle('');
      setPasteMode(false);
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="border rounded-lg p-4 bg-white">
      <h3 className="font-semibold mb-4">Upload Document</h3>

      <div className="flex gap-2 mb-4">
        <Button
          onClick={() => setPasteMode(false)}
          variant={!pasteMode ? 'default' : 'outline'}
          size="sm"
        >
          Upload File
        </Button>
        <Button
          onClick={() => setPasteMode(true)}
          variant={pasteMode ? 'default' : 'outline'}
          size="sm"
        >
          Paste Text
        </Button>
      </div>

      {!pasteMode ? (
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="doc-title-upload">Document Title (optional)</Label>
            <Input
              id="doc-title-upload"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter document title..."
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="doc-file">Select File</Label>
            <input
              id="doc-file"
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileUpload(file);
              }}
              disabled={uploading}
              className="w-full text-sm"
              aria-label="Select document file"
            />
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="doc-title-paste" required>Document Title</Label>
            <Input
              id="doc-title-paste"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter document title..."
              required
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="doc-content">Document Content</Label>
            <Textarea
              id="doc-content"
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder="Paste document content here..."
              rows={6}
            />
          </div>
          <Button
            onClick={handlePaste}
            disabled={uploading || !title.trim() || !pastedText.trim()}
            className="w-full"
          >
            {uploading ? 'Uploading...' : 'Upload Document'}
          </Button>
        </div>
      )}

      {uploading && (
        <div className="mt-3 text-sm text-neutral-600">
          Processing document... Evidence will be extracted automatically.
        </div>
      )}
    </div>
  );
}
