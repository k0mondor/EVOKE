export type MiClassKey = 'left' | 'right' | 'feet'
export type TopomapId = 'instant' | 'temporal_mean'

export interface RealtimeProbability {
  label: MiClassKey
  value: number
}

export interface EegChannelFrame {
  channel: string
  samples: number[]
}

export interface TopomapSnapshot {
  id: TopomapId
  values: number[]
  timestamp: string
}

export interface PredictionSnapshot {
  label: MiClassKey
  signalCode: 0 | 1 | 2
  confidence: number
  usable: boolean
  modelName: string
}

export interface SignalQualitySnapshot {
  ptp: number
  rms: number
  usable: boolean
}

export interface DeviceActionSnapshot {
  deviceId: string
  action: string
  accepted: boolean
  reason: string
  signalCode: 0 | 1 | 2 | null
}

export type RealtimeMessage =
  | {
      type: 'eeg_frame'
      payload: {
        sampling_rate: number
        channels: Record<string, number[]>
      }
    }
  | {
      type: 'mi_probs'
      payload: {
        label: MiClassKey
        signal_code: 0 | 1 | 2
        probabilities: Record<MiClassKey, number>
        confidence: number
        usable: boolean
        model_name: string
      }
    }
  | {
      type: 'signal_quality'
      payload: SignalQualitySnapshot
    }
  | {
      type: 'topomap'
      payload: TopomapSnapshot[]
    }
  | {
      type: 'device_action'
      payload: {
        device_id: string
        action: string
        accepted: boolean
        reason: string
        signal_code: 0 | 1 | 2 | null
      }
    }
