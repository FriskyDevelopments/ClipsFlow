import * as clips from "../clips.js";
import { ValidationError } from "../clips.js";
import { ClipStore } from "../store.js";
import { Clip, PaginatedClips } from "../types.js";

export interface CommandInput {
  subcommand: "add" | "list" | "get" | "update" | "delete";
  title?: string;
  filePath?: string;
  durationSeconds?: number;
  tags?: string[];
  id?: string;
  tag?: string;
  page?: number;
}

export interface CommandResult {
  ok: boolean;
  message: string;
  clip?: Clip;
  clips?: PaginatedClips;
}

/** Parse a comma-separated tags string into a trimmed, non-empty array. */
export function parseTags(raw: string | null | undefined): string[] | undefined {
  if (raw == null) return undefined;
  const tags = raw
    .split(",")
    .map((t) => t.trim())
    .filter((t) => t.length > 0);
  return tags;
}

/**
 * Pure command handler: maps a normalized input to the shared clip core and
 * returns a transport-neutral result. Kept free of discord.js types so it can
 * be unit-tested and bundled into the Worker without a gateway connection.
 */
export async function runClipCommand(
  store: ClipStore,
  input: CommandInput,
): Promise<CommandResult> {
  try {
    // get/update/delete require an id; guard so we never assert undefined
    // through to the store (e.g. if reused outside Discord's required-param check).
    if (["get", "update", "delete"].includes(input.subcommand) && !input.id) {
      return { ok: false, message: "Missing clip id" };
    }
    switch (input.subcommand) {
      case "add": {
        const clip = await clips.createClip(store, {
          title: input.title,
          filePath: input.filePath,
          durationSeconds: input.durationSeconds,
          tags: input.tags,
        });
        return { ok: true, message: `Created clip \`${clip.id}\``, clip };
      }
      case "list": {
        const result = await clips.listClips(store, { tag: input.tag, page: input.page });
        const scope = input.tag ? ` tagged \`${input.tag}\`` : "";
        return {
          ok: true,
          message: `${result.total} clip(s)${scope} — page ${result.page}`,
          clips: result,
        };
      }
      case "get": {
        const clip = await clips.getClip(store, input.id as string);
        if (!clip) return { ok: false, message: `Clip \`${input.id}\` not found` };
        return { ok: true, message: clip.title, clip };
      }
      case "update": {
        const clip = await clips.updateClip(store, input.id as string, {
          title: input.title,
          tags: input.tags,
        });
        return { ok: true, message: `Updated clip \`${clip.id}\``, clip };
      }
      case "delete": {
        await clips.deleteClip(store, input.id as string);
        return { ok: true, message: `Deleted clip \`${input.id}\`` };
      }
      default:
        return { ok: false, message: `Unknown subcommand \`${input.subcommand}\`` };
    }
  } catch (err) {
    if (err instanceof ValidationError) {
      return { ok: false, message: `Validation failed: ${err.errors.join("; ")}` };
    }
    if (err instanceof Error && err.message.includes("not found")) {
      return { ok: false, message: err.message };
    }
    return { ok: false, message: "Internal error" };
  }
}
