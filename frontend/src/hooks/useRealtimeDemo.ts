import { useEffect } from 'react'

import { useRealtimeStore } from '@/stores/realtimeStore'

export const useRealtimeDemo = () => {
  const hydrateDemo = useRealtimeStore((state) => state.hydrateDemo)
  const setConnected = useRealtimeStore((state) => state.setConnected)

  useEffect(() => {
    setConnected(true)
    const timer = window.setInterval(() => hydrateDemo(), 900)

    return () => {
      window.clearInterval(timer)
      setConnected(false)
    }
  }, [hydrateDemo, setConnected])
}
