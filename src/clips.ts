import { validateCreateClip, validateUpdateClip } from "./validators.js";
import { ClipStore } from "./store.js";
import { Clip, ClipQuery, PaginatedClips } from "./types.js";

export class ValidationError extends Error {
  constructor(public readonly errors: string[]) {
    super(errors.join("; "));
    this.name = "ValidationError";
  }
}

export async function createClip(store: ClipStore, input: unknown): Promise<Clip> {
  const result = validateCreateClip(input);
  if (!result.valid) throw new ValidationError(result.errors);

  const data = input as { title: string; filePath: string; durationSeconds: number; tags?: string[] };
  const now = new Date().toISOString();
  const clip: Clip = {
    id: crypto.randomUUID(),
    title: data.title.trim(),
    filePath: data.filePath.trim(),
    durationSeconds: data.durationSeconds,
    tags: data.tags ?? [],
    createdAt: now,
    updatedAt: now,
  };
  await store.insert(clip);
  return clip;
}

export function listClips(store: ClipStore, query: ClipQuery = {}): Promise<PaginatedClips> {
  return store.getAll(query);
}

export function getClip(store: ClipStore, id: string): Promise<Clip | undefined> {
  return store.getById(id);
}

export async function updateClip(store: ClipStore, id: string, input: unknown): Promise<Clip> {
  const result = validateUpdateClip(input);
  if (!result.valid) throw new ValidationError(result.errors);

  const data = input as { title?: string; tags?: string[] };
  const patch: Partial<Clip> = { updatedAt: new Date().toISOString() };
  if (data.title !== undefined) patch.title = data.title.trim();
  if (data.tags !== undefined) patch.tags = data.tags;

  const updated = await store.update(id, patch);
  if (!updated) throw new Error(`Clip ${id} not found`);
  return updated;
}

export async function deleteClip(store: ClipStore, id: string): Promise<void> {
  const deleted = await store.remove(id);
  if (!deleted) throw new Error(`Clip ${id} not found`);
}
