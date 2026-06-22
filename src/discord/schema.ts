import { SlashCommandBuilder } from "discord.js";

// Slash command surface: a single `/clip` command with subcommands that
// mirror the REST API (add / list / get / update / delete).
//
// This is the only module that depends on discord.js. It is used by the
// registration script (`npm run bot:register`, run under Node) and is NOT
// imported by the Worker, which speaks the raw HTTP Interactions protocol.
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
