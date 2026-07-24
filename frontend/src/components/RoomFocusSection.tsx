import { useEffect, useRef, useState } from 'react'

import { cn } from '@/lib/utils'

const MAX_ANGLE = 6

const ROOM_SEGMENTS = [
  {
    id: 0,
    start: 3.14,
    end: 11.28,
    eyebrow: 'focus mode',
    title: 'Focus mode frames the room as a precise operational volume.',
    body: 'Clicking inside this interval freezes the room in its most inspection-heavy state, keeps the right side purely typographic, and makes the left-shift feel intentional rather than decorative.',
    meta: 'segment a',
    rangeLabel: '03.14 - 11.28',
  },
  {
    id: 1,
    start: 11.28,
    end: 20.12,
    eyebrow: 'party mode',
    title: 'Party mode pushes the room into its most kinetic social read.',
    body: 'In this middle segment the composition feels denser and more extroverted, so the enlarged crop can become intentionally aggressive while the right-side copy swaps to a sharper narrative set.',
    meta: 'segment b',
    rangeLabel: '11.28 - 20.12',
  },
  {
    id: 2,
    start: Number.NEGATIVE_INFINITY,
    end: Number.POSITIVE_INFINITY,
    eyebrow: 'relax mode',
    title: 'Relax mode slows the room into a quieter ambient pause.',
    body: 'The last segment reveals the softest state of the room, so the right-side group leans calmer and more spacious while the paused frame feels more architectural than energetic.',
    meta: 'segment c',
    rangeLabel: 'elsewhere',
  },
] as const

const findSegmentIndex = (currentTime: number) => {
  const exactIndex = ROOM_SEGMENTS.findIndex((segment) => currentTime >= segment.start && currentTime < segment.end)
  if (exactIndex >= 0) {
    return exactIndex
  }

  return ROOM_SEGMENTS.reduce(
    (closestIndex, segment, index, collection) => {
      const segmentCenter = (segment.start + segment.end) / 2
      const closestCenter = (collection[closestIndex].start + collection[closestIndex].end) / 2
      return Math.abs(currentTime - segmentCenter) < Math.abs(currentTime - closestCenter) ? index : closestIndex
    },
    0,
  )
}

