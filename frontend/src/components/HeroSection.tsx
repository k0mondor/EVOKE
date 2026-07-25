import { useEffect, useRef } from 'react'

const NAV_ITEMS = [
  { label: 'vision', href: '#landing' },
  { label: 'modes', href: '#room-focus' },
  { label: 'signals', href: '#mission' },
] as const

export const HeroSection = () => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const speedRef = useRef(1.0)
  const targetSpeedRef = useRef(1.0)
  const springVelocityRef = useRef(0)
  const isInteractingRef = useRef(false)
  const startXRef = useRef(0)
  const activePointerIdRef = useRef<number | null>(null)

  useEffect(() => {
    const container = containerRef.current
    const video = videoRef.current
    if (!container || !video) {
      return
    }

    let frameId = 0
    let lastTimestamp = performance.now()

    const getClientX = (event: PointerEvent) => event.clientX

    const handleStart = (event: PointerEvent) => {
      isInteractingRef.current = true
      activePointerIdRef.current = event.pointerId
      startXRef.current = getClientX(event)
      springVelocityRef.current = 0
      container.setPointerCapture(event.pointerId)
    }

    const handleMove = (event: PointerEvent) => {
      if (!isInteractingRef.current || activePointerIdRef.current !== event.pointerId) {
        return
      }

      const clientX = getClientX(event)
      const dragDistance = clientX - startXRef.current
      const sensitivity = dragDistance < 0 ? 0.032 : 0.020
      const minSpeed = -3.5
      const maxSpeed = 3.2
      const calculatedSpeed = 1.0 + dragDistance * sensitivity
      targetSpeedRef.current = Math.max(minSpeed, Math.min(maxSpeed, calculatedSpeed))
    }

    const handleEnd = (event?: PointerEvent) => {
      if (!isInteractingRef.current) {
        return
      }

      if (event && activePointerIdRef.current !== event.pointerId) {
        return
      }

      isInteractingRef.current = false
      targetSpeedRef.current = 1.0
      if (activePointerIdRef.current !== null && container.hasPointerCapture(activePointerIdRef.current)) {
        container.releasePointerCapture(activePointerIdRef.current)
      }
      activePointerIdRef.current = null
    }

    const handleLostPointerCapture = () => {
      handleEnd()
    }

    const handleWindowBlur = () => {
      handleEnd()
    }

    const step = (now: number) => {
      const currentVideo = videoRef.current
      if (!currentVideo) {
        return
      }

      let delta = (now - lastTimestamp) / 1000
      lastTimestamp = now
      if (delta > 0.1) {
        delta = 0.016
      }

      if (isInteractingRef.current) {
        speedRef.current += (targetSpeedRef.current - speedRef.current) * 0.20
      } else {
        const displacement = 1.0 - speedRef.current
        springVelocityRef.current += displacement * 0.18
        springVelocityRef.current *= 0.78
        speedRef.current += springVelocityRef.current
      }

      const speedOffset = speedRef.current - 1.0
      const scaleX = 1 + Math.min(0.08, Math.abs(speedOffset) * 0.02)
      const scaleY = 1 - Math.min(0.04, Math.abs(speedOffset) * 0.012)
      const skew = Math.max(-4, Math.min(4, speedOffset * -1.4))
      container.style.transform = `scale(${scaleX}, ${scaleY}) skewX(${skew}deg)`

      if (currentVideo.readyState >= 2 && currentVideo.duration > 0 && !Number.isNaN(currentVideo.duration)) {
        if (speedRef.current >= 0.1) {
          if (currentVideo.paused) {
            void currentVideo.play().catch(() => {})
          }
          currentVideo.playbackRate = Math.min(speedRef.current, 3.2)
        } else {
          if (!currentVideo.paused) {
            currentVideo.pause()
          }

          const duration = currentVideo.duration
          let newTime = currentVideo.currentTime + speedRef.current * delta
          newTime = ((newTime % duration) + duration) % duration
          currentVideo.currentTime = newTime
        }
      }

      frameId = window.requestAnimationFrame(step)
    }

    currentTimeSafePlay(video)
    frameId = window.requestAnimationFrame(step)

    container.addEventListener('pointerdown', handleStart)
    window.addEventListener('pointermove', handleMove)
    window.addEventListener('pointerup', handleEnd)
    window.addEventListener('pointercancel', handleEnd)
    container.addEventListener('lostpointercapture', handleLostPointerCapture)
    window.addEventListener('blur', handleWindowBlur)

    return () => {
      window.cancelAnimationFrame(frameId)
      container.style.transform = ''
      container.removeEventListener('pointerdown', handleStart)
      window.removeEventListener('pointermove', handleMove)
      window.removeEventListener('pointerup', handleEnd)
      window.removeEventListener('pointercancel', handleEnd)
      container.removeEventListener('lostpointercapture', handleLostPointerCapture)
      window.removeEventListener('blur', handleWindowBlur)
    }
  }, [])

  return (
    <section
      id="landing"
      data-scroll-section
      className="hero-section relative z-20 h-[100svh] min-h-[720px] overflow-hidden bg-black text-white"
    >
      <div
        ref={containerRef}
        className="absolute inset-0 cursor-grab active:cursor-grabbing touch-none select-none will-change-transform"
        style={{ WebkitUserSelect: 'none', transformOrigin: 'center center' }}
      >
        <video
          ref={videoRef}
          className="pointer-events-none h-full w-full object-cover [user-drag:none] [-webkit-user-drag:none]"
          src="/videos/guardnet-hero-brain.mp4"
          loop
          muted
          playsInline
          preload="auto"
          aria-hidden="true"
        />
      </div>
      <div className="pointer-events-none absolute inset-0 bg-black/28" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,0,0,0.02),rgba(0,0,0,0.42)_72%,rgba(0,0,0,0.72)_100%)]" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-56 bg-gradient-to-b from-transparent via-black/24 to-black" />

      <header className="absolute inset-x-0 top-0 z-30 px-4 pt-5 sm:px-6 md:px-10 md:pt-7">
        <nav className="relative mx-auto flex max-w-[1840px] items-center gap-4" aria-label="Primary">
          <a href="#landing" className="evoke-logo px-1 py-2" aria-label="EVOKE home">
            EVOKE
          </a>

          <div className="hero-nav-pill absolute left-1/2 hidden -translate-x-1/2 items-center rounded-full px-2 py-1.5 md:flex">
            {NAV_ITEMS.map((item) => (
              <a
                key={item.label}
                href={item.href}
                className="rounded-full px-5 py-2 text-sm text-white/68 transition hover:bg-white/[0.06] hover:text-white"
              >
                {item.label}
              </a>
            ))}
          </div>
        </nav>
      </header>

      <div className="pointer-events-none relative mx-auto h-full w-full max-w-[1640px] px-4 sm:px-6 md:px-10">
        <h1 className="sr-only">One thought. World responds.</h1>

        <div className="hero-statement hero-statement--thought" aria-hidden="true">
          <span>ONE</span>
          <span>THOUGHT</span>
          <p>Thought-Activated Spatial System.</p>
        </div>

        <div className="hero-statement hero-statement--response" aria-hidden="true">
          <span>WORLD</span>
          <span>RESPONDS</span>
        </div>
      </div>
    </section>
  )
}

function currentTimeSafePlay(video: HTMLVideoElement) {
  video.pause()
  video.currentTime = 0
  video.playbackRate = 1
}
