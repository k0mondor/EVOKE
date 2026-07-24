import { useEffect, useRef, useState } from 'react'

export const useRevealOnce = <T extends HTMLElement>(threshold = 0.15) => {
  const ref = useRef<T | null>(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element || isVisible) {
      return
    }

    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) {
      setIsVisible(true)
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            window.requestAnimationFrame(() => {
              setIsVisible(true)
            })
            observer.unobserve(entry.target)
          }
        })
      },
      {
        threshold,
        rootMargin: '0px 0px -8% 0px',
      },
    )

    observer.observe(element)

    return () => {
      observer.disconnect()
    }
  }, [isVisible, threshold])

  return { ref, isVisible }
}
