import { useCallback, useEffect, useRef, useState } from 'react'

export type BrainSignalSource = 'demo' | 'device'
export type BrainConnectionState = 'demo' | 'connecting' | 'live'
export type AcquisitionState = 'idle' | 'connecting' | 'running' | 'stopped'
export type InferenceState = 'idle' | 'collecting' | 'inferring' | 'complete' | 'cancelled'
export type StreamState = 'idle' | 'disconnected' | 'waiting_for_bytes' | 'partial_frame' | 'streaming'

export interface InferenceFinalResult {
  label: string
  confidence: number
  probabilities: Record<string, number>
  windowCount: number
  completedAt: number
}

export interface BrainRuntimeStatus {
  sourceMode: string
  acquisitionState: AcquisitionState
  inferenceState: InferenceState
  collectionWindowsCollected: number
  collectionWindowsTarget: number
  windowsCollected: number
  windowsTarget: number
  progress: number
  finalResult: InferenceFinalResult | null
  error: string | null
  streamState: StreamState
  tcpConnected: boolean
  tcpBytesReceived: number
  tcpPendingFrameBytes: number
  tcpExpectedFrameBytes: number
  tcpFramesReceived: number
  tcpLastByteAt: number | null
  tcpLastFrameAt: number | null
}

export interface BrainSignalFrame {
  timestamp: number
  source: BrainSignalSource
  signalQuality: number
  activity: number
  probabilities: {
    mode1: number
    mode2: number
    mode3: number
  }
  bands: {
    delta: number
    theta: number
    alpha: number
    beta: number
    gamma: number
  }
  topomap: {
    channelNames: string[]
    values: number[]
    kind: 'instant' | 'temporal_mean'
    timestamp: string
  }
}

