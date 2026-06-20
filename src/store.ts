import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { Clip, ClipQuery, PaginatedClips } from "./types.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Location is overridable so deployments can point at a mounted volume
// and tests can use an isolated temp directory.
const DATA_DIR = process.env.CLIPS_DATA_DIR ?? path.join(__dirname, "..", "data");
const DATA_FILE = path.join(DATA_DIR, "clips.json");

export const DEFAULT_PAGE_LIMIT = 20;
export const MAX_PAGE_LIMIT = 100;

function ensureDataDir(): void {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
}

export function load(): Clip[] {
  ensureDataDir();
  if (!fs.existsSync(DATA_FILE)) {
    return [];
  }
  const raw = fs.readFileSync(DATA_FILE, "utf-8");
  return JSON.parse(raw) as Clip[];
}

function save(clips: Clip[]): void {
  ensureDataDir();
  fs.writeFileSync(DATA_FILE, JSON.stringify(clips, null, 2), "utf-8");
}

// Single query path for the collection: optional tag filtering followed by
// pagination. Returns a bounded slice plus the total matched count so large
// libraries don't blow up the response payload.
export function getAll(query: ClipQuery = {}): PaginatedClips {
  let clips = load();

  if (query.tag !== undefined && query.tag !== "") {
    const tag = query.tag;
    clips = clips.filter((c) => c.tags.includes(tag));
  }

  const total = clips.length;
  const page = normalizePage(query.page);
  const limit = normalizeLimit(query.limit);
  const start = (page - 1) * limit;
  const data = clips.slice(start, start + limit);

  return { data, total, page, limit };
}

function normalizePage(page: number | undefined): number {
  if (page === undefined || !Number.isFinite(page) || page < 1) return 1;
  return Math.floor(page);
}

function normalizeLimit(limit: number | undefined): number {
  if (limit === undefined || !Number.isFinite(limit) || limit < 1) {
    return DEFAULT_PAGE_LIMIT;
  }
  return Math.min(Math.floor(limit), MAX_PAGE_LIMIT);
}

export function getById(id: string): Clip | undefined {
  return load().find((c) => c.id === id);
}

export function insert(clip: Clip): void {
  const clips = load();
  clips.push(clip);
  save(clips);
}

export function update(id: string, patch: Partial<Clip>): Clip | undefined {
  const clips = load();
  const idx = clips.findIndex((c) => c.id === id);
  if (idx === -1) return undefined;
  clips[idx] = { ...clips[idx], ...patch };
  save(clips);
  return clips[idx];
}

export function remove(id: string): boolean {
  const clips = load();
  const next = clips.filter((c) => c.id !== id);
  if (next.length === clips.length) return false;
  save(next);
  return true;
}
