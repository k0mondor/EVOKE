import { create } from 'zustand'

import type {
  EegChannelFrame,
  MiClassKey,
  RealtimeProbability,
  TopomapSnapshot,
} from '@/types/realtime'

const CHANNEL_NAMES = ['Fp1', 'Fp2', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2']

const seedWave = (phase: number, amplitude: number) =>
  Array.from({ length: 72 }, (_, index) => {
    const x = index / 8
    return Math.sin(x + phase) * amplitude + Math.cos(x * 0.6 + phase * 0.5) * amplitude * 0.35
  })

const buildEegFrames = (phase: number): EegChannelFrame[] =>
  CHANNEL_NAMES.map((channel, index) => ({
    channel,
    samples: seedWave(phase + index * 0.45, 0.38 + index * 0.02),
  }))

const pickProbabilities = (phase: number): RealtimeProbability[] => {
  const values = [
    0.4 + Math.sin(phase) * 0.22,
    0.33 + Math.sin(phase + 2.2) * 0.2,
    0.27 + Math.sin(phase + 4.1) * 0.18,
  ].map((value) => Math.max(0.08, value))

  const total = values.reduce((sum, value) => sum + value, 0)
  const labels: MiClassKey[] = ['left', 'right', 'feet']

  return labels.map((label, index) => ({
    label,
    value: values[index] / total,
  }))
}

const buildTopomap = (id: TopomapSnapshot['id'], phase: number): TopomapSnapshot => ({
  id,
  values: Array.from({ length: 12 }, (_, index) => {
    const wave = Math.sin(phase + index * 0.72)
    const mod = Math.cos(phase * 0.45 + index * 0.34)
    return (wave + mod) * 0.5
  }),
  timestamp: new Date().toISOString(),
})

interface RealtimeStore {
  connected: boolean
  eegFrames: EegChannelFrame[]
  probabilities: RealtimeProbability[]
  topomaps: TopomapSnapshot[]
  tick: number
  setConnected: (connected: boolean) => void
  hydrateDemo: () => void
}

export const useRealtimeStore = create<RealtimeStore>((set, get) => ({
  connected: false,
  eegFrames: buildEegFrames(0),
  probabilities: pickProbabilities(0),
  topomaps: [buildTopomap('instant', 0), buildTopomap('temporal_mean', 1.2)],
  tick: 0,
  setConnected: (connected) => set({ connected }),
  hydrateDemo: () => {
    const nextTick = get().tick + 1
    const phase = nextTick * 0.28
    set({
      tick: nextTick,
      eegFrames: buildEegFrames(phase),
      probabilities: pickProbabilities(phase),
      topomaps: [
        buildTopomap('instant', phase),
        buildTopomap('temporal_mean', phase * 0.68 + 0.8),
      ],
    })
  },
}))
