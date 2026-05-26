import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { Clip } from "./types.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, "..", "data");
const DATA_FILE = path.join(DATA_DIR, "clips.json");

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

// TODO: add pagination support — getAll() currently returns the full
// array; it should accept { page, limit } and return a slice plus
// total count so large libraries don't blow up the response payload
export function getAll(): Clip[] {
  return load();
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
