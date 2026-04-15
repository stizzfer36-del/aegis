import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.resolve(process.cwd(), '..', '.aegis', 'memory.db');

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const page = Math.max(1, Number.parseInt(url.searchParams.get('page') ?? '1', 10));
  const topic = (url.searchParams.get('topic') ?? '').trim();
  const pageSize = 50;
  const offset = (page - 1) * pageSize;

  try {
    const db = new Database(DB_PATH, { readonly: true });
    const where = topic ? 'WHERE topic LIKE @topic' : '';
    const rows = db
      .prepare(`SELECT id, trace_id, topic, content, created_at FROM memory ${where} ORDER BY id DESC LIMIT @limit OFFSET @offset`)
      .all({ topic: `%${topic}%`, limit: pageSize, offset }) as Array<Record<string, unknown>>;
    const total = db
      .prepare(`SELECT COUNT(*) as count FROM memory ${where}`)
      .get({ topic: `%${topic}%` }) as { count: number };
    db.close();
    return Response.json({ rows, page, pageSize, total: total.count });
  } catch {
    return Response.json({ rows: [], page, pageSize, total: 0 });
  }
}
