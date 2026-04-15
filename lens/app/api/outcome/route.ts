import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.resolve(process.cwd(), '..', '.aegis', 'outcomes.db');

export async function GET(): Promise<Response> {
  try {
    const db = new Database(DB_PATH, { readonly: true });
    const rows = db
      .prepare(
        `SELECT id, trace_id, agent, action_type, expected, actual, deviation, resolved, created_at
         FROM outcomes ORDER BY created_at DESC LIMIT 100`
      )
      .all() as Array<Record<string, unknown>>;
    db.close();
    return Response.json(rows);
  } catch {
    return Response.json([]);
  }
}
