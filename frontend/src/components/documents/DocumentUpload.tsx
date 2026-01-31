/**
 * Document Upload Component
 * 
 * Handles file uploads for documents (PDF, DOCX, TXT).
 */

'use client';

import { useState } from 'react';
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
        <button
          onClick={() => setPasteMode(false)}
          className={`px-3 py-1 rounded text-sm ${
            !pasteMode
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Upload File
        </button>
        <button
          onClick={() => setPasteMode(true)}
          className={`px-3 py-1 rounded text-sm ${
            pasteMode
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Paste Text
        </button>
      </div>

      {!pasteMode ? (
        <div>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Document title (optional)"
            className="w-full border rounded px-3 py-2 mb-3 text-sm"
          />
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileUpload(file);
            }}
            disabled={uploading}
            className="w-full text-sm"
          />
        </div>
      ) : (
        <div>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Document title (required)"
            className="w-full border rounded px-3 py-2 mb-3 text-sm"
            required
          />
          <textarea
            value={pastedText}
            onChange={(e) => setPastedText(e.target.value)}
            placeholder="Paste document content here..."
            className="w-full border rounded px-3 py-2 mb-3 text-sm h-32"
          />
          <button
            onClick={handlePaste}
            disabled={uploading || !title.trim() || !pastedText.trim()}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? 'Uploading...' : 'Upload Document'}
          </button>
        </div>
      )}

      {uploading && (
        <div className="mt-3 text-sm text-gray-600">
          Processing document... Evidence will be extracted automatically.
        </div>
      )}
    </div>
  );
}
