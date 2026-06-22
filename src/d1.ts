import { Clip, ClipQuery, PaginatedClips } from "./types.js";
import { ClipStore, normalizeLimit, normalizePage } from "./store.js";

/** Shape of a row in the `clips` table (snake_case, tags as a JSON string). */
interface ClipRow {
  id: string;
  title: string;
  file_path: string;
  duration_seconds: number;
  tags: string;
  created_at: string;
  updated_at: string;
}

function rowToClip(row: ClipRow): Clip {
  return {
    id: row.id,
    title: row.title,
    filePath: row.file_path,
    durationSeconds: row.duration_seconds,
    tags: JSON.parse(row.tags) as string[],
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

/**
 * Cloudflare D1 (SQLite) implementation of {@link ClipStore}. Tags are stored
 * as a JSON array in a TEXT column; tag filtering uses SQLite's `json_each`
 * so the membership test runs in the database rather than in the isolate.
 */
export class D1Store implements ClipStore {
  constructor(private readonly db: D1Database) {}

  async getAll(query: ClipQuery = {}): Promise<PaginatedClips> {
    const page = normalizePage(query.page);
    const limit = normalizeLimit(query.limit);
    const offset = (page - 1) * limit;

    const filterByTag = query.tag !== undefined && query.tag !== "";
    const where = filterByTag
      ? "WHERE EXISTS (SELECT 1 FROM json_each(clips.tags) WHERE value = ?)"
      : "";

    const countSql = `SELECT COUNT(*) AS n FROM clips ${where}`;
    const countStmt = filterByTag
      ? this.db.prepare(countSql).bind(query.tag)
      : this.db.prepare(countSql);
    const countRow = await countStmt.first<{ n: number }>();
    const total = countRow?.n ?? 0;

    const pageSql = `SELECT * FROM clips ${where} ORDER BY created_at ASC, id ASC LIMIT ? OFFSET ?`;
    const pageStmt = filterByTag
      ? this.db.prepare(pageSql).bind(query.tag, limit, offset)
      : this.db.prepare(pageSql).bind(limit, offset);
    const { results } = await pageStmt.all<ClipRow>();

    return { data: results.map(rowToClip), total, page, limit };
  }

  async getById(id: string): Promise<Clip | undefined> {
    const row = await this.db
      .prepare("SELECT * FROM clips WHERE id = ?")
      .bind(id)
      .first<ClipRow>();
    return row ? rowToClip(row) : undefined;
  }

  async insert(clip: Clip): Promise<void> {
    await this.db
      .prepare(
        `INSERT INTO clips (id, title, file_path, duration_seconds, tags, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        clip.id,
        clip.title,
        clip.filePath,
        clip.durationSeconds,
        JSON.stringify(clip.tags),
        clip.createdAt,
        clip.updatedAt,
      )
      .run();
  }

  async update(id: string, patch: Partial<Clip>): Promise<Clip | undefined> {
    // Build a partial UPDATE touching only the fields present in `patch`, so
    // we don't read-modify-write the whole row (which races concurrent edits
    // and would rewrite immutable columns). Maps camelCase fields to columns.
    const columns: Record<string, (c: Partial<Clip>) => string | number> = {
      title: (c) => c.title!,
      filePath: (c) => c.filePath!,
      durationSeconds: (c) => c.durationSeconds!,
      tags: (c) => JSON.stringify(c.tags),
      createdAt: (c) => c.createdAt!,
      updatedAt: (c) => c.updatedAt!,
    };
    const colNames: Record<string, string> = {
      title: "title",
      filePath: "file_path",
      durationSeconds: "duration_seconds",
      tags: "tags",
      createdAt: "created_at",
      updatedAt: "updated_at",
    };

    const setClauses: string[] = [];
    const values: (string | number)[] = [];
    for (const key of Object.keys(columns)) {
      if (patch[key as keyof Clip] !== undefined) {
        setClauses.push(`${colNames[key]} = ?`);
        values.push(columns[key](patch));
      }
    }
    if (setClauses.length === 0) return this.getById(id);

    const res = await this.db
      .prepare(`UPDATE clips SET ${setClauses.join(", ")} WHERE id = ?`)
      .bind(...values, id)
      .run();
    if ((res.meta?.changes ?? 0) === 0) return undefined;
    return this.getById(id);
  }

  async remove(id: string): Promise<boolean> {
    const res = await this.db.prepare("DELETE FROM clips WHERE id = ?").bind(id).run();
    // D1 reports affected rows via meta.changes.
    return (res.meta?.changes ?? 0) > 0;
  }
}
