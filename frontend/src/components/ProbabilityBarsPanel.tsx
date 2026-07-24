import { Activity } from 'lucide-react'

import { SectionCard } from '@/components/SectionCard'
import { useRealtimeStore } from '@/stores/realtimeStore'

const LABELS: Record<string, string> = {
  left: 'Left Hand',
  right: 'Right Hand',
  feet: 'Feet',
}

export const ProbabilityBarsPanel = () => {
  const probabilities = useRealtimeStore((state) => state.probabilities)
  const active = probabilities.reduce<(typeof probabilities)[number] | null>(
    (current, item) => (!current || item.value > current.value ? item : current),
    null,
  )

  return (
    <SectionCard
      eyebrow="classification"
      title="Three-class confidence"
      description="Dynamic probability bars visualize the current confidence of left, right, and feet classes. The values can later be replaced by backend inference output."
      className="min-h-[360px]"
    >
      <div className="mb-6 flex items-center gap-3 rounded-2xl bg-[#f4f4f4] px-4 py-3">
        <div className="rounded-full bg-[#7da8ff]/14 p-2 text-[#587dcb]">
          <Activity className="h-4 w-4" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-black/38">dominant intent</p>
          <p className="mt-1 text-sm text-[#121318]">{active ? LABELS[active.label] : 'Awaiting stream'}</p>
        </div>
      </div>
      <div className="space-y-4">
        {probabilities.map((item) => (
          <div key={item.label} className="space-y-2">
            <div className="flex items-center justify-between text-sm text-black/72">
              <span>{LABELS[item.label]}</span>
              <span>{Math.round(item.value * 100)}%</span>
            </div>
            <div className="h-12 overflow-hidden rounded-[20px] bg-[#f5f5f5] p-1">
              <div
                className="h-full rounded-[16px] bg-[linear-gradient(90deg,rgba(89,137,255,0.22),rgba(171,212,255,0.86),rgba(97,180,255,0.55))] shadow-[0_10px_30px_rgba(80,130,255,0.18)] transition-[width] duration-700"
                style={{ width: `${Math.max(12, item.value * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  )
}
