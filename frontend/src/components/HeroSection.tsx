import { useEffect, useRef } from 'react'

import { FloatingNav } from '@/components/FloatingNav'

interface HeroSectionProps {
  sectionIds: string[]
}

interface HeroMetricProps {
  value: string
  label: string
  className: string
  lineClassName?: string
}

const HeroMetric = ({ value, label, className, lineClassName = '' }: HeroMetricProps) => {
  return (
    <div className={`absolute z-20 ${className}`}>
      <div className="flex items-center gap-4">
        <div>
          <p className="text-2xl tracking-[-0.05em] text-white sm:text-4xl md:text-5xl">{value}</p>
          <p className="mt-1 text-[10px] uppercase tracking-[0.24em] text-white/55 sm:text-xs">{label}</p>
        </div>
        <span className={`hidden h-px w-20 bg-white/30 md:block ${lineClassName}`} />
      </div>
    </div>
  )
}

export const HeroSection = ({ sectionIds }: HeroSectionProps) => {
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
    <section id="landing" className="relative z-20 h-[100svh] min-h-[720px] overflow-hidden bg-black text-white">
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

      <FloatingNav sectionIds={sectionIds} />

      <div className="pointer-events-none relative mx-auto h-full w-full max-w-[1400px] px-4 pb-8 pt-20 sm:px-6 md:px-10">
        <div className="px-1 py-2 text-xs uppercase tracking-[0.32em] text-white/88 sm:px-0">
          EEG Nexus
        </div>

        <div className="hidden md:block">
          <h1 className="hero-title absolute left-[5%] top-[17%] z-10 text-[13vw] font-extrabold uppercase leading-none">
            decode
          </h1>
          <p className="absolute left-[7%] top-[47%] z-20 max-w-[330px] text-sm leading-7 text-white/78">
            Real-time EEG interface for motor imagery decoding, scene switching, and live monitoring.
          </p>
          <h1 className="hero-title absolute right-[4%] top-[37%] z-10 text-[13vw] font-extrabold uppercase leading-none">
            brain
          </h1>
          <h1 className="hero-title absolute left-[31%] top-[57%] z-10 text-[13vw] font-extrabold uppercase leading-none">
            intent
          </h1>

          <HeroMetric value="3-class" label="Left / Right / Feet" className="bottom-[8%] left-[7%]" lineClassName="-rotate-[20deg]" />
          <HeroMetric value="8ch" label="Motor imagery EEG" className="right-[7%] top-[22%]" lineClassName="order-first rotate-[20deg]" />
          <HeroMetric value="250Hz" label="Streaming window" className="bottom-[8%] right-[7%]" lineClassName="order-first -rotate-[20deg]" />
        </div>

        <div className="flex h-full flex-col justify-end pb-12 pt-10 md:hidden">
          <div className="max-w-[320px]">
            <p className="text-[11px] uppercase tracking-[0.34em] text-white/52">motor imagery interface</p>
            <h1 className="hero-title mt-5 text-[2.5rem] font-extrabold uppercase leading-[0.84] sm:text-[2.85rem]">
              Decode
              <br />
              Brain
              <br />
              Intent
            </h1>
            <p className="mt-5 text-sm leading-7 text-white/72">
              Real-time EEG interface for motor imagery decoding, scene switching, and live monitoring.
            </p>
          </div>

          <div className="mt-10 grid grid-cols-3 gap-3 text-left">
            {[
              ['3-class', 'Left / Right / Feet'],
              ['8ch', 'Motor imagery EEG'],
              ['250Hz', 'Streaming window'],
            ].map(([value, label]) => (
              <div key={value} className="rounded-[24px] border border-white/10 bg-black/28 px-4 py-4 backdrop-blur-sm">
                <p className="text-xl tracking-[-0.04em] text-white">{value}</p>
                <p className="mt-2 text-[10px] uppercase tracking-[0.24em] text-white/55">{label}</p>
              </div>
            ))}
          </div>
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
