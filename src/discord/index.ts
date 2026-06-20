import {
  ChatInputCommandInteraction,
  Client,
  GatewayIntentBits,
  MessageFlags,
} from "discord.js";
import { runClipCommand, CommandInput } from "./commands.js";
import { toEmbeds } from "./render.js";
import { parseTags } from "./commands.js";

/** Map a Discord chat-input interaction to the pure command input. */
function toCommandInput(interaction: ChatInputCommandInteraction): CommandInput {
  const sub = interaction.options.getSubcommand() as CommandInput["subcommand"];
  return {
    subcommand: sub,
    title: interaction.options.getString("title") ?? undefined,
    filePath: interaction.options.getString("file_path") ?? undefined,
    durationSeconds: interaction.options.getInteger("duration") ?? undefined,
    tags: parseTags(interaction.options.getString("tags")),
    id: interaction.options.getString("id") ?? undefined,
    tag: interaction.options.getString("tag") ?? undefined,
    page: interaction.options.getInteger("page") ?? undefined,
  };
}

export function createBot(): Client {
  // Only the Guilds intent is needed for slash commands — no privileged
  // Message Content intent required.
  const client = new Client({ intents: [GatewayIntentBits.Guilds] });

  client.once("clientReady", (c) => {
    console.log(`ClipsFlow Discord bot logged in as ${c.user.tag}`);
  });

  client.on("interactionCreate", async (interaction) => {
    if (!interaction.isChatInputCommand() || interaction.commandName !== "clip") return;
    const result = runClipCommand(toCommandInput(interaction));
    await interaction.reply({
      embeds: toEmbeds(result),
      // Errors stay private to the invoker; successes are visible to the channel.
      flags: result.ok ? undefined : MessageFlags.Ephemeral,
    });
  });

  return client;
}

// Boot the bot when run directly (not when imported by tests).
if (process.env.NODE_ENV !== "test") {
  const token = process.env.DISCORD_BOT_TOKEN;
  if (!token) {
    console.error("DISCORD_BOT_TOKEN is required to start the Discord bot.");
    process.exit(1);
  }
  const client = createBot();
  void client.login(token);

  const shutdown = () => {
    console.log("Shutting down Discord bot...");
    void client.destroy();
    process.exit(0);
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}
