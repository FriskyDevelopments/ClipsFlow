"use client";

import { useEffect, useState } from "react";
import { getTelegramWebApp, type TelegramWebAppUser } from "../../lib/telegram";
import RunesLoading from "../../components/RunesLoading";
import ClipResultCard from "../../components/ClipResultCard";

type ClipResult = {
  title: string;
  thumbnail: string;
  duration: string;
};

export default function MiniAppPage() {
  const [user, setUser] = useState<TelegramWebAppUser | null>(null);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ClipResult | null>(null);

  useEffect(() => {
    const webApp = getTelegramWebApp();

    if (!webApp) {
      console.warn("Not inside Telegram");
      return;
    }

    webApp.ready();
    webApp.expand();

    setUser(webApp.initDataUnsafe?.user ?? null);

    console.log("TG USER:", webApp.initDataUnsafe?.user);
    console.log("INIT DATA:", webApp.initData);
  }, []);

  const handleProcess = async () => {
    if (!url) {
      return;
    }

    setLoading(true);
    setResult(null);

    await new Promise((resolve) => setTimeout(resolve, 2000));

    setResult({
      title: "Clip ready",
      thumbnail: "https://placehold.co/400x300",
      duration: "0:12",
    });

    setLoading(false);
  };

  const handleSend = () => {
    const webApp = getTelegramWebApp();
    if (!webApp?.sendData || !result) {
      return;
    }

    webApp.sendData(JSON.stringify({ clip_id: "demo-clip-123" }));
  };

  return (
    <div className="min-h-screen bg-[#11131a] text-white p-4">
      <h1 className="text-xl font-bold mb-4">ClipsFlow</h1>

      {user && (
        <div className="text-sm opacity-70 mb-4">
          @{user.username || user.first_name}
        </div>
      )}

      <input
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Paste video URL..."
        className="w-full p-3 rounded bg-[#171b26] border border-white/10 mb-3"
      />

      <button
        onClick={handleProcess}
        disabled={loading}
        className={`w-full p-3 rounded font-bold transition-all ${
          loading
            ? "bg-white/10 text-white/50 cursor-not-allowed"
            : "bg-gradient-to-r from-pink-500 to-cyan-400 text-black hover:opacity-90"
        }`}
      >
        {loading ? "Processing..." : "Process Clip"}
      </button>

      {loading && <RunesLoading />}

      {result && <ClipResultCard result={result} onSend={handleSend} />}
    </div>
  );
}
