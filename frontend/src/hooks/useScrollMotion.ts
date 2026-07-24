import { useEffect, useRef } from 'react'

import { usePageMotionStore } from '@/stores/pageMotionStore'

export const useScrollMotion = () => {
  const setScrollProgress = usePageMotionStore((state) => state.setScrollProgress)
  const currentRef = useRef(usePageMotionStore.getState().scrollProgress)
  const targetRef = useRef(usePageMotionStore.getState().scrollProgress)

  useEffect(() => {
    const update = () => {
      const scrollTop = window.scrollY
      const maxScrollable = Math.max(document.body.scrollHeight - window.innerHeight, 1)
      const nextTarget = Math.max(0, Math.min(1, scrollTop / maxScrollable))
      targetRef.current = nextTarget
    }

    update()
    window.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', update)

    return () => {
      window.removeEventListener('scroll', update)
      window.removeEventListener('resize', update)
    }
  }, [])

  useEffect(() => {
    let frameId = 0

    const animate = () => {
      const next = currentRef.current + (targetRef.current - currentRef.current) * 0.08
      currentRef.current = next
      setScrollProgress(next)
      frameId = window.requestAnimationFrame(animate)
    }

    frameId = window.requestAnimationFrame(animate)

    return () => {
      window.cancelAnimationFrame(frameId)
    }
  }, [setScrollProgress])
}