export const RoomFocusSection = () => {
  const roomInnerRef = useRef<HTMLDivElement | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const isZoomedRef = useRef(false)
  const [isZoomed, setIsZoomed] = useState(false)
  const [activeSegmentIndex, setActiveSegmentIndex] = useState<number | null>(null)

  useEffect(() => {
    const roomInner = roomInnerRef.current
    if (!roomInner) {
      return
    }

    const setTilt = (rotateX: number, rotateY: number) => {
      roomInner.style.setProperty('--rx', `${rotateX.toFixed(3)}deg`)
      roomInner.style.setProperty('--ry', `${rotateY.toFixed(3)}deg`)
    }

    const resetTilt = () => {
      setTilt(0, 0)
    }

    const handleMouseMove = (event: MouseEvent) => {
      if (isZoomedRef.current) {
        return
      }

      const centerX = window.innerWidth / 2
      const centerY = window.innerHeight / 2
      const offsetX = (event.clientX - centerX) / centerX
      const offsetY = (event.clientY - centerY) / centerY
      const rotateX = offsetY * MAX_ANGLE
      const rotateY = offsetX * -MAX_ANGLE
      setTilt(rotateX, rotateY)
    }

    const handleWheel = (event: WheelEvent) => {
      if (!isZoomedRef.current || event.deltaY <= 0) {
        return
      }

      const video = videoRef.current
      if (!video) {
        return
      }

      isZoomedRef.current = false
      setIsZoomed(false)
      setActiveSegmentIndex(null)
      resetTilt()
      void video.play().catch(() => {})
    }

    resetTilt()
    window.addEventListener('mousemove', handleMouseMove, { passive: true })
    window.addEventListener('wheel', handleWheel, { passive: true })

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('wheel', handleWheel)
    }
  }, [])

  const exitZoom = () => {
    const video = videoRef.current
    const roomInner = roomInnerRef.current
    if (!video || !roomInner || !isZoomedRef.current) {
      return
    }

    isZoomedRef.current = false
    setIsZoomed(false)
    setActiveSegmentIndex(null)
    roomInner.style.setProperty('--rx', '0deg')
    roomInner.style.setProperty('--ry', '0deg')
    void video.play().catch(() => {})
  }

  const handleRoomClick = () => {
    const video = videoRef.current
    const roomInner = roomInnerRef.current
    if (!video || !roomInner) {
      return
    }

    if (isZoomedRef.current) {
      exitZoom()
      return
    }

    const index = findSegmentIndex(video.currentTime)
    isZoomedRef.current = true
    setIsZoomed(true)
    setActiveSegmentIndex(index)
    roomInner.style.setProperty('--rx', '0deg')
    roomInner.style.setProperty('--ry', '0deg')
    video.pause()
  }

  const handleStageLeave = () => {
    if (isZoomedRef.current || !roomInnerRef.current) {
      return
    }

    roomInnerRef.current.style.setProperty('--rx', '0deg')
    roomInnerRef.current.style.setProperty('--ry', '0deg')
  }

  return (
    <section id="room-focus" className="relative bg-black px-4 pb-[18vh] pt-[24vh] sm:px-6 md:px-10 md:pb-[24vh] md:pt-[34vh]">
      <div className="mx-auto max-w-[1400px]">
        <div className="mb-10 max-w-[760px]">
          <p className="text-[11px] uppercase tracking-[0.34em] text-white/42">room focus module</p>
          <h2 className="mt-4 text-4xl font-light tracking-[-0.055em] text-white sm:text-5xl md:text-[4.35rem] md:leading-[0.94]">
            Pause the room, inspect the state, then return it to motion.
          </h2>
          <p className="mt-5 max-w-[560px] text-sm leading-7 text-white/58 sm:text-base">
            This new module lives between the hero and the photo strip. The room stays centered by default, follows your
            cursor in subtle 3D, and opens a pure typography panel only when you click into a matching time segment.
          </p>
        </div>

        <div
          className="stage-container relative overflow-visible rounded-[34px] bg-black"
          data-zoomed={isZoomed ? 'true' : 'false'}
          onMouseLeave={handleStageLeave}
        >
          <div className="pointer-events-none absolute inset-x-6 top-6 z-20 flex items-center justify-between text-[10px] uppercase tracking-[0.3em] text-white/28 sm:inset-x-8">
            <span>mousemove for parallax</span>
            <span>{isZoomed ? 'click room or wheel down to exit' : 'click room to inspect segment'}</span>
          </div>

          <div
            className="room-outer"
            onClick={handleRoomClick}
            role="button"
            tabIndex={0}
            aria-label="Toggle room focus mode"
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                handleRoomClick()
              }
            }}
          >
            <div ref={roomInnerRef} className="room-inner">
              <video
                ref={videoRef}
                className="room-video"
                src="/videos/guardnet-security-custom.mp4"
                autoPlay
                loop
                muted
                playsInline
                preload="auto"
                aria-hidden="true"
              />
            </div>
          </div>

          <div className="info-panel-container" aria-live="polite">
            {ROOM_SEGMENTS.map((segment, index) => (
              <div
                key={segment.id}
                className={cn('info-text-group', activeSegmentIndex === index && isZoomed && 'active')}
              >
                <p className="info-text-eyebrow">{segment.eyebrow}</p>
                <p className="info-text-meta-label">{segment.meta}</p>
                <h3 className="info-text-title">{segment.title}</h3>
                <p className="info-text-body">{segment.body}</p>
                <div className="info-text-footer">
                  <span>pause-driven state reveal</span>
                  <span>{segment.rangeLabel}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
