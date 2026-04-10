import { Signal } from "./types"

export async function sendDiscordWebhook(signal: Signal, webhookUrl?: string): Promise<void> {
  if (!webhookUrl) {
    console.log("Discord webhook URL not configured, skipping notification")
    return
  }

  const messageSnippet = signal.message.length > 100
    ? signal.message.substring(0, 100) + "..."
    : signal.message

  const embed = {
    title: signal.ticketId,
    description: messageSnippet,
    color: 0xFF4500,
    fields: [
      {
        name: "Request Type",
        value: signal.requestType,
        inline: true
      },
      {
        name: "Name",
        value: signal.name,
        inline: true
      },
      {
        name: "Contact",
        value: signal.contact,
        inline: true
      }
    ],
    footer: {
      text: "Frisky Signal Intake v1.0"
    },
    timestamp: new Date(signal.createdAt).toISOString()
  }

  try {
    const response = await fetch(webhookUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        embeds: [embed]
      })
    })

    if (!response.ok) {
      console.error("Discord webhook failed:", response.status, response.statusText)
    }
  } catch (error) {
    console.error("Discord webhook error:", error)
  }
}
