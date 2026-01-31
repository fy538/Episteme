/**
 * Evidence types
 */

export interface Evidence {
  id: string;
  text: string;
  type: 'fact' | 'metric' | 'claim' | 'quote' | 'benchmark';
  chunk: string;
  document: string;
  document_title: string;
  chunk_preview: {
    chunk_index: number;
    text_preview: string;
    token_count: number;
    span: any;
  };
  extraction_confidence: number;
  user_credibility_rating: number | null;
  embedding: number[] | null;
  extracted_at: string;
  created_at: string;
}
