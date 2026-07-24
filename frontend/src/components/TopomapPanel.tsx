import { useMemo, useState } from 'react'

import { SectionCard } from '@/components/SectionCard'
import { cn } from '@/lib/utils'
import { useRealtimeStore } from '@/stores/realtimeStore'

interface TopomapPanelProps {
  id: 'instant' | 'temporal_mean'
  eyebrow: string
  title: string
  description: string
}

const ELECTRODE_POINTS = [
  ['26%', '33%'],
  ['70%', '32%'],
  ['34%', '58%'],
  ['66%', '58%'],
  ['50%', '76%'],
] as const

const formatMode = (value: number) => `${50 + value * 40}%`

export const TopomapPanel = ({ id, eyebrow, title, description }: TopomapPanelProps) => {
  const [rotation, setRotation] = useState(0)
  const topomap = useRealtimeStore((state) => state.topomaps.find((item) => item.id === id))

  const background = useMemo(() => {
    if (!topomap) {
      return undefined
    }

    const [a, b, c, d, e, f] = topomap.values
    return {
      background: `radial-gradient(circle at ${formatMode(a)} ${formatMode(b)}, rgba(34,34,34,0.34), transparent 32%),
        radial-gradient(circle at ${formatMode(c)} ${formatMode(d)}, rgba(18,18,18,0.42), transparent 34%),
        radial-gradient(circle at ${formatMode(e)} ${formatMode(f)}, rgba(56,56,56,0.26), transparent 28%),
        radial-gradient(circle at 50% 52%, rgba(255,255,255,0.14), transparent 68%)`,
    }
  }, [topomap])

  const handleWheel = (event: React.WheelEvent<HTMLDivElement>) => {
    event.preventDefault()
    setRotation((prev) => prev + event.deltaY * 0.08)
  }

  return (
    <SectionCard eyebrow={eyebrow} title={title} description={description} className="min-h-[320px]">
      <div className="flex items-center justify-between text-xs text-black/45">
        <span>{id === 'instant' ? 'instant topomap' : 'temporal mean topomap'}</span>
        <span>{topomap?.timestamp.slice(11, 19) ?? '--:--:--'}</span>
      </div>
      <div className="mt-5 flex items-center justify-center">
        <div
          className="relative flex aspect-square w-[min(74vw,250px)] items-center justify-center"
          onWheel={handleWheel}
        >
          <div className="absolute inset-[10%] rounded-full bg-[radial-gradient(circle,rgba(82,140,255,0.18),transparent_70%)] blur-2xl" />
          <div
            className={cn(
              'relative aspect-square w-full rounded-full bg-[#f4f4f4] transition-transform duration-300 ease-out',
            )}
            style={{
              ...background,
              transform: `rotate(${rotation}deg)`,
            }}
          >
            <div className="absolute inset-[7%] rounded-full border border-black/8" />
            <div className="absolute left-1/2 top-[8%] h-4 w-4 -translate-x-1/2 rounded-full border border-black/8 bg-white/30" />
            <div className="absolute left-1/2 top-1 h-8 w-px -translate-x-1/2 bg-black/12" />
            {ELECTRODE_POINTS.map(([left, top], index) => (
              <span
                key={`${left}-${top}-${index}`}
                className="absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-black/10 bg-white/34"
                style={{ left, top }}
              />
            ))}
          </div>
        </div>
      </div>
    </SectionCard>
  )
}
