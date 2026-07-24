import { create } from 'zustand'

import type {
  DeviceActionSnapshot,
  EegChannelFrame,
  MiClassKey,
  PredictionSnapshot,
  RealtimeMessage,
  RealtimeProbability,
  SignalQualitySnapshot,
  TopomapSnapshot,
} from '@/types/realtime'

const CHANNEL_NAMES = ['CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'CH6', 'CH7', 'CH8']

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

const buildProbabilitiesFromMap = (probabilities: Record<MiClassKey, number>): RealtimeProbability[] =>
  (['left', 'right', 'feet'] as MiClassKey[]).map((label) => ({
    label,
    value: probabilities[label] ?? 0,
  }))

interface RealtimeStore {
  connected: boolean
  samplingRate: number
  eegFrames: EegChannelFrame[]
  probabilities: RealtimeProbability[]
  topomaps: TopomapSnapshot[]
  prediction: PredictionSnapshot | null
  signalQuality: SignalQualitySnapshot | null
  deviceAction: DeviceActionSnapshot | null
  setConnected: (connected: boolean) => void
  ingestMessage: (message: RealtimeMessage) => void
}

export const useRealtimeStore = create<RealtimeStore>((set) => ({
  connected: false,
  samplingRate: 500,
  eegFrames: buildEegFrames(0),
  probabilities: pickProbabilities(0),
  topomaps: [buildTopomap('instant', 0), buildTopomap('temporal_mean', 1.2)],
  prediction: null,
  signalQuality: null,
  deviceAction: null,
  setConnected: (connected) => set({ connected }),
  ingestMessage: (message) => {
    switch (message.type) {
      case 'eeg_frame':
        set({
          samplingRate: message.payload.sampling_rate,
          eegFrames: Object.entries(message.payload.channels).map(([channel, samples]) => ({
            channel,
            samples,
          })),
        })
        return
      case 'mi_probs':
        set({
          probabilities: buildProbabilitiesFromMap(message.payload.probabilities),
          prediction: {
            label: message.payload.label,
            signalCode: message.payload.signal_code,
            confidence: message.payload.confidence,
            usable: message.payload.usable,
            modelName: message.payload.model_name,
          },
        })
        return
      case 'signal_quality':
        set({
          signalQuality: {
            ptp: message.payload.ptp,
            rms: message.payload.rms,
            usable: message.payload.usable,
          },
        })
        return
      case 'topomap':
        set({ topomaps: message.payload })
        return
      case 'device_action':
        set({
          deviceAction: {
            deviceId: message.payload.device_id,
            action: message.payload.action,
            accepted: message.payload.accepted,
            reason: message.payload.reason,
            signalCode: message.payload.signal_code,
          },
        })
        return
    }
  },
}))