const INITIAL_FRAME: BrainSignalFrame = {
  timestamp: Date.now(),
  source: 'demo',
  signalQuality: 88,
  activity: 0.52,
  probabilities: { mode1: 31, mode2: 39, mode3: 30 },
  bands: { delta: 0.24, theta: 0.36, alpha: 0.72, beta: 0.48, gamma: 0.18 },
  topomap: {
    channelNames: ['CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'CH6', 'CH7', 'CH8'],
    values: [0.2, -0.15, 0.52, -0.45, 0.34, -0.26, 0.12, -0.08],
    kind: 'temporal_mean',
    timestamp: new Date().toISOString(),
  },
}

const INITIAL_RUNTIME_STATUS: BrainRuntimeStatus = {
  sourceMode: 'demo',
  acquisitionState: 'idle',
  inferenceState: 'idle',
  collectionWindowsCollected: 0,
  collectionWindowsTarget: 5,
  windowsCollected: 0,
  windowsTarget: 0,
  progress: 0,
  finalResult: null,
  error: null,
  streamState: 'idle',
  tcpConnected: false,
  tcpBytesReceived: 0,
  tcpPendingFrameBytes: 0,
  tcpExpectedFrameBytes: 328,
  tcpFramesReceived: 0,
  tcpLastByteAt: null,
  tcpLastFrameAt: null,
}

const clamp = (value: number, minimum = 0, maximum = 100) =>
  Math.min(maximum, Math.max(minimum, value))

function createDemoFrame(elapsedSeconds: number): BrainSignalFrame {
  const probabilityWeights = [
    0.72 + Math.sin(elapsedSeconds * 0.43) * 0.28,
    0.72 + Math.sin(elapsedSeconds * 0.43 + 2.1) * 0.28,
    0.72 + Math.sin(elapsedSeconds * 0.43 + 4.2) * 0.28,
  ]
  const probabilityTotal = probabilityWeights.reduce((sum, value) => sum + value, 0)

  return {
    timestamp: Date.now(),
    source: 'demo',
    signalQuality: Math.round(clamp(88 + Math.sin(elapsedSeconds * 0.25) * 5)),
    activity: clamp(0.48 + Math.sin(elapsedSeconds * 1.2) * 0.16, 0, 1),
    probabilities: {
      mode1: (probabilityWeights[0] / probabilityTotal) * 100,
      mode2: (probabilityWeights[1] / probabilityTotal) * 100,
      mode3: (probabilityWeights[2] / probabilityTotal) * 100,
    },
    bands: {
      delta: clamp(0.24 + Math.sin(elapsedSeconds * 0.5) * 0.08, 0, 1),
      theta: clamp(0.36 + Math.sin(elapsedSeconds * 0.82 + 0.7) * 0.1, 0, 1),
      alpha: clamp(0.7 + Math.sin(elapsedSeconds * 0.64 + 1.2) * 0.13, 0, 1),
      beta: clamp(0.48 + Math.sin(elapsedSeconds * 1.08 + 0.3) * 0.11, 0, 1),
      gamma: clamp(0.18 + Math.sin(elapsedSeconds * 1.42 + 1.6) * 0.06, 0, 1),
    },
    topomap: {
      channelNames: INITIAL_FRAME.topomap.channelNames,
      values: INITIAL_FRAME.topomap.channelNames.map((_, index) => {
        const lateral = index % 2 === 0 ? 1 : -1
        const anteriorPosterior = 1 - Math.floor(index / 2) * 0.38
        return clamp(
          Math.sin(elapsedSeconds * 0.82 + index * 0.68) * 0.52 +
            Math.cos(elapsedSeconds * 0.37 + index * 0.31) * 0.22 +
            lateral * Math.sin(elapsedSeconds * 0.23) * 0.2 * anteriorPosterior,
          -1,
          1,
        )
      }),
      kind: 'temporal_mean',
      timestamp: new Date().toISOString(),
    },
  }
}

function normalizeDeviceFrame(value: unknown): BrainSignalFrame | null {
  if (!value || typeof value !== 'object') {
    return null
  }

  const payload = value as Partial<BrainSignalFrame>
  const probabilities = payload.probabilities
  const bands = payload.bands
  if (!probabilities || !bands) {
    return null
  }

  const mode1 = Number(probabilities.mode1)
  const mode2 = Number(probabilities.mode2)
  const mode3 = Number(probabilities.mode3)
  const total = mode1 + mode2 + mode3
  if (![mode1, mode2, mode3, total].every(Number.isFinite) || total <= 0) {
    return null
  }

  return {
    timestamp: Number.isFinite(Number(payload.timestamp)) ? Number(payload.timestamp) : Date.now(),
    source: 'device',
    signalQuality: clamp(Number(payload.signalQuality) || 0),
    activity: clamp(Number(payload.activity) || 0, 0, 1),
    probabilities: {
      mode1: (mode1 / total) * 100,
      mode2: (mode2 / total) * 100,
      mode3: (mode3 / total) * 100,
    },
    bands: {
      delta: clamp(Number(bands.delta) || 0, 0, 1),
      theta: clamp(Number(bands.theta) || 0, 0, 1),
      alpha: clamp(Number(bands.alpha) || 0, 0, 1),
      beta: clamp(Number(bands.beta) || 0, 0, 1),
      gamma: clamp(Number(bands.gamma) || 0, 0, 1),
    },
    topomap: payload.topomap ?? INITIAL_FRAME.topomap,
  }
}

interface RealtimeEnvelope {
  type: string
  timestamp_ms?: number
  payload?: unknown
}

const normalizeProbability = (value: unknown) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return 0
  }
  return numeric <= 1 ? numeric * 100 : numeric
}

