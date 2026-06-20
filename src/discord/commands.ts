import { SlashCommandBuilder } from "discord.js";
import * as clips from "../clips.js";
import { ValidationError } from "../clips.js";
import { Clip, PaginatedClips } from "../types.js";

// Slash command surface: a single `/clip` command with subcommands that
// mirror the REST API (add / list / get / update / delete).
export const clipCommand = new SlashCommandBuilder()
  .setName("clip")
  .setDescription("Manage video clips")
  .addSubcommand((s) =>
    s
      .setName("add")
      .setDescription("Create a new clip")
      .addStringOption((o) => o.setName("title").setDescription("Clip title").setRequired(true))
      .addStringOption((o) => o.setName("file_path").setDescription("Path to the clip file").setRequired(true))
      .addIntegerOption((o) =>
        o.setName("duration").setDescription("Duration in seconds (1–3600)").setRequired(true),
      )
      .addStringOption((o) => o.setName("tags").setDescription("Comma-separated tags").setRequired(false)),
  )
  .addSubcommand((s) =>
    s
      .setName("list")
      .setDescription("List clips")
      .addStringOption((o) => o.setName("tag").setDescription("Filter by tag").setRequired(false))
      .addIntegerOption((o) => o.setName("page").setDescription("Page number (default 1)").setRequired(false)),
  )
  .addSubcommand((s) =>
    s
      .setName("get")
      .setDescription("Show one clip")
      .addStringOption((o) => o.setName("id").setDescription("Clip id").setRequired(true)),
  )
  .addSubcommand((s) =>
    s
      .setName("update")
      .setDescription("Update a clip's title and/or tags")
      .addStringOption((o) => o.setName("id").setDescription("Clip id").setRequired(true))
      .addStringOption((o) => o.setName("title").setDescription("New title").setRequired(false))
      .addStringOption((o) => o.setName("tags").setDescription("New comma-separated tags").setRequired(false)),
  )
  .addSubcommand((s) =>
    s
      .setName("delete")
      .setDescription("Delete a clip")
      .addStringOption((o) => o.setName("id").setDescription("Clip id").setRequired(true)),
  );

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
 * be unit-tested without a gateway connection.
 */
export function runClipCommand(input: CommandInput): CommandResult {
  try {
    switch (input.subcommand) {
      case "add": {
        const clip = clips.createClip({
          title: input.title,
          filePath: input.filePath,
          durationSeconds: input.durationSeconds,
          tags: input.tags,
        });
        return { ok: true, message: `Created clip \`${clip.id}\``, clip };
      }
      case "list": {
        const result = clips.listClips({ tag: input.tag, page: input.page });
        const scope = input.tag ? ` tagged \`${input.tag}\`` : "";
        return {
          ok: true,
          message: `${result.total} clip(s)${scope} — page ${result.page}`,
          clips: result,
        };
      }
      case "get": {
        const clip = clips.getClip(input.id as string);
        if (!clip) return { ok: false, message: `Clip \`${input.id}\` not found` };
        return { ok: true, message: clip.title, clip };
      }
      case "update": {
        const clip = clips.updateClip(input.id as string, {
          title: input.title,
          tags: input.tags,
        });
        return { ok: true, message: `Updated clip \`${clip.id}\``, clip };
      }
      case "delete": {
        clips.deleteClip(input.id as string);
        return { ok: true, message: `Deleted clip \`${input.id}\`` };
      }
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
