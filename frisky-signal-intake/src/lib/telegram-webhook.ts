import { Signal } from "./types"

interface TelegramMessage {
  chat_id: string
  text: string
  parse_mode: "Markdown" | "HTML"
}

export async function sendTelegramWebhook(signal: Signal, botToken?: string, chatId?: string): Promise<void> {
  if (!botToken || !chatId) {
    console.log("Telegram bot configuration incomplete, skipping notification")
    return
  }

  const messageSnippet = signal.message.length > 200
    ? signal.message.substring(0, 200) + "..."
    : signal.message

  const message = `
🚨 *New Signal Received*

*Ticket ID:* \`${signal.ticketId}\`
*Type:* ${signal.requestType}
*From:* ${signal.name}
*Contact:* ${signal.contact}
${signal.project ? `*Project:* ${signal.project}\n` : ''}
*Message:*
${messageSnippet}

_Frisky Signal Intake System_
  `.trim()

  const payload: TelegramMessage = {
    chat_id: chatId,
    text: message,
    parse_mode: "Markdown"
  }

  try {
    const response = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      const error = await response.json()
      console.error("Telegram webhook failed:", response.status, error)
    }
  } catch (error) {
    console.error("Telegram webhook error:", error)
  }
}
