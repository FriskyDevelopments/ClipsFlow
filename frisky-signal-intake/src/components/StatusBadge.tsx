import { Badge } from "@/components/ui/badge"
import { SignalStatus } from "@/lib/types"
import { cn } from "@/lib/utils"

interface StatusBadgeProps {
  status: SignalStatus
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const getStatusColor = (status: SignalStatus) => {
    switch (status) {
      case "SIGNAL_RECEIVED":
        return "bg-accent/20 text-accent border-accent/30"
      case "OPERATOR_ASSIGNED":
        return "bg-primary/20 text-primary border-primary/30"
      case "IN_REVIEW":
        return "bg-blue-500/20 text-blue-400 border-blue-500/30"
      case "WAITING_ON_USER":
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
      case "RESOLUTION_COMPLETE":
        return "bg-green-500/20 text-green-400 border-green-500/30"
      default:
        return "bg-muted-foreground/20 text-muted-foreground border-muted-foreground/30"
    }
  }

  return (
    <Badge
      variant="outline"
      className={cn(
        "text-xs font-medium uppercase tracking-wider border",
        getStatusColor(status),
        className
      )}
    >
      {status.replace(/_/g, " ")}
    </Badge>
  )
}
