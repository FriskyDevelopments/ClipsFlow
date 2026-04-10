import { SignalStatus } from "@/lib/types"
import { CheckCircle, Clock } from "@phosphor-icons/react"
import { cn } from "@/lib/utils"

interface StatusTimelineProps {
  currentStatus: SignalStatus
  lastUpdated: number
  className?: string
}

const statusOrder: SignalStatus[] = [
  "SIGNAL_RECEIVED",
  "OPERATOR_ASSIGNED",
  "IN_REVIEW",
  "WAITING_ON_USER",
  "RESOLUTION_COMPLETE"
]

export function StatusTimeline({ currentStatus, lastUpdated, className }: StatusTimelineProps) {
  const currentIndex = statusOrder.indexOf(currentStatus)

  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp)
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    })
  }

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Signal Status
        </h3>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock size={14} />
          <span>Last ping: {formatTimestamp(lastUpdated)}</span>
        </div>
      </div>

      <div className="relative">
        {statusOrder.map((status, index) => {
          const isPast = index < currentIndex
          const isCurrent = index === currentIndex
          const isFuture = index > currentIndex

          return (
            <div key={status} className="relative flex items-start gap-4 pb-8 last:pb-0">
              {index !== statusOrder.length - 1 && (
                <div
                  className={cn(
                    "absolute left-[11px] top-6 w-0.5 h-full",
                    isPast || isCurrent ? "bg-primary/30" : "bg-border"
                  )}
                />
              )}

              <div className={cn(
                "relative flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center",
                isCurrent && "bg-primary border-primary shadow-[0_0_20px_rgba(var(--color-primary),0.3)]",
                isPast && "bg-primary/20 border-primary",
                isFuture && "bg-transparent border-border"
              )}>
                {isPast && <CheckCircle size={14} className="text-primary" weight="fill" />}
                {isCurrent && <div className="w-2 h-2 rounded-full bg-primary-foreground" />}
              </div>

              <div className="flex-1 pt-0.5">
                <div className={cn(
                  "text-sm font-medium uppercase tracking-wider",
                  isCurrent && "text-foreground",
                  isPast && "text-muted-foreground",
                  isFuture && "text-muted-foreground/50"
                )}>
                  {status.replace(/_/g, " ")}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
