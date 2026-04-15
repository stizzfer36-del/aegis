import { promises as fs } from 'fs';
import path from 'path';

const EVENTS_PATH = path.resolve(process.cwd(), '..', '.aegis', 'events.jsonl');

function parseSafe(line: string): unknown | null {
  try {
    return JSON.parse(line);
  } catch {
    return null;
  }
}

export async function GET(): Promise<Response> {
  const encoder = new TextEncoder();
  let offset = 0;

  const stream = new ReadableStream<Uint8Array>({
    async start(controller): Promise<void> {
      const sendLine = (line: string): void => {
        const parsed = parseSafe(line);
        if (parsed !== null) {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(parsed)}\n\n`));
        }
      };

      const ping = setInterval(() => {
        controller.enqueue(encoder.encode(': ping\n\n'));
      }, 15000);

      const poll = setInterval(async () => {
        try {
          const file = await fs.readFile(EVENTS_PATH, 'utf-8');
          const chunk = file.slice(offset);
          offset = file.length;
          for (const line of chunk.split('\n')) {
            if (line.trim()) {
              sendLine(line);
            }
          }
        } catch {
          // keep stream alive even if file does not exist yet
        }
      }, 1000);

      try {
        const initial = await fs.readFile(EVENTS_PATH, 'utf-8');
        offset = initial.length;
        for (const line of initial.split('\n').slice(-200)) {
          if (line.trim()) {
            sendLine(line);
          }
        }
      } catch {
        offset = 0;
      }

      const close = (): void => {
        clearInterval(ping);
        clearInterval(poll);
      };

      // @ts-expect-error non-standard on server runtime; guarded fallback
      controller.signal?.addEventListener?.('abort', close);
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
    },
  });
}
