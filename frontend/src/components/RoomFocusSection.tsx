import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react'

import { cn } from '@/lib/utils'

const MAX_ANGLE = 3.5
const SECURITY_VIDEO_FPS = 30

const SECURITY_MODES = [
  {
    id: 'relax',
    label: 'Relax Mode',
    title: 'Unwind',
    body: 'A quiet space that lets the day fall away.',
    features: [
      'Warm ambient lights on',
      'Bedside lights dimmed',
      'Curtains closed',
      'White noise playing',
      'TV off · Calm wallpaper on',
    ],
    targetTime: 17 + 20 / SECURITY_VIDEO_FPS,
  },
  {
    id: 'focus',
    label: 'Focus Mode',
    title: 'Deep Focus',
    body: 'Clear the room. Enter your flow.',
    features: [
      'Cool-white task lights on',
      'Desk lighting brightened',
      'Curtains fully open',
      'Focus playlist playing',
      'TV off · Work display active',
    ],
    targetTime: 1,
  },
  {
    id: 'party',
    label: 'Party Mode',
    title: 'Game Night',
    body: 'Turn the room into part of the crowd.',
    features: [
      'Color light strips on',
      'Curtains half open',
      'Live match playing on TV',
      'Game running on monitor',
      'Party audio mode on',
    ],
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
  const stageRef = useRef<HTMLDivElement | null>(null)
  const roomInnerRef = useRef<HTMLDivElement | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const focusTimerRef = useRef<number | undefined>(undefined)
  const switchTimerRef = useRef<number | undefined>(undefined)
  const pendingModeRef = useRef<SecurityMode | null>(null)
  const isZoomedRef = useRef(false)
  const [isZoomed, setIsZoomed] = useState(false)
  const [isDetailsVisible, setIsDetailsVisible] = useState(false)
  const [isSwitching, setIsSwitching] = useState(false)
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
    setIsDetailsVisible(false)
    resetTilt()

    if (focusTimerRef.current !== undefined) {
      window.clearTimeout(focusTimerRef.current)
    }
    focusTimerRef.current = window.setTimeout(() => {
      setIsZoomed(false)
    }, 340)

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
    const stage = stageRef.current
    const roomInner = roomInnerRef.current
    if (!stage || !roomInner) {
      return
    }

    const setTilt = (rotateX: number, rotateY: number) => {
      roomInner.style.setProperty('--rx', `${rotateX.toFixed(3)}deg`)
      roomInner.style.setProperty('--ry', `${rotateY.toFixed(3)}deg`)
    }

    const handlePointerMove = (event: PointerEvent) => {
      if (isZoomedRef.current) {
        return
      }

      const bounds = stage.getBoundingClientRect()
      const centerX = bounds.left + bounds.width / 2
      const centerY = bounds.top + bounds.height / 2
      const offsetX = (event.clientX - centerX) / (bounds.width / 2)
      const offsetY = (event.clientY - centerY) / (bounds.height / 2)
      setTilt(offsetY * MAX_ANGLE, offsetX * -MAX_ANGLE)
    }

    setTilt(0, 0)
    stage.addEventListener('pointermove', handlePointerMove, { passive: true })
    stage.addEventListener('pointerleave', resetTilt)

    return () => {
      stage.removeEventListener('pointermove', handlePointerMove)
      stage.removeEventListener('pointerleave', resetTilt)
    }
  }, [resetTilt])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isZoomedRef.current) {
        exitFocusMode()
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      if (focusTimerRef.current !== undefined) {
        window.clearTimeout(focusTimerRef.current)
      }
      if (switchTimerRef.current !== undefined) {
        window.clearTimeout(switchTimerRef.current)
      }
    }
  }, [exitFocusMode])

  const seekToMode = (mode: SecurityMode) => {
    const video = videoRef.current
    if (!video) {
      return
    }

    pendingModeRef.current = mode
    video.playbackRate = 1
    video.currentTime = MODE_BY_ID[mode].targetTime

    if (isZoomedRef.current) {
      video.pause()
    } else {
      void video.play().catch(() => undefined)
    }
  }

  const handleModeChange = (mode: SecurityMode) => {
    pendingModeRef.current = mode
    setActiveMode(mode)
    setIsSwitching(true)

    if (switchTimerRef.current !== undefined) {
      window.clearTimeout(switchTimerRef.current)
    }
    switchTimerRef.current = window.setTimeout(() => {
      setIsSwitching(false)
    }, 420)

    const video = videoRef.current
    if (!video) {
      return
    }

    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
      seekToMode(mode)
    } else {
      video.addEventListener(
        'loadedmetadata',
        () => {
          if (pendingModeRef.current === mode) {
            seekToMode(mode)
          }
        },
        { once: true },
      )
    }
  }

  const handleRoomClick = () => {
    const video = videoRef.current
    if (!video) {
      return
    }

    if (isZoomedRef.current) {
      exitFocusMode()
      return
    }

    setActiveMode(getSecurityModeAtTime(video.currentTime))
    isZoomedRef.current = true
    setIsDetailsVisible(false)
    setIsZoomed(true)
    resetTilt()
    video.pause()

    if (focusTimerRef.current !== undefined) {
      window.clearTimeout(focusTimerRef.current)
    }
    focusTimerRef.current = window.setTimeout(() => {
      setIsDetailsVisible(true)
    }, 520)
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
                data-active={activeMode === mode.id ? 'true' : 'false'}
                className="security-mode-button"
                onClick={() => handleModeChange(mode.id)}
                aria-pressed={activeMode === mode.id}
              >
                <span className="security-mode-button__label">{mode.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div
          ref={stageRef}
          className="stage-container security-stage"
          data-zoomed={isZoomed ? 'true' : 'false'}
          data-switching={isSwitching ? 'true' : 'false'}
        >
          <div className="security-stage-hint pointer-events-none absolute inset-x-6 top-6 z-20 flex items-center justify-between sm:inset-x-8">
            <span>move to explore</span>
            <span>{isZoomed ? 'click room or press esc to return' : 'click room to inspect the current scene'}</span>
          </div>

          <button
            type="button"
            className="security-exit-button"
            data-visible={isDetailsVisible ? 'true' : 'false'}
            onClick={exitFocusMode}
            aria-label="Exit scene inspection"
            tabIndex={isDetailsVisible ? 0 : -1}
          >
            <span>Close</span>
            <span aria-hidden="true">×</span>
          </button>

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
                onTimeUpdate={(event) => {
                  if (pendingModeRef.current) {
                    return
                  }

                  const mode = getSecurityModeAtTime(event.currentTarget.currentTime)
                  setActiveMode((currentMode) => (currentMode === mode ? currentMode : mode))
                }}
                onSeeked={() => {
                  const pendingMode = pendingModeRef.current
                  if (!pendingMode) {
                    return
                  }

                  pendingModeRef.current = null
                  setActiveMode(pendingMode)
                }}
              />
              <div className="video-shield" aria-hidden="true" />
            </div>
          </div>

          <div className="info-panel-container" aria-live="polite">
            <div
              key={activeModeContent.id}
              className={cn('info-text-group', isDetailsVisible && 'active')}
              data-mode={activeModeContent.id}
            >
              <h3 className="info-text-title">{activeModeContent.title}</h3>
              <p className="info-text-body">{activeModeContent.body}</p>
              <ul className="info-feature-list">
                {activeModeContent.features.map((feature) => (
                  <li key={feature}>
                    <span className="info-feature-check" aria-hidden="true">
                      ✓
                    </span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
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
