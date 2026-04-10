import { motion } from "framer-motion"
import { GlassPanel } from "@/components/GlassPanel"

export function AccessDenied() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
      >
        <GlassPanel className="border-red-500/30 bg-red-950/10 max-w-md w-full p-8 text-center">
          <div className="mb-4">
            <span className="text-4xl font-bold text-red-500">✕</span>
          </div>
          <h2 className="text-2xl font-bold mb-2 text-foreground">ACCESS DENIED</h2>
          <p className="text-muted-foreground text-sm">
            Jules Verification failed. This portal is exclusively for Pro users.
            No valid session_id found in the URL.
          </p>
        </GlassPanel>
      </motion.div>
    </div>
  )
}
