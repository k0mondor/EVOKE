import { useEffect, useRef } from 'react'

import { publicAssetUrl } from '@/lib/assets'

const HERO_VIDEO_URL = publicAssetUrl('videos/guardnet-hero-brain.mp4')
const HERO_POSTER_URL = publicAssetUrl('images/guardnet-hero-poster.jpg')

const NAV_ITEMS = [
  { label: 'VISION', href: '#landing' },
  { label: 'MODES', href: '#room-focus' },
  { label: 'SIGNALS', href: '#mission' },
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
        className="absolute inset-0 cursor-grab touch-pan-y select-none will-change-transform active:cursor-grabbing"
        style={{
          WebkitUserSelect: 'none',
          transformOrigin: 'center center',
          backgroundImage: `url(${HERO_POSTER_URL})`,
          backgroundPosition: 'center',
          backgroundSize: 'cover',
        }}
      >
        <video
          ref={videoRef}
          className="pointer-events-none h-full w-full object-cover [user-drag:none] [-webkit-user-drag:none]"
          src={HERO_VIDEO_URL}
          poster={HERO_POSTER_URL}
          autoPlay
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

          <div className="hero-nav-pill absolute left-1/2 flex -translate-x-1/2 items-center rounded-full px-2 py-1.5">
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

          <div className="hero-qr-trigger">
            <button
              type="button"
              className="hero-qr-card"
              aria-label="Show the EVOKE community QR code"
            >
              <span className="hero-qr-card__compact" aria-hidden="true">
                <svg viewBox="0 0 24 24" role="presentation">
                  <path d="M4 4h6v6H4V4Zm2 2v2h2V6H6Zm8-2h6v6h-6V4Zm2 2v2h2V6h-2ZM4 14h6v6H4v-6Zm2 2v2h2v-2H6Zm8-2h2v2h-2v-2Zm4 0h2v4h-2v-4Zm-4 4h4v2h-4v-2Z" />
                </svg>
                <span>JOIN</span>
              </span>

              <span className="hero-qr-card__expanded">
                <img src={publicAssetUrl('images/evoke-community-qr.jpg')} alt="EVOKE community group QR code" />
                <strong>SCAN TO JOIN</strong>
                <small>EVOKE COMMUNITY</small>
              </span>
            </button>
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

        <div className="hero-event-meta" aria-label="AdventureX 2026">
          <span className="hero-event-meta__label">AdventureX</span>
          <span className="hero-event-meta__year">2026</span>
        </div>

        <div className="hero-signal-meta" aria-label="8 channels at 250 hertz">
          <span className="hero-signal-meta__number">8</span>
          <span className="hero-signal-meta__unit">CHANNELS</span>
          <span className="hero-signal-meta__divider">/</span>
          <span className="hero-signal-meta__number">250</span>
          <span className="hero-signal-meta__unit">HZ</span>
        </div>
      </div>
    </section>
  )
}

function currentTimeSafePlay(video: HTMLVideoElement) {
  video.currentTime = 0
  video.playbackRate = 1
  void video.play().catch(() => undefined)
}
