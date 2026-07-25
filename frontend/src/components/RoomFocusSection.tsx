import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react'

import { cn } from '@/lib/utils'

const MAX_ANGLE = 6
const SECURITY_VIDEO_FPS = 30

const SECURITY_MODES = [
  {
    id: 'relax',
    label: 'Relax Mode',
    eyebrow: 'relax mode',
    title: 'Relax mode settles the room into a quiet ambient pause.',
    body: 'Light softens, visual noise falls away, and the environment becomes a calm space for recovery, reflection, and slower breathing.',
    meta: 'ambient state',
    rangeLabel: '17.20',
    targetTime: 17 + 20 / SECURITY_VIDEO_FPS,
  },
  {
    id: 'focus',
    label: 'Focus Mode',
    eyebrow: 'focus mode',
    title: 'Focus mode turns the room into a precise working space.',
    body: 'The scene narrows attention around the task at hand, balancing clarity and structure for concentrated work, learning, and decision making.',
    meta: 'precision state',
    rangeLabel: '01.00',
    targetTime: 1,
  },
  {
    id: 'party',
    label: 'Party Mode',
    eyebrow: 'party mode',
    title: 'Party mode shifts the room into a vivid social atmosphere.',
    body: 'Color and energy rise together, transforming the same physical space into an expressive setting for music, play, and shared moments.',
    meta: 'social state',
    rangeLabel: '09.10',
    targetTime: 9 + 10 / SECURITY_VIDEO_FPS,
  },
] as const

type SecurityMode = (typeof SECURITY_MODES)[number]['id']

const MODE_BY_ID = SECURITY_MODES.reduce<Record<SecurityMode, (typeof SECURITY_MODES)[number]>>(
  (collection, mode) => {
    collection[mode.id] = mode
    return collection
  },
  {} as Record<SecurityMode, (typeof SECURITY_MODES)[number]>,
)

const getSecurityModeAtTime = (time: number): SecurityMode => {
  if (time >= MODE_BY_ID.relax.targetTime || time < MODE_BY_ID.focus.targetTime) {
    return 'relax'
  }

  if (time >= MODE_BY_ID.party.targetTime) {
    return 'party'
  }

  return 'focus'
}

export interface RoomFocusSectionHandle {
  isFocused: () => boolean
  exitFocusMode: () => void
}

