import { useEffect } from 'react'

import { createRealtimeSocket } from '@/services/realtime'
import { useRealtimeStore } from '@/stores/realtimeStore'

const DEFAULT_REALTIME_URL = 'ws://127.0.0.1:8000/ws/realtime'

export const useRealtimeStream = () => {
  const ingestMessage = useRealtimeStore((state) => state.ingestMessage)
  const setConnected = useRealtimeStore((state) => state.setConnected)

  useEffect(() => {
    const url = import.meta.env.VITE_REALTIME_WS_URL ?? DEFAULT_REALTIME_URL
    const socket = createRealtimeSocket(url, {
      onOpen: () => setConnected(true),
      onClose: () => setConnected(false),
      onError: () => setConnected(false),
      onMessage: (message) => ingestMessage(message),
    })

    return () => {
      socket.close()
      setConnected(false)
    }
  }, [ingestMessage, setConnected])
}
