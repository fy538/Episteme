/**
 * Shared SSE (Server-Sent Events) stream parser.
 *
 * Handles ReadableStream → TextDecoder → buffer accumulation →
 * split on double-newline → event/data line parsing.
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type SSEEventData = Record<string, any>;

export interface SSEEvent {
  event: string;
  data: SSEEventData;
}

/**
 * Parse an SSE stream from a fetch Response body.
 *
 * @param body - ReadableStream<Uint8Array> from Response.body
 * @param onEvent - Callback invoked for each parsed SSE event.
 *   `data` is JSON-parsed when possible, otherwise the raw string.
 * @returns A promise that resolves when the stream is fully consumed.
 */
export async function parseSSEStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: SSEEvent) => void,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split('\n\n');
    buffer = events.pop() || '';

    for (const raw of events) {
      if (!raw.trim()) continue;

      const lines = raw.split('\n');
      let eventType = 'message';
      let dataPayload = '';

      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.replace('event:', '').trim();
        } else if (line.startsWith('data:')) {
          dataPayload += line.replace('data:', '').trim();
        }
      }

      if (!dataPayload) continue;
      try {
        onEvent({ event: eventType, data: JSON.parse(dataPayload) });
      } catch {
        // Non-JSON payload — wrap in object to satisfy SSEEventData shape
        onEvent({ event: eventType, data: { raw: dataPayload } });
      }
    }
  }
}
