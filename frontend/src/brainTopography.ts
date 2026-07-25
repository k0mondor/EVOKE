import type { BrainSignalFrame } from '@/brainSignal'

export interface ResolvedSensor {
  channel: string
  x: number
  y: number
  value: number
}

export type SensorPosition = [number, number]

export const TOPOGRAPHY_COLORS = {
  negative: '#d56cff',
  neutral: '#1aadd9',
  positive: '#f57829',
} as const

const STANDARD_1020_POSITIONS: Record<string, [number, number]> = {
  FP1: [-0.34, 0.82],
  FP2: [0.34, 0.82],
  AF7: [-0.62, 0.69],
  AF3: [-0.28, 0.66],
  AFZ: [0, 0.69],
  AF4: [0.28, 0.66],
  AF8: [0.62, 0.69],
  F7: [-0.72, 0.5],
  F3: [-0.4, 0.47],
  FZ: [0, 0.5],
  F4: [0.4, 0.47],
  F8: [0.72, 0.5],
  T7: [-0.82, 0],
  C3: [-0.52, 0.02],
  CZ: [0, 0],
  C4: [0.52, 0.02],
  T8: [0.82, 0],
  P7: [-0.7, -0.46],
  P3: [-0.38, -0.43],
  PZ: [0, -0.46],
  P4: [0.38, -0.43],
  P8: [0.7, -0.46],
  O1: [-0.27, -0.78],
  OZ: [0, -0.82],
  O2: [0.27, -0.78],
}

// The production device is a forehead headband: all eight unnamed electrodes
// sit along one anterior arc, ordered from the wearer's left to right.
export const FRONTAL_8_CHANNEL_POSITIONS: SensorPosition[] = [
  [-0.72, 0.66],
  [-0.51, 0.74],
  [-0.3, 0.8],
  [-0.1, 0.83],
  [0.1, 0.83],
  [0.3, 0.8],
  [0.51, 0.74],
  [0.72, 0.66],
]

const COLOR_CHANNELS = {
  negative: [213, 108, 255],
  neutral: [26, 173, 217],
  positive: [245, 120, 41],
} as const

const mix = (from: readonly number[], to: readonly number[], amount: number) =>
  from.map((value, index) => Math.round(value + (to[index] - value) * amount))

export const colorChannelsForValue = (value: number) => {
  const normalized = Math.max(-1, Math.min(1, value))
  return normalized < 0
    ? mix(COLOR_CHANNELS.negative, COLOR_CHANNELS.neutral, normalized + 1)
    : mix(COLOR_CHANNELS.neutral, COLOR_CHANNELS.positive, normalized)
}

export const colorForValue = (value: number) => {
  const [red, green, blue] = colorChannelsForValue(value)
  return `rgb(${red}, ${green}, ${blue})`
}

export const resolveTopographySensors = (
  frame: BrainSignalFrame,
  positionOverrides?: SensorPosition[],
): ResolvedSensor[] => {
  const names = frame.topomap.channelNames
  const values = frame.topomap.values
  const mean = values.reduce((sum, value) => sum + value, 0) / Math.max(1, values.length)
  const centered = values.map((value) => value - mean)
  const scale = Math.max(1e-6, ...centered.map((value) => Math.abs(value)))

  return values.map((_, index) => {
    const channel = names[index] ?? `CH${index + 1}`
    const standardPosition = STANDARD_1020_POSITIONS[channel.toUpperCase()]
    const manualPosition = positionOverrides?.[index]
    const fallbackPosition =
      FRONTAL_8_CHANNEL_POSITIONS[index] ??
      ([
        Math.cos((index / Math.max(1, values.length)) * Math.PI) * 0.74,
        0.48 + Math.sin((index / Math.max(1, values.length)) * Math.PI) * 0.34,
      ] as [number, number])
    const [x, y] = manualPosition ?? standardPosition ?? fallbackPosition

    return {
      channel,
      x,
      y,
      value: centered[index] / scale,
    }
  })
}
