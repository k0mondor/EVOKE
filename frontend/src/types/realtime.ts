export type MiClassKey = 'left' | 'right' | 'feet'

export interface RealtimeProbability {
  label: MiClassKey
  value: number
}

export interface EegChannelFrame {
  channel: string
  samples: number[]
}

export interface TopomapSnapshot {
  id: 'instant' | 'temporal_mean'
  values: number[]
  timestamp: string
}
