"use client";

import { useState } from "react";
import RunesLoading from "../../components/RunesLoading";
import ClipResultCard from "../../components/ClipResultCard";

const DEMO_RESULT = {
  title: "Example Clip 01",
  thumbnail: "https://placehold.co/400x300",
  duration: "0:45",
};

export default function PlaygroundPage() {
  const [activeState, setActiveState] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");

  return (
    <div className="min-h-screen bg-[#11131a] text-white p-6">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8 border-b border-white/10 pb-4 flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-bold">UI Playground</h1>
            <p className="text-sm opacity-60">Visual system states preview</p>
          </div>
          <div className="flex gap-2 text-sm">
            <button
              onClick={() => setActiveState("idle")}
              className={`px-3 py-1 rounded border ${activeState === "idle" ? "bg-white/10 border-white/20" : "border-transparent opacity-50 hover:opacity-100"}`}
            >
              Idle
            </button>
            <button
              onClick={() => setActiveState("loading")}
              className={`px-3 py-1 rounded border ${activeState === "loading" ? "bg-white/10 border-white/20" : "border-transparent opacity-50 hover:opacity-100"}`}
            >
              Loading
            </button>
            <button
              onClick={() => setActiveState("success")}
              className={`px-3 py-1 rounded border ${activeState === "success" ? "bg-white/10 border-white/20" : "border-transparent opacity-50 hover:opacity-100"}`}
            >
              Success
            </button>
            <button
              onClick={() => setActiveState("error")}
              className={`px-3 py-1 rounded border ${activeState === "error" ? "bg-white/10 border-white/20" : "border-transparent opacity-50 hover:opacity-100"}`}
            >
              Error
            </button>
          </div>
        </div>

        <div className="space-y-12">
          {/* Active State View */}
          <section>
            <h2 className="text-sm font-semibold opacity-50 mb-4 uppercase tracking-wider">
              Active Flow Preview
            </h2>
            <div className="max-w-sm border border-white/10 rounded-lg p-4 bg-[#0a0b0f]">
              <input
                value="https://youtube.com/watch?v=demo"
                readOnly
                className="w-full p-3 rounded bg-[#171b26] border border-white/10 mb-3 text-white/50"
              />

              <button
                disabled={activeState === "loading"}
                className={`w-full p-3 rounded font-bold transition-all ${
                  activeState === "loading"
                    ? "bg-white/10 text-white/50 cursor-not-allowed"
                    : "bg-gradient-to-r from-pink-500 to-cyan-400 text-black hover:opacity-90"
                }`}
              >
                {activeState === "loading" ? "Processing..." : "Process Clip"}
              </button>

              {activeState === "loading" && <RunesLoading />}

              {activeState === "error" && (
                <div className="mt-4 p-3 rounded bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex gap-2 items-start">
                  <span className="font-mono">✕</span>
                  <div>
                    <div className="font-bold mb-1">Disruption Detected</div>
                    <div className="opacity-80">
                      Failed to extract media from the provided URL.
                    </div>
                  </div>
                </div>
              )}

              {activeState === "success" && (
                <ClipResultCard
                  result={DEMO_RESULT}
                  onSend={() => alert("Simulated send!")}
                />
              )}
            </div>
          </section>

          {/* Component Library */}
          <section className="pt-8 border-t border-white/10">
            <h2 className="text-sm font-semibold opacity-50 mb-6 uppercase tracking-wider">
              Component Library
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <h3 className="text-sm opacity-70 mb-3 font-mono">
                  {"<RunesLoading />"}
                </h3>
                <div className="p-4 border border-white/10 rounded bg-[#0a0b0f]">
                  <RunesLoading />
                </div>
              </div>

              <div>
                <h3 className="text-sm opacity-70 mb-3 font-mono">
                  {"<ClipResultCard />"}
                </h3>
                <div className="p-4 border border-white/10 rounded bg-[#0a0b0f]">
                  <ClipResultCard result={DEMO_RESULT} />
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