export const RoomFocusSection = forwardRef<RoomFocusSectionHandle>(function RoomFocusSection(_, ref) {
  const roomInnerRef = useRef<HTMLDivElement | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const isZoomedRef = useRef(false)
  const [isZoomed, setIsZoomed] = useState(false)
  const [activeMode, setActiveMode] = useState<SecurityMode>('relax')
  const activeModeContent = MODE_BY_ID[activeMode]

  const resetTilt = useCallback(() => {
    const roomInner = roomInnerRef.current
    if (!roomInner) {
      return
    }

    roomInner.style.setProperty('--rx', '0deg')
    roomInner.style.setProperty('--ry', '0deg')
  }, [])

  const exitFocusMode = useCallback(() => {
    const video = videoRef.current

    isZoomedRef.current = false
    setIsZoomed(false)
    resetTilt()

    if (video) {
      void video.play().catch(() => undefined)
    }
  }, [resetTilt])

  useImperativeHandle(
    ref,
    () => ({
      isFocused: () => isZoomedRef.current,
      exitFocusMode,
    }),
    [exitFocusMode],
  )

  useEffect(() => {
    const roomInner = roomInnerRef.current
    if (!roomInner) {
      return
    }

    const setTilt = (rotateX: number, rotateY: number) => {
      roomInner.style.setProperty('--rx', `${rotateX.toFixed(3)}deg`)
      roomInner.style.setProperty('--ry', `${rotateY.toFixed(3)}deg`)
    }

    const handleMouseMove = (event: MouseEvent) => {
      if (isZoomedRef.current) {
        return
      }

      const centerX = window.innerWidth / 2
      const centerY = window.innerHeight / 2
      const offsetX = (event.clientX - centerX) / centerX
      const offsetY = (event.clientY - centerY) / centerY
      setTilt(offsetY * MAX_ANGLE, offsetX * -MAX_ANGLE)
    }

    setTilt(0, 0)
    window.addEventListener('mousemove', handleMouseMove, { passive: true })

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
    }
  }, [])

  const seekToMode = (mode: SecurityMode) => {
    const video = videoRef.current
    if (!video) {
      return
    }

    video.playbackRate = 1
    video.currentTime = MODE_BY_ID[mode].targetTime

    if (isZoomedRef.current) {
      video.pause()
    } else {
      void video.play().catch(() => undefined)
    }
  }

  const handleModeChange = (mode: SecurityMode) => {
    setActiveMode(mode)

    const video = videoRef.current
    if (!video) {
      return
    }

    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
      seekToMode(mode)
    } else {
      video.addEventListener('loadedmetadata', () => seekToMode(mode), { once: true })
    }
  }

  const handleRoomClick = () => {
    const video = videoRef.current
    if (!video || isZoomedRef.current) {
      return
    }

    setActiveMode(getSecurityModeAtTime(video.currentTime))
    isZoomedRef.current = true
    setIsZoomed(true)
    resetTilt()
    video.pause()
  }

  return (
    <section
      id="room-focus"
      data-scroll-section
      className="security-section relative h-[100svh] min-h-[720px] overflow-hidden bg-black text-white"
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 z-10 h-52 bg-gradient-to-b from-black to-transparent" />
      <div className="security-text-gradient pointer-events-none absolute inset-x-0 bottom-0 z-10" />

      <div className="relative mx-auto h-full w-full max-w-[1520px] px-4 sm:px-6 md:px-10">
        <div className="security-mode-control absolute left-1/2 z-30 -translate-x-1/2">
          <div className="security-mode-selector" role="group" aria-label="Jump to room mode">
            {SECURITY_MODES.map((mode) => (
              <button
                key={mode.id}
                type="button"
                data-mode={mode.id}
                className="security-mode-button"
                onClick={() => handleModeChange(mode.id)}
              >
                {mode.label}
              </button>
            ))}
          </div>
        </div>

        <div
          className="stage-container security-stage"
          data-zoomed={isZoomed ? 'true' : 'false'}
          onMouseLeave={() => {
            if (!isZoomedRef.current) {
              resetTilt()
            }
          }}
        >
          <div className="security-stage-hint pointer-events-none absolute inset-x-6 top-6 z-20 flex items-center justify-between sm:inset-x-8">
            <span>mousemove for parallax</span>
            <span>{isZoomed ? 'scroll down to return' : 'click video to inspect the current scene'}</span>
          </div>

          <div
            className="room-outer"
            onClick={handleRoomClick}
            role="button"
            tabIndex={0}
            aria-label="Inspect the current room scene"
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
                className="room-video security-video"
                src="/videos/guardnet-security-custom.mp4"
                autoPlay
                loop
                muted
                playsInline
                preload="auto"
                aria-hidden="true"
              />
              <div className="video-shield" aria-hidden="true" />
            </div>
          </div>

          <div className="info-panel-container" aria-live="polite">
            <div key={activeModeContent.id} className={cn('info-text-group', isZoomed && 'active')}>
              <p className="info-text-eyebrow">{activeModeContent.eyebrow}</p>
              <p className="info-text-meta-label">{activeModeContent.meta}</p>
              <h3 className="info-text-title">{activeModeContent.title}</h3>
              <p className="info-text-body">{activeModeContent.body}</p>
              <div className="info-text-footer">
                <span>button-controlled scene</span>
                <span>{activeModeContent.rangeLabel}</span>
              </div>
            </div>
          </div>

          <div className={cn('security-copy', isZoomed && 'security-copy--hidden')}>
            <h2 className="security-copy__title">
              <span>THOUGHT-ACTIVATED</span>
              <span>ENVIRONMENT</span>
            </h2>
            <p className="security-copy__description">
              From homes and stages to classrooms, meeting rooms, livestream studios, and healthcare spaces, any
              environment you imagine can be awakened by thought and shaped into its ideal atmosphere.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
})