function reduceRealtimeEnvelope(current: BrainSignalFrame, message: RealtimeEnvelope): BrainSignalFrame | null {
  if (!message.payload || typeof message.payload !== 'object') {
    return null
  }

  const timestamp = Number(message.timestamp_ms) || Date.now()

  if (message.type === 'eeg_frame') {
    const payload = message.payload as { channels?: unknown }
    if (!payload.channels || typeof payload.channels !== 'object') {
      return null
    }

    const entries = Object.entries(payload.channels as Record<string, unknown>)
      .filter((entry): entry is [string, unknown[]] => Array.isArray(entry[1]))
      .slice(0, 8)
    if (!entries.length) {
      return null
    }

    const values = entries.map(([, samples]) => {
      const numericSamples = samples.map(Number).filter(Number.isFinite)
      if (!numericSamples.length) {
        return 0
      }
      return Math.sqrt(
        numericSamples.reduce((sum, sample) => sum + sample * sample, 0) / numericSamples.length,
      )
    })

    return {
      ...current,
      timestamp,
      source: 'device',
      topomap: {
        channelNames: entries.map(([channel]) => channel),
        values,
        kind: 'temporal_mean',
        timestamp: new Date(timestamp).toISOString(),
      },
    }
  }

  if (message.type === 'mi_probs') {
    const payload = message.payload as {
      probabilities?: Record<string, unknown>
      confidence?: unknown
    }
    const probabilities = payload.probabilities
    if (!probabilities) {
      return null
    }

    const mode1 = normalizeProbability(probabilities.left)
    const mode2 = normalizeProbability(probabilities.right)
    const mode3 = normalizeProbability(probabilities.feet)
    const total = mode1 + mode2 + mode3
    if (total <= 0) {
      return null
    }

    return {
      ...current,
      timestamp,
      source: 'device',
      activity: clamp(Number(payload.confidence) || 0, 0, 1),
      probabilities: {
        mode1: (mode1 / total) * 100,
        mode2: (mode2 / total) * 100,
        mode3: (mode3 / total) * 100,
      },
    }
  }

  if (message.type === 'signal_quality') {
    const payload = message.payload as { usable?: unknown }
    return {
      ...current,
      timestamp,
      source: 'device',
      signalQuality: payload.usable ? Math.max(current.signalQuality, 85) : Math.min(current.signalQuality, 35),
    }
  }

  if (message.type === 'topomap' && Array.isArray(message.payload)) {
    const snapshots = message.payload as Array<{
      id?: unknown
      channel_names?: unknown
      values?: unknown
      timestamp?: unknown
    }>
    const snapshot =
      snapshots.find((item) => item.id === 'temporal_mean') ??
      snapshots.find((item) => item.id === 'instant')
    if (!snapshot || !Array.isArray(snapshot.values)) {
      return null
    }

    const values = snapshot.values.map(Number)
    if (!values.every(Number.isFinite)) {
      return null
    }

    const channelNames = Array.isArray(snapshot.channel_names)
      ? snapshot.channel_names.map(String)
      : values.map((_, index) => `CH${index + 1}`)

    return {
      ...current,
      timestamp,
      source: 'device',
      topomap: {
        channelNames,
        values,
        kind: snapshot.id === 'instant' ? 'instant' : 'temporal_mean',
        timestamp: String(snapshot.timestamp ?? new Date(timestamp).toISOString()),
      },
    }
  }

  return null
}

