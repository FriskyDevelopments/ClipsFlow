import { Clip } from "../types.js";
import { CommandResult } from "./commands.js";

const OK_COLOR = 0x2ecc71;
const ERR_COLOR = 0xe74c3c;

/**
 * Minimal Discord embed JSON shape. We emit raw embed objects (not discord.js
 * `EmbedBuilder` instances) so this module is dependency-free and bundles into
 * the Cloudflare Worker, which returns interaction responses as plain JSON.
 */
export interface Embed {
  color?: number;
  title?: string;
  description?: string;
  fields?: { name: string; value: string; inline?: boolean }[];
  footer?: { text: string };
}

function clipFields(clip: Clip) {
  return [
    { name: "id", value: `\`${clip.id}\``, inline: false },
    { name: "duration", value: `${clip.durationSeconds}s`, inline: true },
    { name: "tags", value: clip.tags.length ? clip.tags.join(", ") : "—", inline: true },
    { name: "file", value: `\`${clip.filePath}\``, inline: false },
  ];
}

/** Convert a transport-neutral CommandResult into a Discord embed payload. */
export function toEmbeds(result: CommandResult): Embed[] {
  if (!result.ok) {
    return [{ color: ERR_COLOR, description: `❌ ${result.message}` }];
  }

  if (result.clip) {
    return [{ color: OK_COLOR, title: result.clip.title, fields: clipFields(result.clip) }];
  }

  if (result.clips) {
    const { data, total, page, limit } = result.clips;
    if (data.length === 0) {
      return [{ color: OK_COLOR, title: result.message, description: "No clips found." }];
    }
    return [
      {
        color: OK_COLOR,
        title: result.message,
        description: data
          .map((c) => `• \`${c.id}\` — **${c.title}** (${c.durationSeconds}s)`)
          .join("\n"),
        footer: { text: `page ${page} · ${limit}/page · ${total} total` },
      },
    ];
  }

  return [{ color: OK_COLOR, title: result.message }];
}
