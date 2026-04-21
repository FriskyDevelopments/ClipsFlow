"use client";

import { useEffect, useState } from "react";
import { getTelegramWebApp, type TelegramWebAppUser } from "../../lib/telegram";
import { motion, AnimatePresence } from "framer-motion";

export default function StixMiniApp() {
  const [user, setUser] = useState<TelegramWebAppUser | null>(null);
  const [prompt, setPrompt] = useState("");
  const [phase, setPhase] = useState<"idle" | "charging" | "synthesis">("idle");
  const [chargingText, setChargingText] = useState("");
  const [triad, setTriad] = useState<{ A: string; B: string; C: string } | null>(null);

  useEffect(() => {
    const webApp = getTelegramWebApp();
    if (!webApp) return;

    webApp.ready();
    webApp.expand();
    
    // Set theme colors to match Cyber-Occult aesthetic
    webApp.setHeaderColor("#070B14");
    webApp.setBackgroundColor("#070B14");

    setUser(webApp.initDataUnsafe?.user ?? null);
  }, []);

  const executeRitual = async () => {
    if (!prompt.trim()) return;
    
    setPhase("charging");
    
    // Phase 1 loader
    setChargingText("✨ [ ✦ ✧ ✧ ] Ghost Protocol initialized...");
    await new Promise(r => setTimeout(r, 800));
    
    // Phase 2 loader
    setChargingText("👾 [ ✧ ✦ ✧ ] Injecting Neural Hype...");
    await new Promise(r => setTimeout(r, 800));

    // Phase 3 loader
    setChargingText("💎 [ ✧ ✧ ✦ ] Polishing The Triad...");
    await new Promise(r => setTimeout(r, 800));

    // Wait for "API" response (Mocking the true OpenAI call for frontend testing)
    setTriad({
      A: "🚀 MΛGIC HYPE: Your project is about to shatter the matrix. Viral trajectory confirmed.",
      B: "💻 DEEP TECH: Under-the-hood optimization matrix fully scaled and optimized.",
      C: "✨ AESTHETIC: Pure minimalist glassmorphism vibes. Let the visuals breathe."
    });
    setPhase("synthesis");
  };

  const dispatchToChat = (selectedText: string, theme: string) => {
    const webApp = getTelegramWebApp();
    if (!webApp?.sendData) return;
    
    // Push the result back to Telegram Bot via WebApp protocol
    webApp.sendData(JSON.stringify({ 
      action: "manifest_completed", 
      theme,
      content: selectedText 
    }));
    
    // Provide tactile feedback before closing
    if (webApp.HapticFeedback) {
      webApp.HapticFeedback.impactOccurred("heavy");
    }
    webApp.close();
  };

  return (
    <div className="min-h-screen bg-[#070B14] text-white p-5 font-sans relative overflow-hidden">
      {/* Occult Ambient Glows */}
      <div className="absolute top-[-50px] left-[-50px] w-[200px] h-[200px] bg-purple-600/20 rounded-full blur-[80px]" />
      <div className="absolute bottom-[-50px] right-[-50px] w-[200px] h-[200px] bg-cyan-600/20 rounded-full blur-[80px]" />

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="relative z-10">
        <h1 className="text-2xl font-black tracking-tighter mb-1 bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">
          NΞBU MΛGIC
        </h1>
        <p className="text-white/50 text-xs mb-6 font-mono tracking-widest">
          {user ? `IDENTITY // ${user.username || user.first_name}` : "GHOST PROTOCOL_"}
        </p>

        <AnimatePresence mode="wait">
          {phase === "idle" && (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Drop your raw intent here..."
                className="w-full h-32 p-4 rounded-2xl bg-white/[0.03] border border-white/10 mb-4 focus:outline-none focus:border-cyan-500/50 focus:bg-white/[0.05] transition-all resize-none shadow-[0_0_15px_rgba(0,0,0,0.5)]"
              />

              <button
                onClick={executeRitual}
                disabled={!prompt.trim()}
                className="w-full p-4 rounded-xl font-bold transition-all bg-gradient-to-r from-purple-600 hover:from-purple-500 to-cyan-600 hover:to-cyan-500 shadow-[0_0_20px_rgba(168,85,247,0.3)] disabled:opacity-50"
              >
                Synthesize Triad ✨
              </button>
            </motion.div>
          )}

          {phase === "charging" && (
            <motion.div
              key="charging"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
              className="flex flex-col items-center justify-center h-48 space-y-4"
            >
              <div className="w-12 h-12 rounded-full border-t-2 border-r-2 border-cyan-400 animate-spin shadow-[0_0_15px_rgba(34,211,238,0.5)]" />
              <p className="font-mono text-sm text-cyan-200/80 animate-pulse">
                {chargingText}
              </p>
            </motion.div>
          )}

          {phase === "synthesis" && triad && (
            <motion.div
              key="synthesis"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              <p className="text-xs text-white/50 text-center mb-4">Select your manipulation vector</p>
              
              {Object.entries(triad).map(([key, text], index) => {
                const colors = [
                  "border-purple-500/30 hover:border-purple-400 shadow-purple-500/10",
                  "border-cyan-500/30 hover:border-cyan-400 shadow-cyan-500/10",
                  "border-emerald-500/30 hover:border-emerald-400 shadow-emerald-500/10"
                ];
                const bgColors = [
                  "bg-purple-500/10",
                  "bg-cyan-500/10",
                  "bg-emerald-500/10"
                ];
                const labels = ["HYPE", "DEEP TECH", "AESTHETIC"];

                return (
                  <motion.button
                    key={key}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    onClick={() => dispatchToChat(text, labels[index])}
                    className={`block w-full text-left p-5 rounded-2xl border ${colors[index]} bg-black/40 backdrop-blur-md transition-all hover:-translate-y-1`}
                  >
                    <div className="flex items-center gap-3 mb-2">
                       <span className={`text-xs font-bold px-2 py-1 rounded ${bgColors[index]}`}>OPTION {key}</span>
                       <span className="text-white/70 text-xs tracking-wider">{labels[index]}</span>
                    </div>
                    <p className="text-sm font-medium leading-relaxed">{text}</p>
                  </motion.button>
                );
              })}

              <button 
                onClick={() => setPhase("idle")}
                className="w-full mt-4 p-3 text-sm text-white/50 hover:text-white transition-colors"
              >
                🔄 Reroll Phase
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
