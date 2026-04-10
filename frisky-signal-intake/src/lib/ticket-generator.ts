export function generateTicketId(): string {
  const digits = Math.floor(1000 + Math.random() * 9000)
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
  const letter = letters[Math.floor(Math.random() * letters.length)]
  return `FRK-${digits}-${letter}`
}

export async function generateUniqueTicketId(existingIds: string[]): Promise<string> {
  let attempts = 0
  let ticketId = generateTicketId()

  while (existingIds.includes(ticketId) && attempts < 10) {
    ticketId = generateTicketId()
    attempts++
  }

  return ticketId
}