function normalizeRuntimeStatus(value: unknown): BrainRuntimeStatus | null {
  if (!value || typeof value !== 'object') {
    return null
  }

  const payload = value as Record<string, unknown>
  const acquisitionState = String(payload.acquisition_state ?? 'idle') as AcquisitionState
  const inferenceState = String(payload.inference_state ?? 'idle') as InferenceState
  const finalResultPayload =
    payload.final_result && typeof payload.final_result === 'object'
      ? (payload.final_result as Record<string, unknown>)
      : null

  const finalResult = finalResultPayload
    ? {
        label: String(finalResultPayload.label ?? ''),
        confidence: clamp(Number(finalResultPayload.confidence) || 0, 0, 1),
        probabilities:
          finalResultPayload.probabilities && typeof finalResultPayload.probabilities === 'object'
            ? Object.fromEntries(
                Object.entries(finalResultPayload.probabilities as Record<string, unknown>).map(
                  ([label, probability]) => [label, Number(probability) || 0],
                ),
              )
            : {},
        windowCount: Number(finalResultPayload.window_count) || 0,
        completedAt: Number(finalResultPayload.completed_at_ms) || Date.now(),
      }
    : null

  return {
    sourceMode: String(payload.source_mode ?? 'demo'),
    acquisitionState,
    inferenceState,
    collectionWindowsCollected: Math.max(0, Number(payload.collection_windows_collected) || 0),
    collectionWindowsTarget: Math.max(1, Number(payload.collection_windows_target) || 5),
    windowsCollected: Math.max(0, Number(payload.windows_collected) || 0),
    windowsTarget: Math.max(0, Number(payload.windows_target) || 0),
    progress: clamp(Number(payload.progress) || 0, 0, 1),
    finalResult,
    error: payload.error ? String(payload.error) : null,
    streamState: String(payload.stream_state ?? 'idle') as StreamState,
    tcpConnected: Boolean(payload.tcp_connected),
    tcpBytesReceived: Math.max(0, Number(payload.tcp_bytes_received) || 0),
    tcpPendingFrameBytes: Math.max(0, Number(payload.tcp_pending_frame_bytes) || 0),
    tcpExpectedFrameBytes: Math.max(1, Number(payload.tcp_expected_frame_bytes) || 328),
    tcpFramesReceived: Math.max(0, Number(payload.tcp_frames_received) || 0),
    tcpLastByteAt: payload.tcp_last_byte_at_ms ? Number(payload.tcp_last_byte_at_ms) : null,
    tcpLastFrameAt: payload.tcp_last_frame_at_ms ? Number(payload.tcp_last_frame_at_ms) : null,
  }
}

