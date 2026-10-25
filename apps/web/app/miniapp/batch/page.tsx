"use client";

import { useEffect, useMemo, useState } from "react";
import { getTelegramWebApp } from "../../../lib/telegram";

// Telegram limits WebApp.sendData payloads to 4096 bytes.
const MAX_PAYLOAD_BYTES = 4096;
const MAX_URLS = 50;
// Mirrors services/batch_agent.py BLOCKED_HOST_SUFFIXES. The bot re-checks server-side.
const BLOCKED_HOSTS = [
  "spotify.com",
  "spotify.link",
  "music.apple.com",
  "itunes.apple.com",
  "soundcloud.com",
  "deezer.com",
  "tidal.com",
  "music.amazon.com",
  "music.youtube.com",
];

type State = "idle" | "sent" | "preview";

function hostOf(raw: string): string | null {
  try {
    const u = new URL(/^https?:\/\//i.test(raw) ? raw : `https://${raw}`);
    return u.hostname.toLowerCase();
  } catch {
    return null;
  }
}

function isBlocked(host: string): boolean {
  return BLOCKED_HOSTS.some((s) => host === s || host.endsWith(`.${s}`));
}

export default function BatchMiniAppPage() {
  const [text, setText] = useState("");
  const [state, setState] = useState<State>("idle");
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const webApp = getTelegramWebApp();
    webApp?.ready();
    webApp?.expand();
  }, []);

  const parsed = useMemo(() => {
    const tokens = Array.from(new Set(text.split(/[\s,]+/).map((t) => t.trim()).filter(Boolean)));
    const urls: string[] = [];
    const rejected: string[] = [];
    for (const t of tokens) {
      const host = hostOf(t);
      if (!host || isBlocked(host)) rejected.push(t);
      else urls.push(t);
    }
    return { urls, rejected };
  }, [text]);

  const payload = JSON.stringify({ action: "batch_download", urls: parsed.urls, source: "clipsflow-miniapp-batch" });
  const payloadBytes = new TextEncoder().encode(payload).length;
  const tooBig = payloadBytes > MAX_PAYLOAD_BYTES || parsed.urls.length > MAX_URLS;

  const submit = () => {
    if (parsed.urls.length === 0) {
      setNotice("Paste at least one supported link (one per line).");
      return;
    }
    if (tooBig) {
      setNotice(`Too many links for one batch (max ${MAX_URLS}, ${MAX_PAYLOAD_BYTES} bytes). Split it.`);
      return;
    }
    const webApp = getTelegramWebApp();
    if (webApp?.sendData) {
      webApp.sendData(payload);
      setState("sent");
      return;
    }
    setState("preview");
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col gap-4 p-6">
      <h1 className="text-2xl font-semibold">Batch downloads</h1>
      <p className="text-sm opacity-80">
        Paste public video links (one per line). Each link runs through the normal ClipsFlow pipeline, one at a
        time. Only providers on the admin allowlist are accepted. Music-streaming services (Spotify, Apple Music,
        SoundCloud, …) are not supported.
      </p>
      <textarea
        aria-label="Links"
        className="min-h-48 rounded-md border p-3 font-mono text-sm text-black"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={"https://youtu.be/...\nhttps://www.tiktok.com/@user/video/..."}
      />
      <div className="text-sm">
        {parsed.urls.length} link(s) ready · {payloadBytes}/{MAX_PAYLOAD_BYTES} bytes
        {parsed.rejected.length > 0 && <div className="text-red-500">Skipped: {parsed.rejected.join(", ")}</div>}
      </div>
      <button className="rounded-md bg-white px-4 py-2 font-medium text-black disabled:opacity-50" onClick={submit} disabled={tooBig}>
        Send batch to bot
      </button>
      {state === "sent" && <p>Batch sent. Progress continues in the bot chat (/batch status).</p>}
      {state === "preview" && <p>Preview mode: open this page from the bot to send real batches.</p>}
      {notice && <p className="text-amber-400">{notice}</p>}
    </main>
  );
}
