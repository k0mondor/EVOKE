import { useMemo } from 'react'

import { SectionCard } from '@/components/SectionCard'
import { useRealtimeStore } from '@/stores/realtimeStore'

const buildPath = (samples: number[], width: number, height: number) =>
  samples
    .map((sample, index) => {
      const x = (index / Math.max(samples.length - 1, 1)) * width
      const y = height / 2 - sample * height * 0.34
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')

export const EegWaveformPanel = () => {
  const frames = useRealtimeStore((state) => state.eegFrames)
  const connected = useRealtimeStore((state) => state.connected)

  const paths = useMemo(
    () =>
      frames.map((frame) => ({
        channel: frame.channel,
        path: buildPath(frame.samples, 500, 42),
      })),
    [frames],
  )

  return (
    <SectionCard
      eyebrow="waveform"
      title="Live EEG stream"
      description="The current version uses a frontend demo stream to emulate multi-channel rolling motion. It can later be replaced by real WebSocket frames."
      className="min-h-[360px]"
    >
      <div className="mb-4 flex items-center justify-between text-xs text-black/45">
        <span>{connected ? 'stream online' : 'stream offline'}</span>
        <span>8 channels / 500 Hz</span>
      </div>
      <div className="space-y-3">
        {paths.map((item) => (
          <div key={item.channel} className="grid grid-cols-[40px_1fr] items-center gap-3">
            <span className="text-[11px] uppercase tracking-[0.18em] text-black/35">{item.channel}</span>
            <div className="overflow-hidden rounded-2xl bg-white/30 p-2">
              <svg viewBox="0 0 500 42" className="h-10 w-full">
                <defs>
                  <linearGradient id={`wave-${item.channel}`} x1="0%" x2="100%" y1="0%" y2="0%">
                    <stop offset="0%" stopColor="rgba(155,197,255,0.25)" />
                    <stop offset="48%" stopColor="rgba(201,235,255,0.95)" />
                    <stop offset="100%" stopColor="rgba(82,134,255,0.35)" />
                  </linearGradient>
                </defs>
                <path
                  d="M 0 21 L 500 21"
                  stroke="rgba(0,0,0,0.08)"
                  strokeDasharray="2 7"
                  strokeWidth="1"
                  fill="none"
                />
                <path d={item.path} stroke={`url(#wave-${item.channel})`} strokeWidth="1.75" fill="none" />
              </svg>
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  )
}
