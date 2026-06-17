type RunesLoadingProps = {
  active?: boolean;
  state?: "idle" | "handoff" | "sent" | "preview";
};

const steps = ["Receive", "Shape", "Confirm"];

export default function RunesLoading({ active = false, state = "idle" }: RunesLoadingProps) {
  return (
    <div className="relative overflow-hidden rounded-md border border-[#253132] bg-[#101720] p-4 shadow-[0_20px_80px_rgba(0,0,0,0.26)]">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[#d6ef7d]/70 to-transparent" />
      <div className="flex items-center justify-between gap-2">
        {steps.map((step, index) => {
          const lit = active || state === "sent" || (state === "idle" && index === 0);
          return (
            <div key={step} className="flex min-w-0 flex-1 items-center">
              <div className="flex min-w-0 items-center gap-2">
                <span
                  className={`h-2.5 w-2.5 shrink-0 rounded-full transition ${
                    lit ? "bg-[#d6ef7d] shadow-[0_0_24px_rgba(214,239,125,0.5)]" : "bg-[#2d3839]"
                  } ${active && index === 1 ? "animate-[cf-breathe_1.8s_ease-in-out_infinite]" : ""}`}
                />
                <span className="truncate text-[11px] uppercase tracking-[0.12em] text-[#9da9a5]">{step}</span>
              </div>
              {index < steps.length - 1 && <span className="mx-3 h-px flex-1 bg-[#263233]" />}
            </div>
          );
        })}
      </div>
      <div className="mt-5 h-24 overflow-hidden rounded bg-[#0b0f15]">
        <div className={`cf-signal-field h-full w-full ${active ? "is-active" : ""}`}>
          <span className="cf-signal-pulse" />
          <span className="cf-signal-pulse cf-signal-pulse-late" />
        </div>
      </div>
    </div>
  );
}
