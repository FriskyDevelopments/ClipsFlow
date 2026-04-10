import { useParams, useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { GlassPanel } from "@/components/GlassPanel"
import { SignalFooter } from "@/components/SignalFooter"
import { CheckCircle } from "@phosphor-icons/react"
import { motion } from "framer-motion"

export function SubmittedPage() {
  const { ticketId } = useParams()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-background p-8 flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="max-w-2xl w-full"
      >
        <GlassPanel className="text-center">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center">
              <CheckCircle size={32} className="text-primary" weight="fill" />
            </div>
          </div>

          <h1 className="text-3xl font-semibold mb-4">
            Signal Received
          </h1>

          <div className="space-y-4 mb-8">
            <div className="glass-panel inline-block px-6 py-3 rounded">
              <p className="text-sm text-muted-foreground mb-1 uppercase tracking-wider">
                Ticket ID
              </p>
              <p className="text-2xl font-semibold tracking-tight">
                {ticketId}
              </p>
            </div>

            <div className="space-y-2 text-muted-foreground">
              <p>Your request is now in the system.</p>
              <p>Track it with your Ticket ID.</p>
              <p className="text-sm">No DMs. The desk will handle it from here.</p>
            </div>
          </div>

          <div className="flex gap-4 justify-center">
            <Button onClick={() => navigate("/status")} size="lg">
              Check Request Status
            </Button>
            <Button onClick={() => navigate("/")} variant="outline" size="lg">
              Submit Another
            </Button>
          </div>
        </GlassPanel>

        <div className="mt-6 text-center text-sm text-muted-foreground">
          <p>Save your Ticket ID to check status at any time.</p>
        </div>
      </motion.div>

      <SignalFooter />
    </div>
  )
}
