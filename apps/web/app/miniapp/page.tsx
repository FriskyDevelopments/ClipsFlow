"use client";

import { useEffect, useMemo, useState } from "react";
import { getTelegramWebApp, type TelegramWebAppUser } from "../../lib/telegram";
import RunesLoading from "../../components/RunesLoading";

type DeskState = "idle" | "handoff" | "sent" | "preview";

const deskCopy: Record<DeskState, { title: string; detail: string }> = {
  idle: {
    title: "Private clipping desk",
    detail: "Paste a public video link and the bot will return the finished export in Telegram.",
  },
  handoff: {
    title: "Handing link to Telegram",
    detail: "Keep the chat nearby. Delivery status continues in the bot until the file is actually sent.",
  },
  sent: {
    title: "Request received",
    detail: "Your export is now moving through the bot pipeline. Free exports carry the ClipFLOW watermark.",
  },
  preview: {
    title: "Telegram bridge preview",
    detail: "Open this page from the bot to send real clip requests.",
  },
};

export default function MiniAppPage() {
  const [user, setUser] = useState<TelegramWebAppUser | null>(null);
  const [url, setUrl] = useState("");
  const [deskState, setDeskState] = useState<DeskState>("idle");
  const [notice, setNotice] = useState<string | null>(null);

  const trimmedUrl = url.trim();
  const currentCopy = deskCopy[deskState];
  const userLabel = useMemo(() => {
    if (!user) return "guest session";
    return user.username ? `@${user.username}` : user.first_name;
  }, [user]);

  useEffect(() => {
    const webApp = getTelegramWebApp();

    if (!webApp) {
      return;
    }

    webApp.ready();
    webApp.expand();
    setUser(webApp.initDataUnsafe?.user ?? null);
  }, []);

  const handleProcess = async () => {
    if (!trimmedUrl) {
      setNotice("Paste a video URL first.");
      return;
    }

    setDeskState("handoff");
    setNotice(null);

    const webApp = getTelegramWebApp();
    if (webApp?.sendData) {
      webApp.sendData(
        JSON.stringify({
          action: "process_clip",
          url: trimmedUrl,
          source: "clipsflow-miniapp",
        }),
      );
      webApp.HapticFeedback?.impactOccurred("soft");
      setDeskState("sent");
      return;
    }

    await new Promise((resolve) => setTimeout(resolve, 650));
    setDeskState("preview");
  };

  return (
    <main className="min-h-screen overflow-hidden bg-[#0d1016] text-[#f7f4ec]">
      <section className="mx-auto flex min-h-screen w-full max-w-md flex-col px-5 py-5">
        <header className="flex items-center justify-between text-[11px] uppercase tracking-[0.16em] text-[#a9b4af]">
          <span>ClipsFlow</span>
          <span>{userLabel}</span>
        </header>

        <div className="flex flex-1 flex-col justify-center gap-7 py-8">
          <div className="space-y-3">
            <h1 className="max-w-[11ch] text-5xl font-semibold leading-[0.95] text-[#fffaf0]">
              {currentCopy.title}
            </h1>
            <p className="max-w-sm text-[15px] leading-6 text-[#b9c3bd]">{currentCopy.detail}</p>
          </div>

          <RunesLoading active={deskState === "handoff"} state={deskState} />

          <div className="space-y-3">
            <label className="block text-[11px] uppercase tracking-[0.16em] text-[#8d9895]" htmlFor="clip-url">
              Video link
            </label>
            <input
              id="clip-url"
              value={url}
              onChange={(event) => {
                setUrl(event.target.value);
                if (deskState !== "idle") setDeskState("idle");
              }}
              placeholder="https://..."
              className="w-full rounded-md border border-[#2b3435] bg-[#111822] px-4 py-4 text-[15px] text-[#fffaf0] outline-none transition focus:border-[#d6ef7d] focus:ring-2 focus:ring-[#d6ef7d]/15"
            />
            <button
              onClick={handleProcess}
              disabled={deskState === "handoff"}
              className="w-full rounded-md bg-[#d6ef7d] px-4 py-4 text-[14px] font-semibold text-[#12160f] transition hover:bg-[#e4ff8a] disabled:cursor-wait disabled:bg-[#2f3a33] disabled:text-[#8c978f]"
            >
              {deskState === "handoff" ? "Preparing handoff" : "Send to Telegram"}
            </button>
          </div>

          {notice && (
            <p className="rounded-md border border-[#463934] bg-[#1b1515] px-4 py-3 text-sm text-[#f3c7b5]">
              {notice}
            </p>
          )}
        </div>

        <footer className="grid grid-cols-3 gap-2 border-t border-[#222b2c] pt-4 text-[11px] text-[#8d9895]">
          <span>Watermarked trial</span>
          <span className="text-center">Clean Pro later</span>
          <span className="text-right">Telegram delivery</span>
        </footer>
      </section>
    </main>
  );
}
