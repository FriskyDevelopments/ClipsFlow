export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

const MAX_CLIP_DURATION_SECONDS = 3600;

export function validateCreateClip(input: unknown): ValidationResult {
  const errors: string[] = [];

  if (typeof input !== "object" || input === null) {
    return { valid: false, errors: ["Input must be an object"] };
  }

  const data = input as Record<string, unknown>;

  if (typeof data.title !== "string" || data.title.trim() === "") {
    errors.push("title must be a non-empty string");
  }

  if (typeof data.filePath !== "string" || data.filePath.trim() === "") {
    errors.push("filePath must be a non-empty string");
  }

  if (data.tags !== undefined) {
    if (!Array.isArray(data.tags) || data.tags.some((t) => typeof t !== "string")) {
      errors.push("tags must be an array of strings");
    }
  }

  const dur = data.durationSeconds;
  if (typeof dur !== "number" || !Number.isFinite(dur) || dur <= 0) {
    errors.push("durationSeconds must be a positive finite number");
  } else if (dur > MAX_CLIP_DURATION_SECONDS) {
    errors.push(`durationSeconds must not exceed ${MAX_CLIP_DURATION_SECONDS} (got ${dur})`);
  }

  return { valid: errors.length === 0, errors };
}

export function validateUpdateClip(input: unknown): ValidationResult {
  const errors: string[] = [];

  if (typeof input !== "object" || input === null) {
    return { valid: false, errors: ["Input must be an object"] };
  }

  const data = input as Record<string, unknown>;

  if (data.title !== undefined && (typeof data.title !== "string" || data.title.trim() === "")) {
    errors.push("title must be a non-empty string");
  }

  if (data.tags !== undefined) {
    if (!Array.isArray(data.tags) || data.tags.some((t) => typeof t !== "string")) {
      errors.push("tags must be an array of strings");
    }
  }

  return { valid: errors.length === 0, errors };
}
