import { Clip, ClipQuery, PaginatedClips } from "./types.js";

export const DEFAULT_PAGE_LIMIT = 20;
export const MAX_PAGE_LIMIT = 100;

/**
 * Transport- and backend-neutral persistence contract for clips. The HTTP API
 * and the Discord interactions handler both operate against this interface, so
 * the runtime can swap an in-memory store (tests, local dev) for a D1-backed
 * store (Cloudflare Workers) without touching the core logic.
 *
 * All methods are async: D1 is async, and awaiting a synchronous in-memory
 * implementation is a no-op, so a single async core serves both backends.
 */
export interface ClipStore {
  getAll(query?: ClipQuery): Promise<PaginatedClips>;
  getById(id: string): Promise<Clip | undefined>;
  insert(clip: Clip): Promise<void>;
  update(id: string, patch: Partial<Clip>): Promise<Clip | undefined>;
  remove(id: string): Promise<boolean>;
}

export function normalizePage(page: number | undefined): number {
  if (page === undefined || !Number.isFinite(page) || page < 1) return 1;
  return Math.floor(page);
}

export function normalizeLimit(limit: number | undefined): number {
  if (limit === undefined || !Number.isFinite(limit) || limit < 1) {
    return DEFAULT_PAGE_LIMIT;
  }
  return Math.min(Math.floor(limit), MAX_PAGE_LIMIT);
}

/**
 * In-memory clip store. Used by the test suite and `wrangler dev` fallbacks.
 * Not durable across isolates/restarts — production uses {@link D1Store}.
 */
export class MemoryStore implements ClipStore {
  private clips: Clip[] = [];

  // Copy on the way in and out so callers can't mutate persisted state through
  // a returned reference — matching D1Store, which materializes fresh objects.
  private clone(clip: Clip): Clip {
    return { ...clip, tags: [...clip.tags] };
  }

  async getAll(query: ClipQuery = {}): Promise<PaginatedClips> {
    let clips = this.clips;

    if (query.tag !== undefined && query.tag !== "") {
      const tag = query.tag;
      clips = clips.filter((c) => c.tags.includes(tag));
    }

    const total = clips.length;
    const page = normalizePage(query.page);
    const limit = normalizeLimit(query.limit);
    const start = (page - 1) * limit;
    const data = clips.slice(start, start + limit).map((c) => this.clone(c));

    return { data, total, page, limit };
  }

  async getById(id: string): Promise<Clip | undefined> {
    const found = this.clips.find((c) => c.id === id);
    return found ? this.clone(found) : undefined;
  }

  async insert(clip: Clip): Promise<void> {
    this.clips.push(this.clone(clip));
  }

  async update(id: string, patch: Partial<Clip>): Promise<Clip | undefined> {
    const idx = this.clips.findIndex((c) => c.id === id);
    if (idx === -1) return undefined;
    // Clone via the merged object so a caller-owned patch.tags array can't
    // alias persisted state after the call returns.
    this.clips[idx] = this.clone({ ...this.clips[idx], ...patch });
    return this.clone(this.clips[idx]);
  }

  async remove(id: string): Promise<boolean> {
    const next = this.clips.filter((c) => c.id !== id);
    if (next.length === this.clips.length) return false;
    this.clips = next;
    return true;
  }
}
