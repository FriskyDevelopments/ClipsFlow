import { v4 as uuidv4 } from "uuid";
import * as store from "./store.js";
import { validateCreateClip, validateUpdateClip } from "./validators.js";
import { Clip, ClipQuery, PaginatedClips } from "./types.js";

export class ValidationError extends Error {
  constructor(public readonly errors: string[]) {
    super(errors.join("; "));
    this.name = "ValidationError";
  }
}

export function createClip(input: unknown): Clip {
  const result = validateCreateClip(input);
  if (!result.valid) throw new ValidationError(result.errors);

  const data = input as { title: string; filePath: string; durationSeconds: number; tags?: string[] };
  const now = new Date().toISOString();
  const clip: Clip = {
    id: uuidv4(),
    title: data.title.trim(),
    filePath: data.filePath.trim(),
    durationSeconds: data.durationSeconds,
    tags: data.tags ?? [],
    createdAt: now,
    updatedAt: now,
  };
  store.insert(clip);
  return clip;
}

export function listClips(query: ClipQuery = {}): PaginatedClips {
  return store.getAll(query);
}

export function getClip(id: string): Clip | undefined {
  return store.getById(id);
}

export function updateClip(id: string, input: unknown): Clip {
  const result = validateUpdateClip(input);
  if (!result.valid) throw new ValidationError(result.errors);

  const data = input as { title?: string; tags?: string[] };
  const patch: Partial<Clip> = { updatedAt: new Date().toISOString() };
  if (data.title !== undefined) patch.title = data.title.trim();
  if (data.tags !== undefined) patch.tags = data.tags;

  const updated = store.update(id, patch);
  if (!updated) throw new Error(`Clip ${id} not found`);
  return updated;
}

export function deleteClip(id: string): void {
  const deleted = store.remove(id);
  if (!deleted) throw new Error(`Clip ${id} not found`);
}
