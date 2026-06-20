import { EmbedBuilder } from "discord.js";
import { Clip } from "../types.js";
import { CommandResult } from "./commands.js";

const OK_COLOR = 0x2ecc71;
const ERR_COLOR = 0xe74c3c;

function clipFields(clip: Clip) {
  return [
    { name: "id", value: `\`${clip.id}\``, inline: false },
    { name: "duration", value: `${clip.durationSeconds}s`, inline: true },
    { name: "tags", value: clip.tags.length ? clip.tags.join(", ") : "—", inline: true },
    { name: "file", value: `\`${clip.filePath}\``, inline: false },
  ];
}

/** Convert a transport-neutral CommandResult into a Discord embed payload. */
export function toEmbeds(result: CommandResult): EmbedBuilder[] {
  if (!result.ok) {
    return [new EmbedBuilder().setColor(ERR_COLOR).setDescription(`❌ ${result.message}`)];
  }

  const embed = new EmbedBuilder().setColor(OK_COLOR).setTitle(result.message);

  if (result.clip) {
    embed.setTitle(result.clip.title).addFields(clipFields(result.clip));
  } else if (result.clips) {
    const { data, total, page, limit } = result.clips;
    embed.setTitle(result.message);
    if (data.length === 0) {
      embed.setDescription("No clips found.");
    } else {
      embed.setDescription(
        data.map((c) => `• \`${c.id}\` — **${c.title}** (${c.durationSeconds}s)`).join("\n"),
      );
      embed.setFooter({ text: `page ${page} · ${limit}/page · ${total} total` });
    }
  }

  return [embed];
}
