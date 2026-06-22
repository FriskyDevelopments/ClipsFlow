import { ClipStore } from "../store.js";
import { CommandInput, parseTags, runClipCommand } from "./commands.js";
import { toEmbeds } from "./render.js";

// Discord interaction + response type constants (raw protocol numbers).
const InteractionType = { PING: 1, APPLICATION_COMMAND: 2 } as const;
const ResponseType = { PONG: 1, CHANNEL_MESSAGE_WITH_SOURCE: 4 } as const;
const EPHEMERAL = 1 << 6; // MessageFlags.Ephemeral

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  }
  return bytes;
}

/**
 * Verify a Discord interaction request signature (Ed25519 over
 * `timestamp + rawBody`) using Web Crypto. Discord rejects an app whose
 * endpoint does not enforce this, so an invalid/missing signature is a 401.
 */
export async function verifyKey(
  rawBody: string,
  signature: string | null,
  timestamp: string | null,
  publicKey: string,
): Promise<boolean> {
  if (!signature || !timestamp) return false;
  try {
    const key = await crypto.subtle.importKey(
      "raw",
      hexToBytes(publicKey),
      { name: "Ed25519" },
      false,
      ["verify"],
    );
    const message = new TextEncoder().encode(timestamp + rawBody);
    return await crypto.subtle.verify("Ed25519", key, hexToBytes(signature), message);
  } catch {
    return false;
  }
}

interface InteractionOption {
  name: string;
  value?: string | number;
  options?: InteractionOption[];
}

/** Flatten a subcommand interaction's option list into a lookup map. */
function optionMap(options: InteractionOption[] | undefined): Map<string, string | number> {
  const map = new Map<string, string | number>();
  for (const o of options ?? []) {
    if (o.value !== undefined) map.set(o.name, o.value);
  }
  return map;
}

/** Map a Discord `/clip` application-command interaction to a CommandInput. */
function toCommandInput(data: { options?: InteractionOption[] }): CommandInput {
  const sub = data.options?.[0];
  const opts = optionMap(sub?.options);
  const str = (k: string) => (opts.has(k) ? String(opts.get(k)) : undefined);
  const int = (k: string) => (opts.has(k) ? Number(opts.get(k)) : undefined);
  return {
    subcommand: (sub?.name ?? "list") as CommandInput["subcommand"],
    title: str("title"),
    filePath: str("file_path"),
    durationSeconds: int("duration"),
    tags: parseTags(str("tags")),
    id: str("id"),
    tag: str("tag"),
    page: int("page"),
  };
}

/**
 * Handle a raw Discord HTTP interaction request and produce the JSON response.
 * This is the Workers-native replacement for the discord.js gateway client:
 * Discord POSTs interactions to the Worker, which verifies and replies inline.
 */
export async function handleInteraction(
  request: Request,
  store: ClipStore,
  publicKey: string,
): Promise<Response> {
  const rawBody = await request.text();
  const valid = await verifyKey(
    rawBody,
    request.headers.get("x-signature-ed25519"),
    request.headers.get("x-signature-timestamp"),
    publicKey,
  );
  if (!valid) return new Response("invalid request signature", { status: 401 });

  const interaction = JSON.parse(rawBody) as {
    type: number;
    data?: { name?: string; options?: InteractionOption[] };
  };

  if (interaction.type === InteractionType.PING) {
    return Response.json({ type: ResponseType.PONG });
  }

  if (
    interaction.type === InteractionType.APPLICATION_COMMAND &&
    interaction.data?.name === "clip"
  ) {
    const result = await runClipCommand(store, toCommandInput(interaction.data));
    return Response.json({
      type: ResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
      data: {
        embeds: toEmbeds(result),
        // Errors stay private to the invoker; successes are visible in-channel.
        flags: result.ok ? 0 : EPHEMERAL,
      },
    });
  }

  return new Response("unsupported interaction", { status: 400 });
}
