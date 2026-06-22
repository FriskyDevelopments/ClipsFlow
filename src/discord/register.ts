import { REST, Routes } from "discord.js";
import { clipCommand } from "./schema.js";

// Registers the /clip slash command with Discord.
//   - Set DISCORD_GUILD_ID for instant, guild-scoped registration (dev).
//   - Omit it to register globally (can take up to ~1h to propagate).
async function main(): Promise<void> {
  const token = process.env.DISCORD_BOT_TOKEN;
  const clientId = process.env.DISCORD_CLIENT_ID;
  const guildId = process.env.DISCORD_GUILD_ID;

  if (!token || !clientId) {
    console.error("DISCORD_BOT_TOKEN and DISCORD_CLIENT_ID are required.");
    process.exit(1);
  }

  const rest = new REST({ version: "10" }).setToken(token);
  const body = [clipCommand.toJSON()];

  if (guildId) {
    await rest.put(Routes.applicationGuildCommands(clientId, guildId), { body });
    console.log(`Registered /clip to guild ${guildId}.`);
  } else {
    await rest.put(Routes.applicationCommands(clientId), { body });
    console.log("Registered /clip globally.");
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
