import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { GlassPanel } from "@/components/GlassPanel"
import { SignalDeskHeader } from "@/components/SignalDeskHeader"
import { SignalFooter } from "@/components/SignalFooter"
import { StatusTimeline } from "@/components/StatusTimeline"
import { MagnifyingGlass } from "@phosphor-icons/react"
import { Signal } from "@/lib/types"
import { useKV } from "@github/spark/hooks"
import { motion } from "framer-motion"

export function StatusPage() {
  const navigate = useNavigate()
  const [signals] = useKV<Signal[]>("signals", [])
  const [ticketId, setTicketId] = useState("")
  const [searchedSignal, setSearchedSignal] = useState<Signal | null>(null)
  const [notFound, setNotFound] = useState(false)

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()

    const signal = signals?.find(s => s.ticketId.toUpperCase() === ticketId.toUpperCase())

    if (signal) {
      setSearchedSignal(signal)
      setNotFound(false)
    } else {
      setSearchedSignal(null)
      setNotFound(true)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <SignalDeskHeader
        variant="status"
        onTrack={() => {}}
        onTransmit={() => navigate("/")}
      />

      <div className="p-6 sm:p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="max-w-3xl mx-auto"
        >

          <GlassPanel className="mb-8">
            <form onSubmit={handleSearch} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="ticket-id">Ticket ID</Label>
                <div className="flex gap-2">
                  <Input
                    id="ticket-id"
                    value={ticketId}
                    onChange={(e) => setTicketId(e.target.value)}
                    placeholder="FRK-XXXX-X"
                    className="uppercase"
                    required
                  />
                  <Button type="submit">
                    <MagnifyingGlass className="mr-2" />
                    Search
                  </Button>
                </div>
              </div>
            </form>
          </GlassPanel>

          {notFound && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <GlassPanel className="text-center">
                <p className="text-muted-foreground">
                  Signal not found. Please verify your Ticket ID and try again.
                </p>
              </GlassPanel>
            </motion.div>
          )}

          {searchedSignal && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <GlassPanel>
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-medium">
                      {searchedSignal.ticketId}
                    </h2>
                    <span className="text-sm text-muted-foreground">
                      {searchedSignal.requestType}
                    </span>
                  </div>
                  <div className="space-y-1 text-sm">
                    <p className="text-muted-foreground">
                      <span className="font-medium">Name:</span> {searchedSignal.name}
                    </p>
                    {searchedSignal.project && (
                      <p className="text-muted-foreground">
                        <span className="font-medium">Project:</span> {searchedSignal.project}
                      </p>
                    )}
                  </div>
                </div>

                <StatusTimeline
                  currentStatus={searchedSignal.status}
                  lastUpdated={searchedSignal.updatedAt}
                />
              </GlassPanel>
            </motion.div>
          )}
        </motion.div>
      </div>

      <SignalFooter />
    </div>
  )
}