export function useBrainSignal() {
  const [frame, setFrame] = useState<BrainSignalFrame>(INITIAL_FRAME)
  const [connectionState, setConnectionState] = useState<BrainConnectionState>('demo')
  const [runtimeStatus, setRuntimeStatus] = useState<BrainRuntimeStatus>(INITIAL_RUNTIME_STATUS)
  const [commandMessage, setCommandMessage] = useState('')
  const socketRef = useRef<WebSocket | null>(null)
  const runtimeStatusRef = useRef<BrainRuntimeStatus>(INITIAL_RUNTIME_STATUS)
  const demoJobTimersRef = useRef<number[]>([])
  const demoRunIdRef = useRef(0)
  const demoLockedProbabilitiesRef = useRef<BrainSignalFrame['probabilities'] | null>(null)

  const commitRuntimeStatus = useCallback(
    (update: (current: BrainRuntimeStatus) => BrainRuntimeStatus) => {
      const next = update(runtimeStatusRef.current)
      runtimeStatusRef.current = next
      setRuntimeStatus(next)
    },
    [],
  )

  const clearDemoJob = useCallback(() => {
    demoRunIdRef.current += 1
    demoJobTimersRef.current.forEach((timer) => window.clearTimeout(timer))
    demoJobTimersRef.current = []
  }, [])

  const startDemoRun = useCallback((payload: Record<string, unknown>) => {
    clearDemoJob()
    demoLockedProbabilitiesRef.current = null

    const runId = demoRunIdRef.current
    const collectionTarget = Math.round(clamp(Number(payload.collection_window_count) || 3, 3, 50))
    const inferenceTarget = Math.round(clamp(Number(payload.inference_window_count) || 1, 1, 50))
    let collected = 0
    let inferred = 0

    const queue = (callback: () => void, delay: number) => {
      const timer = window.setTimeout(callback, delay)
      demoJobTimersRef.current.push(timer)
    }

    commitRuntimeStatus(() => ({
      ...INITIAL_RUNTIME_STATUS,
      sourceMode: 'demo',
      acquisitionState: 'running',
      inferenceState: 'collecting',
      collectionWindowsTarget: collectionTarget,
      windowsTarget: inferenceTarget,
      streamState: 'streaming',
      progress: 0,
    }))
    setCommandMessage('Browser-generated EEG stream is running.')

    const finish = () => {
      if (demoRunIdRef.current !== runId) {
        return
      }

      const presets = [
        { label: 'left', confidence: 0.78, values: [78, 14, 8] },
        { label: 'right', confidence: 0.74, values: [17, 74, 9] },
        { label: 'feet', confidence: 0.81, values: [11, 8, 81] },
      ] as const
      const result = presets[(runId - 1) % presets.length]
      const lockedProbabilities = {
        mode1: result.values[0],
        mode2: result.values[1],
        mode3: result.values[2],
      }

      demoLockedProbabilitiesRef.current = lockedProbabilities
      setFrame((current) => ({
        ...current,
        timestamp: Date.now(),
        source: 'demo',
        activity: result.confidence,
        probabilities: lockedProbabilities,
      }))
      commitRuntimeStatus((current) => ({
        ...current,
        acquisitionState: 'stopped',
        inferenceState: 'complete',
        windowsCollected: inferenceTarget,
        progress: 1,
        streamState: 'idle',
        finalResult: {
          label: result.label,
          confidence: result.confidence,
          probabilities: {
            left: result.values[0] / 100,
            right: result.values[1] / 100,
            feet: result.values[2] / 100,
          },
          windowCount: inferenceTarget,
          completedAt: Date.now(),
        },
      }))
      setCommandMessage('Live demo inference completed in this browser.')
    }

    const infer = () => {
      if (demoRunIdRef.current !== runId) {
        return
      }

      inferred += 1
      commitRuntimeStatus((current) => ({
        ...current,
        inferenceState: 'inferring',
        windowsCollected: inferred,
        progress: inferred / inferenceTarget,
      }))

      if (inferred < inferenceTarget) {
        queue(infer, 560)
      } else {
        queue(finish, 420)
      }
    }

    const collect = () => {
      if (demoRunIdRef.current !== runId) {
        return
      }

      collected += 1
      commitRuntimeStatus((current) => ({
        ...current,
        collectionWindowsCollected: collected,
        progress: (collected / collectionTarget) * 0.45,
      }))

      if (collected < collectionTarget) {
        queue(collect, 520)
      } else {
        commitRuntimeStatus((current) => ({
          ...current,
          inferenceState: 'inferring',
          windowsCollected: 0,
          progress: 0,
        }))
        queue(infer, 560)
      }
    }

    queue(collect, 420)
  }, [clearDemoJob, commitRuntimeStatus])

  const stopDemoRun = useCallback(() => {
    clearDemoJob()
    demoLockedProbabilitiesRef.current = null
    commitRuntimeStatus((current) => ({
      ...current,
      acquisitionState: 'stopped',
      inferenceState: ['collecting', 'inferring'].includes(current.inferenceState)
        ? 'cancelled'
        : current.inferenceState,
      streamState: 'idle',
    }))
    setCommandMessage('Live demo acquisition stopped.')
  }, [clearDemoJob, commitRuntimeStatus])

  const sendCommand = useCallback((command: string, payload: Record<string, unknown> = {}) => {
    const socket = socketRef.current
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ command, ...payload }))
      return true
    }

    if (command === 'start_acquisition') {
      startDemoRun(payload)
      return true
    }
    if (command === 'stop_acquisition') {
      stopDemoRun()
      return true
    }

    setCommandMessage('This command needs the optional realtime backend.')
    return false
  }, [startDemoRun, stopDemoRun])

  useEffect(() => {
    const appMode = String(import.meta.env.VITE_APP_MODE ?? 'demo').trim().toLowerCase()
    const websocketUrl =
      appMode === 'realtime'
        ? (
            import.meta.env.VITE_REALTIME_WS_URL ??
            import.meta.env.VITE_BRAIN_SIGNAL_WS_URL
          )?.trim()
        : undefined
    let demoTimer: number | undefined
    let reconnectTimer: number | undefined
    let socket: WebSocket | undefined
    let cancelled = false
    let lastEegVisualUpdate = 0
    const demoStartedAt = performance.now()

    const startDemo = () => {
      if (demoTimer !== undefined || cancelled) {
        return
      }

      setConnectionState('demo')
      demoTimer = window.setInterval(() => {
        const nextFrame = createDemoFrame((performance.now() - demoStartedAt) / 1000)
        if (demoLockedProbabilitiesRef.current) {
          nextFrame.probabilities = demoLockedProbabilitiesRef.current
        }
        setFrame(nextFrame)
      }, 120)
    }

    const stopDemo = () => {
      if (demoTimer !== undefined) {
        window.clearInterval(demoTimer)
        demoTimer = undefined
      }
    }

    const connect = () => {
      if (!websocketUrl || cancelled) {
        startDemo()
        return
      }

      setConnectionState('connecting')
      socket = new WebSocket(websocketUrl)
      socketRef.current = socket
      socket.addEventListener('open', () => {
        clearDemoJob()
        demoLockedProbabilitiesRef.current = null
        stopDemo()
        setConnectionState('live')
        socket?.send(JSON.stringify({ command: 'get_status' }))
      })
      socket.addEventListener('message', (event) => {
        try {
          const data = JSON.parse(String(event.data))
          if (data?.type === 'runtime_state') {
            const previousInferenceState = runtimeStatusRef.current.inferenceState
            const nextRuntimeStatus = normalizeRuntimeStatus(data.payload)
            if (nextRuntimeStatus) {
              runtimeStatusRef.current = nextRuntimeStatus
              setRuntimeStatus(nextRuntimeStatus)
              if (
                nextRuntimeStatus.inferenceState === 'collecting' &&
                previousInferenceState !== 'collecting'
              ) {
                setFrame((current) => ({
                  ...current,
                  probabilities: { mode1: 0, mode2: 0, mode3: 0 },
                }))
              } else if (
                nextRuntimeStatus.inferenceState === 'complete' &&
                nextRuntimeStatus.finalResult
              ) {
                const probabilities = nextRuntimeStatus.finalResult.probabilities
                const mode1 = normalizeProbability(probabilities.left)
                const mode2 = normalizeProbability(probabilities.right)
                const mode3 = normalizeProbability(probabilities.feet)
                const total = mode1 + mode2 + mode3
                if (total > 0) {
                  setFrame((current) => ({
                    ...current,
                    probabilities: {
                      mode1: (mode1 / total) * 100,
                      mode2: (mode2 / total) * 100,
                      mode3: (mode3 / total) * 100,
                    },
                  }))
                }
              }
            }
            return
          }
          if (data?.type === 'command_ack') {
            setCommandMessage(String(data.payload?.message ?? ''))
            return
          }
          if (data?.type === 'eeg_frame') {
            const now = performance.now()
            if (now - lastEegVisualUpdate < 90) {
              return
            }
            lastEegVisualUpdate = now
          }
          if (
            data?.type === 'mi_probs' &&
            !['collecting', 'inferring'].includes(runtimeStatusRef.current.inferenceState)
          ) {
            return
          }

          const nextFrame = normalizeDeviceFrame(data)
          if (nextFrame) {
            setFrame(nextFrame)
            return
          }

          setFrame((current) => reduceRealtimeEnvelope(current, data as RealtimeEnvelope) ?? current)
        } catch {
          // Keep the last valid frame when a device packet is malformed.
        }
      })
      socket.addEventListener('close', () => {
        if (socketRef.current === socket) {
          socketRef.current = null
        }
        if (cancelled) {
          return
        }
        clearDemoJob()
        demoLockedProbabilitiesRef.current = null
        commitRuntimeStatus(() => INITIAL_RUNTIME_STATUS)
        startDemo()
        reconnectTimer = window.setTimeout(connect, 2000)
      })
      socket.addEventListener('error', () => socket?.close())
    }

    connect()

    return () => {
      cancelled = true
      clearDemoJob()
      stopDemo()
      socket?.close()
      if (socketRef.current === socket) {
        socketRef.current = null
      }
      if (reconnectTimer !== undefined) {
        window.clearTimeout(reconnectTimer)
      }
    }
  }, [clearDemoJob, commitRuntimeStatus])

  return { frame, connectionState, runtimeStatus, commandMessage, sendCommand }
}
