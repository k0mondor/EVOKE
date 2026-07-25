import { lazy, Suspense, useEffect, useState } from 'react'

import { useBrainSignal } from '@/brainSignal'
import { FRONTAL_8_CHANNEL_POSITIONS, type SensorPosition } from '@/brainTopography'

const ScalpTopomap = lazy(() => import('@/components/ScalpTopomap'))
const BrainModel = lazy(() => import('@/components/BrainModel'))
const SENSOR_LAYOUT_STORAGE_KEY = 'evoke-frontal-sensor-layout-v1'

const createDefaultSensorPositions = (): SensorPosition[] =>
  FRONTAL_8_CHANNEL_POSITIONS.map(([x, y]) => [x, y])

const loadSensorPositions = (): SensorPosition[] => {
  try {
    const value = JSON.parse(window.localStorage.getItem(SENSOR_LAYOUT_STORAGE_KEY) ?? 'null')
    if (
      Array.isArray(value) &&
      value.length === 8 &&
      value.every(
        (position) =>
          Array.isArray(position) &&
          position.length === 2 &&
          position.every((coordinate) => Number.isFinite(Number(coordinate))),
      )
    ) {
      return value.map(([x, y]) => [Number(x), Number(y)] as SensorPosition)
    }
  } catch {
    // Fall back to the calibrated headband arc when storage is unavailable.
  }
  return createDefaultSensorPositions()
}

