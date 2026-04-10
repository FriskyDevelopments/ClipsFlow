import { useState, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { GlassPanel } from "@/components/GlassPanel"
import { SignalDeskHeader } from "@/components/SignalDeskHeader"
import { StatusBadge } from "@/components/StatusBadge"
import { MagnifyingGlass, Funnel, Export, Gear } from "@phosphor-icons/react"
import { Signal, SignalStatus, RequestType } from "@/lib/types"
import { useKV } from "@github/spark/hooks"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"

export function ConsolePage() {
  const navigate = useNavigate()
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [password, setPassword] = useState("")
  const [signals, setSignals] = useKV<Signal[]>("signals", [])
  const [webhookUrl, setWebhookUrl] = useKV<string>("discord-webhook-url", "")
  const [telegramBotToken, setTelegramBotToken] = useKV<string>("telegram-bot-token", "")
  const [telegramChatId, setTelegramChatId] = useKV<string>("telegram-chat-id", "")
  const [tempWebhookUrl, setTempWebhookUrl] = useState("")
  const [tempTelegramBotToken, setTempTelegramBotToken] = useState("")
  const [tempTelegramChatId, setTempTelegramChatId] = useState("")
  const [settingsOpen, setSettingsOpen] = useState(false)

  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState<SignalStatus | "ALL">("ALL")
  const [typeFilter, setTypeFilter] = useState<RequestType | "ALL">("ALL")

  const filteredSignals = useMemo(() => {
    if (!signals) return []

    return signals.filter(signal => {
      const matchesSearch =
        signal.ticketId.toLowerCase().includes(searchTerm.toLowerCase()) ||
        signal.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        signal.contact.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesStatus = statusFilter === "ALL" || signal.status === statusFilter
      const matchesType = typeFilter === "ALL" || signal.requestType === typeFilter

      return matchesSearch && matchesStatus && matchesType
    })
  }, [signals, searchTerm, statusFilter, typeFilter])

  const handleMarkAsViewed = (signalId: string) => {
    setSignals((current) =>
      current?.map(s => s.id === signalId ? { ...s, isNew: false } : s) ?? []
    )
  }

  const handleExportCSV = () => {
    if (!signals || signals.length === 0) {
      toast.error("No signals to export")
      return
    }

    const headers = ["Ticket ID", "Name", "Contact", "Request Type", "Project", "Status", "Created At", "Updated At"]
    const rows = signals.map(s => [
      s.ticketId,
      s.name,
      s.contact,
      s.requestType,
      s.project || "",
      s.status,
      new Date(s.createdAt).toLocaleString(),
      new Date(s.updatedAt).toLocaleString()
    ])

    const csvContent = [
      headers.join(","),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(","))
    ].join("\n")

    const blob = new Blob([csvContent], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = `signals-export-${Date.now()}.csv`
    link.click()
    URL.revokeObjectURL(url)

    toast.success("Signals exported to CSV")
  }

  const handleSaveSettings = () => {
    setWebhookUrl(tempWebhookUrl)
    setTelegramBotToken(tempTelegramBotToken)
    setTelegramChatId(tempTelegramChatId)
    setSettingsOpen(false)
    toast.success("Settings saved")
  }

  const openSettings = () => {
    setTempWebhookUrl(webhookUrl || "")
    setTempTelegramBotToken(telegramBotToken || "")
    setTempTelegramChatId(telegramChatId || "")
    setSettingsOpen(true)
  }

  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp)
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    })
  }

  const scrollToQueue = () => {
    const element = document.getElementById('signal-queue')
    element?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  const activeSignalsCount = filteredSignals.filter(s =>
    s.status !== "RESOLUTION_COMPLETE"
  ).length

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <GlassPanel className="max-w-md w-full p-8 text-center">
          <h2 className="text-2xl font-bold mb-6 text-foreground tracking-tight">OPERATOR ACCESS</h2>
          <div className="space-y-4">
            <div className="space-y-2 text-left">
              <Label htmlFor="password">System Access Key</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => {
                  const expectedKey = import.meta.env.VITE_SYSTEM_PASSWORD || "admin"
                  if (e.key === "Enter" && password === expectedKey) {
                    setIsAuthenticated(true)
                  } else if (e.key === "Enter") {
                    toast.error("Invalid access key")
                  }
                }}
                placeholder="Enter access key..."
                className="bg-[#0A0A0A] border-[#333333]"
              />
            </div>
            <Button
              onClick={() => {
                const expectedKey = import.meta.env.VITE_SYSTEM_PASSWORD || "admin"
                if (password === expectedKey) {
                  setIsAuthenticated(true)
                } else {
                  toast.error("Invalid access key")
                }
              }}
              className="w-full bg-[#E67E22] text-black"
            >
              Verify Identity
            </Button>
          </div>
        </GlassPanel>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <SignalDeskHeader
        variant="console"
        onOpenQueue={scrollToQueue}
        onActiveSignals={scrollToQueue}
      />

      <div className="p-6 sm:p-8">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="max-w-7xl mx-auto"
        >
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight mb-2">
                Signal Queue
              </h2>
              <p className="text-muted-foreground">
                {activeSignalsCount} active signal{activeSignalsCount !== 1 ? 's' : ''}
              </p>
            </div>

            <div className="flex gap-2">
              <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" onClick={openSettings}>
                    <Gear className="mr-2" />
                    Settings
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Console Settings</DialogTitle>
                    <DialogDescription>
                      Configure webhook notifications for new signals
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 pt-4">
                    <div className="space-y-2">
                      <Label htmlFor="webhook-url">Discord Webhook URL</Label>
                      <Input
                        id="webhook-url"
                        value={tempWebhookUrl}
                        onChange={(e) => setTempWebhookUrl(e.target.value)}
                        placeholder="https://discord.com/api/webhooks/..."
                      />
                      <p className="text-xs text-muted-foreground">
                        Discord channel for signal notifications
                      </p>
                    </div>

                    <div className="border-t pt-4">
                      <h4 className="text-sm font-medium mb-3">Telegram Bot Configuration</h4>
                      <div className="space-y-4">
                        <div className="space-y-2">
                          <Label htmlFor="telegram-bot-token">Bot Token</Label>
                          <Input
                            id="telegram-bot-token"
                            type="password"
                            value={tempTelegramBotToken}
                            onChange={(e) => setTempTelegramBotToken(e.target.value)}
                            placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                          />
                          <p className="text-xs text-muted-foreground">
                            Get from @BotFather on Telegram
                          </p>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="telegram-chat-id">Chat ID</Label>
                          <Input
                            id="telegram-chat-id"
                            value={tempTelegramChatId}
                            onChange={(e) => setTempTelegramChatId(e.target.value)}
                            placeholder="-1001234567890"
                          />
                          <p className="text-xs text-muted-foreground">
                            Channel or group chat ID for notifications
                          </p>
                        </div>
                      </div>
                    </div>

                    <Button onClick={handleSaveSettings} className="w-full">
                      Save Settings
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>

              <Button onClick={handleExportCSV} variant="outline">
                <Export className="mr-2" />
                Export CSV
              </Button>
            </div>
          </div>

          <GlassPanel className="mb-6" id="signal-queue">
            <div className="flex gap-4 flex-wrap">
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                  <Input
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search by Ticket ID, name, or contact"
                    className="pl-10"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as SignalStatus | "ALL")}>
                  <SelectTrigger className="w-[180px]">
                    <Funnel className="mr-2" size={18} />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Status</SelectItem>
                    <SelectItem value="SIGNAL_RECEIVED">Signal Received</SelectItem>
                    <SelectItem value="OPERATOR_ASSIGNED">Operator Assigned</SelectItem>
                    <SelectItem value="IN_REVIEW">In Review</SelectItem>
                    <SelectItem value="WAITING_ON_USER">Waiting On User</SelectItem>
                    <SelectItem value="RESOLUTION_COMPLETE">Resolution Complete</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={typeFilter} onValueChange={(value) => setTypeFilter(value as RequestType | "ALL")}>
                  <SelectTrigger className="w-[200px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">All Types</SelectItem>
                    <SelectItem value="Technical Support">Technical Support</SelectItem>
                    <SelectItem value="Billing / Order Help">Billing / Order Help</SelectItem>
                    <SelectItem value="Partnership / Collaboration">Partnership / Collaboration</SelectItem>
                    <SelectItem value="Custom Build Request">Custom Build Request</SelectItem>
                    <SelectItem value="General Inquiry">General Inquiry</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </GlassPanel>

          <GlassPanel className="overflow-hidden p-0">
            {filteredSignals.length === 0 ? (
              <div className="p-12 text-center text-muted-foreground">
                <p>No active signals</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[140px]">Ticket ID</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredSignals.map((signal) => (
                      <TableRow
                        key={signal.id}
                        className={cn(
                          "cursor-pointer transition-all duration-200",
                          signal.isNew && "signal-new"
                        )}
                        onClick={() => {
                          handleMarkAsViewed(signal.id)
                          navigate(`/console/signal/${signal.id}`)
                        }}
                      >
                        <TableCell className="font-medium">
                          {signal.ticketId}
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{signal.name}</div>
                            <div className="text-sm text-muted-foreground">{signal.contact}</div>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm">
                          {signal.requestType}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={signal.status} />
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatTimestamp(signal.createdAt)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </GlassPanel>
        </motion.div>
      </div>
    </div>
  )
}
