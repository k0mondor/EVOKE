import type { RealtimeMessage } from '@/types/realtime'

export interface RealtimeSocketHandlers {
  onOpen?: () => void
  onClose?: () => void
  onMessage?: (message: RealtimeMessage) => void
  onError?: (event: Event) => void
}

export const createRealtimeSocket = (
  url: string,
  handlers: RealtimeSocketHandlers,
): WebSocket => {
  const socket = new WebSocket(url)

  socket.onopen = () => handlers.onOpen?.()
  socket.onclose = () => handlers.onClose?.()
  socket.onerror = (event) => handlers.onError?.(event)
  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as RealtimeMessage
      handlers.onMessage?.(data)
    } catch {
      // Ignore malformed messages in the demo phase.
    }
  }

  return socket
}