export const FinalBenefitsSection = () => {
  const { frame, connectionState, runtimeStatus, commandMessage, sendCommand } = useBrainSignal()
  const [sensorPositions, setSensorPositions] = useState<SensorPosition[]>(loadSensorPositions)
  const [collectionWindowCount, setCollectionWindowCount] = useState(3)
  const [inferenceWindowCount, setInferenceWindowCount] = useState(1)
  const confidenceScores = [
    { label: 'Mode 1', value: frame.probabilities.mode1, tone: 'confidence-bar__fill--orange' },
    { label: 'Mode 2', value: frame.probabilities.mode2, tone: 'confidence-bar__fill--blue' },
    { label: 'Mode 3', value: frame.probabilities.mode3, tone: 'confidence-bar__fill--purple' },
  ]
  const highestMode = confidenceScores.reduce((highest, score) => (score.value > highest.value ? score : highest))
  const isAcquiring = ['connecting', 'running'].includes(runtimeStatus.acquisitionState)
  const backendReady = connectionState === 'live'
  const connectionLabel =
    connectionState !== 'live'
      ? connectionState === 'connecting'
        ? 'Connecting'
        : 'Live demo'
      : runtimeStatus.acquisitionState === 'running'
        ? runtimeStatus.streamState === 'waiting_for_bytes'
          ? 'Waiting for data'
          : runtimeStatus.streamState === 'partial_frame'
            ? 'Partial frame'
            : runtimeStatus.streamState === 'streaming'
              ? 'Acquiring'
              : 'Source connected'
        : runtimeStatus.acquisitionState === 'connecting'
          ? 'Source link'
          : 'Backend ready'
  const streamDetail =
    runtimeStatus.streamState === 'partial_frame'
      ? `${runtimeStatus.tcpPendingFrameBytes} / ${runtimeStatus.tcpExpectedFrameBytes} B`
      : runtimeStatus.streamState === 'streaming'
        ? `${runtimeStatus.tcpFramesReceived} frames · ${runtimeStatus.tcpBytesReceived} B`
        : runtimeStatus.streamState === 'waiting_for_bytes'
          ? `${runtimeStatus.tcpBytesReceived} B received`
          : commandMessage
  const finalModeLabels: Record<string, string> = {
    left: 'Mode 1',
    right: 'Mode 2',
    feet: 'Mode 3',
  }
  const inferenceStatusLabel =
    runtimeStatus.inferenceState === 'collecting'
      ? `Collecting ${runtimeStatus.collectionWindowsCollected} / ${runtimeStatus.collectionWindowsTarget}`
      : runtimeStatus.inferenceState === 'inferring'
        ? `Inferring ${runtimeStatus.windowsCollected} / ${runtimeStatus.windowsTarget}`
        : runtimeStatus.inferenceState === 'complete' && runtimeStatus.finalResult
          ? `${finalModeLabels[runtimeStatus.finalResult.label] ?? runtimeStatus.finalResult.label} · ${Math.round(runtimeStatus.finalResult.confidence * 100)}%`
          : runtimeStatus.inferenceState === 'cancelled'
            ? 'Inference cancelled'
            : 'Awaiting inference run'

  useEffect(() => {
    try {
      window.localStorage.setItem(SENSOR_LAYOUT_STORAGE_KEY, JSON.stringify(sensorPositions))
    } catch {
      // The live view remains usable when browser storage is unavailable.
    }
  }, [sensorPositions])

  return (
    <section
      id="mission"
      data-scroll-section
      className="benefits-section relative flex h-[100svh] min-h-[720px] overflow-hidden bg-black px-4 py-8 text-white sm:px-6 md:px-10"
    >
      <div className="mx-auto flex h-full w-full max-w-[1400px] flex-col">
        <header className="benefits-header">
          <p className="benefits-header__eyebrow">brain signal interface</p>
          <h2 className="benefits-header__title">Live Neural Classification</h2>
        </header>

        <div className="benefits-dashboard">
          <div className="benefits-model-grid">
            <article className="benefit-card brain-card brain-card--topomap">
              <div className="brain-card__viewport">
                <div className="brain-card__glow" aria-hidden="true" />
                <Suspense fallback={<div className="brain-model-fallback">Loading topography</div>}>
                  <ScalpTopomap
                    frame={frame}
                    sensorPositions={sensorPositions}
                    onSensorPositionsChange={setSensorPositions}
                    onResetSensorPositions={() => setSensorPositions(createDefaultSensorPositions())}
                  />
                </Suspense>
              </div>
              <div className="brain-card__caption">
                <div>
                  <p className="benefit-card__eyebrow">MNE-style 2D projection</p>
                  <h3 className="benefit-card__heading">Frontal scalp topography</h3>
                </div>
                <span className="brain-card__activity">{Math.round(frame.activity * 100)}</span>
              </div>
            </article>

            <article className="benefit-card brain-card brain-card--cortex">
              <div className="brain-card__viewport">
                <div className="brain-card__glow" aria-hidden="true" />
                <Suspense fallback={<div className="brain-model-fallback">Loading cortex</div>}>
                  <BrainModel frame={frame} sensorPositions={sensorPositions} />
                </Suspense>
              </div>
              <div className="brain-card__caption">
                <div>
                  <p className="benefit-card__eyebrow">Realtime 3D field</p>
                  <h3 className="benefit-card__heading">Frontal cortical activity</h3>
                </div>
                <span className="brain-card__activity">{frame.topomap.values.length}CH</span>
              </div>
            </article>
          </div>

          <div className="benefits-data-rail">
            <article className="benefit-card classification-card">
              <div className="benefit-card__inner benefit-card__inner--rail">
                <div className="rail-heading">
                  <p className="benefit-card__eyebrow">Live inference</p>
                  <h3 className="benefit-card__heading">Three-class confidence</h3>
                </div>

                <div className="classification-live">
                  <div className="confidence-bars">
                    {confidenceScores.map((score) => (
                      <div key={score.label}>
                        <div className="confidence-bar__label">
                          <span>{score.label}</span>
                          <span className={score.label === highestMode.label ? 'is-highest' : ''}>
                            {Math.round(score.value)}%
                          </span>
                        </div>
                        <div className="confidence-bar__track">
                          <div
                            className={`confidence-bar__fill ${score.tone}`}
                            style={{ width: `${score.value}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className={`inference-job inference-job--${runtimeStatus.inferenceState}`}>
                    <div className="inference-job__label">
                      <span>Formal inference</span>
                      <strong>{inferenceStatusLabel}</strong>
                    </div>
                    <div className="inference-job__state" aria-live="polite">
                      <span />
                      {runtimeStatus.inferenceState === 'collecting'
                        ? 'Preparing'
                        : runtimeStatus.inferenceState === 'inferring'
                          ? 'Live probabilities'
                          : runtimeStatus.inferenceState === 'complete'
                            ? 'Result locked'
                            : 'Starts with acquisition'}
                    </div>
                  </div>
                </div>
              </div>
            </article>

            <article className="benefit-card telemetry-card">
              <div className="benefit-card__inner benefit-card__inner--rail">
                <div className="rail-heading">
                  <p className="benefit-card__eyebrow">Realtime link</p>
                  <h3 className="benefit-card__heading">Acquisition</h3>
                </div>

                <div className="runtime-control-panel">
                  <div className="runtime-control-panel__top">
                    <div className="runtime-control-fields">
                      <label>
                        <span>Collect windows</span>
                        <input
                          type="number"
                          min="3"
                          max="50"
                          step="1"
                          disabled={isAcquiring}
                          value={collectionWindowCount}
                          onChange={(event) =>
                            setCollectionWindowCount(Math.max(3, Math.min(50, Number(event.target.value) || 3)))
                          }
                        />
                      </label>
                      <label>
                        <span>Infer windows</span>
                        <input
                          type="number"
                          min="1"
                          max="50"
                          step="1"
                          disabled={isAcquiring}
                          value={inferenceWindowCount}
                          onChange={(event) =>
                            setInferenceWindowCount(Math.max(1, Math.min(50, Number(event.target.value) || 1)))
                          }
                        />
                      </label>
                    </div>

                    <div className="runtime-control-actions">
                      <button
                        type="button"
                        className="runtime-control-button runtime-control-button--start"
                        disabled={!backendReady || isAcquiring}
                        onClick={() =>
                          sendCommand('start_acquisition', {
                            collection_window_count: collectionWindowCount,
                            inference_window_count: inferenceWindowCount,
                          })
                        }
                      >
                        Start acquisition
                      </button>
                      <button
                        type="button"
                        className="runtime-control-button runtime-control-button--stop"
                        disabled={!backendReady || !isAcquiring}
                        onClick={() => sendCommand('stop_acquisition')}
                      >
                        Stop
                      </button>
                    </div>
                  </div>

                  <div className="runtime-control-status">
                    <span className={`telemetry-status telemetry-status--${connectionState}`}>
                      <span aria-hidden="true" />
                      {connectionLabel}
                    </span>
                    <span>Signal {Math.round(frame.signalQuality)}%</span>
                    <span>Active {highestMode.label}</span>
                    <span className={runtimeStatus.error ? 'has-error' : ''}>
                      {runtimeStatus.error ?? streamDetail}
                    </span>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>
  )
}
