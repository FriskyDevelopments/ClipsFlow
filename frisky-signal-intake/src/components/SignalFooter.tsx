import { motion } from "framer-motion"

export function SignalFooter() {
  return (
    <footer className="relative w-full mt-16 pb-12">
      <div className="absolute inset-x-0 top-0 h-[1px] bg-gradient-to-r from-transparent via-border to-transparent" />

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="max-w-5xl mx-auto px-6 sm:px-8 pt-12"
      >
        <div className="space-y-6 text-center">
          <p
            className="
              text-[14px] md:text-[15px]
              tracking-wide
              text-transparent
              bg-clip-text
              bg-gradient-to-r
              from-white/55
              via-white/35
              to-white/55
              opacity-90
            "
          >
            🐾 Forged with a Frisky Paw and a daring heart.
          </p>

          <div className="space-y-3">
            <div className="text-lg sm:text-xl text-foreground/90 leading-relaxed">
              <span>Your </span>
              <span className="font-semibold bg-gradient-to-r from-[oklch(0.65_0.25_265)] via-[oklch(0.60_0.22_275)] to-[oklch(0.55_0.20_285)] bg-clip-text text-transparent drop-shadow-[0_0_10px_oklch(0.60_0.22_275/0.35)]">
                Signal
              </span>
              <span> matters.</span>
            </div>

            <p className="text-base sm:text-lg text-muted-foreground">
              We're here to move it forward.
            </p>

            <p className="text-xs sm:text-sm text-muted-foreground/70 italic pt-2">
              — FriskyDevelopments
            </p>
          </div>

          <div className="pt-6">
            <p className="text-xs text-muted-foreground/50">
              ✦
            </p>
          </div>
        </div>
      </motion.div>
    </footer>
  )
}
