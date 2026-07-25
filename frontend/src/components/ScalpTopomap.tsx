import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'

import type { BrainSignalFrame } from '@/brainSignal'
import {
  colorChannelsForValue,
  resolveTopographySensors,
  type SensorPosition,
  TOPOGRAPHY_COLORS,
} from '@/brainTopography'

interface ScalpTopomapProps {
  frame: BrainSignalFrame
  sensorPositions: SensorPosition[]
  onSensorPositionsChange: (positions: SensorPosition[]) => void
  onResetSensorPositions: () => void
}

interface InterpolationPoint {
  x: number
  y: number
  value: number
}

const getTopomapGeometry = (width: number, height: number) => {
  const radius = Math.min(width * 0.4, height * 0.36)
  return {
    radius,
    centerX: width / 2,
    centerY: Math.min(height * 0.43, radius * 1.22),
  }
}

const interpolateSmooth = (x: number, y: number, points: InterpolationPoint[]) => {
  let value = 0

  // Overlapping Gaussian radial fields form rounded activity regions without
  // exposing the straight edges of an underlying triangle mesh.
  for (const point of points) {
    const distanceSquared = (x - point.x) ** 2 + (y - point.y) ** 2
    value += point.value * Math.exp(-distanceSquared / 0.16)
  }

  return value
}

const drawTopomap = (
  canvas: HTMLCanvasElement,
  frame: BrainSignalFrame,
  sensorPositions: SensorPosition[],
) => {
  const bounds = canvas.getBoundingClientRect()
  if (bounds.width <= 0 || bounds.height <= 0) {
    return
  }

  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
  const width = bounds.width
  const height = bounds.height
  const targetWidth = Math.round(width * pixelRatio)
  const targetHeight = Math.round(height * pixelRatio)
  if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
    canvas.width = targetWidth
    canvas.height = targetHeight
  }

  const context = canvas.getContext('2d')
  if (!context) {
    return
  }

  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
  context.clearRect(0, 0, width, height)

  const sensors = resolveTopographySensors(frame, sensorPositions)
  const { radius, centerX, centerY } = getTopomapGeometry(width, height)
  const resolution = 112
  const field = new Float32Array(resolution * resolution)
  const interpolationInput: InterpolationPoint[] = [
    ...sensors,
    ...Array.from({ length: 16 }, (_, index) => {
      const angle = (index / 16) * Math.PI * 2
      return {
        x: Math.cos(angle) * 1.04,
        y: Math.sin(angle) * 1.04,
        value: 0,
      }
    }),
  ]
  const offscreen = document.createElement('canvas')
  offscreen.width = resolution
  offscreen.height = resolution
  const offscreenContext = offscreen.getContext('2d')
  if (!offscreenContext) {
    return
  }

  const image = offscreenContext.createImageData(resolution, resolution)
  for (let yIndex = 0; yIndex < resolution; yIndex += 1) {
    for (let xIndex = 0; xIndex < resolution; xIndex += 1) {
      const x = (xIndex / (resolution - 1)) * 2 - 1
      const y = 1 - (yIndex / (resolution - 1)) * 2
      const index = yIndex * resolution + xIndex

      if (x * x + y * y > 1) {
        image.data[index * 4 + 3] = 0
        continue
      }

      const value = interpolateSmooth(x, y, interpolationInput)
      field[index] = value
    }
  }

  const fieldScale = Math.max(1e-6, ...field.map((value) => Math.abs(value)))
  for (let yIndex = 0; yIndex < resolution; yIndex += 1) {
    for (let xIndex = 0; xIndex < resolution; xIndex += 1) {
      const x = (xIndex / (resolution - 1)) * 2 - 1
      const y = 1 - (yIndex / (resolution - 1)) * 2
      const index = yIndex * resolution + xIndex
      if (x * x + y * y > 1) {
        continue
      }

      field[index] /= fieldScale
      const [red, green, blue] = colorChannelsForValue(field[index])
      image.data[index * 4] = red
      image.data[index * 4 + 1] = green
      image.data[index * 4 + 2] = blue
      image.data[index * 4 + 3] = 242
    }
  }

  offscreenContext.putImageData(image, 0, 0)

  context.save()
  context.beginPath()
  context.arc(centerX, centerY, radius, 0, Math.PI * 2)
  context.clip()
  context.imageSmoothingEnabled = true
  context.drawImage(offscreen, centerX - radius, centerY - radius, radius * 2, radius * 2)
  drawContours(context, field, resolution, centerX, centerY, radius)
  context.restore()

  context.strokeStyle = 'rgba(255,255,255,0.86)'
  context.lineWidth = 1.6
  context.beginPath()
  context.arc(centerX, centerY, radius, 0, Math.PI * 2)
  context.stroke()

  context.beginPath()
  context.moveTo(centerX - radius * 0.12, centerY - radius * 0.985)
  context.lineTo(centerX, centerY - radius * 1.12)
  context.lineTo(centerX + radius * 0.12, centerY - radius * 0.985)
  context.stroke()

  context.beginPath()
  context.arc(centerX - radius * 1.02, centerY, radius * 0.12, Math.PI * 0.52, Math.PI * 1.48)
  context.stroke()
  context.beginPath()
  context.arc(centerX + radius * 1.02, centerY, radius * 0.12, -Math.PI * 0.48, Math.PI * 0.48)
  context.stroke()

  context.font = "600 9px 'Elms Sans', sans-serif"
  context.textAlign = 'center'
  context.textBaseline = 'top'
  for (const sensor of sensors) {
    const x = centerX + sensor.x * radius
    const y = centerY - sensor.y * radius
    context.fillStyle = '#050608'
    context.beginPath()
    context.arc(x, y, 4.4, 0, Math.PI * 2)
    context.fill()
    context.strokeStyle = '#fff'
    context.lineWidth = 1.3
    context.stroke()
    context.fillStyle = '#fff'
    context.fillText(sensor.channel, x, y + 7)
  }
}

const drawContours = (
  context: CanvasRenderingContext2D,
  field: Float32Array,
  resolution: number,
  centerX: number,
  centerY: number,
  radius: number,
) => {
  const thresholds = [-0.66, -0.33, 0.33, 0.66]
  context.strokeStyle = 'rgba(255,255,255,0.24)'
  context.lineWidth = 0.75
  context.lineCap = 'round'
  context.lineJoin = 'round'

  const project = (x: number, y: number) => ({
    x: centerX - radius + (x / (resolution - 1)) * radius * 2,
    y: centerY - radius + (y / (resolution - 1)) * radius * 2,
  })

  for (const threshold of thresholds) {
    context.beginPath()
    for (let y = 0; y < resolution - 1; y += 1) {
      for (let x = 0; x < resolution - 1; x += 1) {
        const topLeft = field[y * resolution + x]
        const topRight = field[y * resolution + x + 1]
        const bottomRight = field[(y + 1) * resolution + x + 1]
        const bottomLeft = field[(y + 1) * resolution + x]
        const crossings: Array<{ x: number; y: number }> = []

        const addCrossing = (
          first: number,
          second: number,
          firstPoint: [number, number],
          secondPoint: [number, number],
        ) => {
          if ((first < threshold) === (second < threshold)) {
            return
          }
          const amount = (threshold - first) / (second - first)
          crossings.push({
            x: firstPoint[0] + (secondPoint[0] - firstPoint[0]) * amount,
            y: firstPoint[1] + (secondPoint[1] - firstPoint[1]) * amount,
          })
        }

        addCrossing(topLeft, topRight, [x, y], [x + 1, y])
        addCrossing(topRight, bottomRight, [x + 1, y], [x + 1, y + 1])
        addCrossing(bottomRight, bottomLeft, [x + 1, y + 1], [x, y + 1])
        addCrossing(bottomLeft, topLeft, [x, y + 1], [x, y])

        if (crossings.length === 2) {
          const start = project(crossings[0].x, crossings[0].y)
          const end = project(crossings[1].x, crossings[1].y)
          context.moveTo(start.x, start.y)
          context.lineTo(end.x, end.y)
        } else if (crossings.length === 4) {
          const first = project(crossings[0].x, crossings[0].y)
          const second = project(crossings[1].x, crossings[1].y)
          const third = project(crossings[2].x, crossings[2].y)
          const fourth = project(crossings[3].x, crossings[3].y)
          context.moveTo(first.x, first.y)
          context.lineTo(second.x, second.y)
          context.moveTo(third.x, third.y)
          context.lineTo(fourth.x, fourth.y)
        }
      }
    }
    context.stroke()
  }
}

export default function ScalpTopomap({
  frame,
  sensorPositions,
  onSensorPositionsChange,
  onResetSensorPositions,
}: ScalpTopomapProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const draggingSensorRef = useRef<number | null>(null)
  const latestFrameRef = useRef(frame)
  const latestPositionsRef = useRef(sensorPositions)
  const [isDragging, setIsDragging] = useState(false)
  latestFrameRef.current = frame
  latestPositionsRef.current = sensorPositions

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) {
      return
    }

    const draw = () => drawTopomap(canvas, latestFrameRef.current, latestPositionsRef.current)
    const resizeObserver = new ResizeObserver(draw)
    resizeObserver.observe(canvas)
    draw()
    return () => resizeObserver.disconnect()
  }, [])

  useEffect(() => {
    if (canvasRef.current) {
      drawTopomap(canvasRef.current, frame, sensorPositions)
    }
  }, [frame, sensorPositions])

  const normalizedPointerPosition = (event: ReactPointerEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) {
      return null
    }
    const bounds = canvas.getBoundingClientRect()
    const { radius, centerX, centerY } = getTopomapGeometry(bounds.width, bounds.height)
    return {
      x: (event.clientX - bounds.left - centerX) / radius,
      y: -(event.clientY - bounds.top - centerY) / radius,
    }
  }

  const handlePointerDown = (event: ReactPointerEvent<HTMLCanvasElement>) => {
    const point = normalizedPointerPosition(event)
    if (!point) {
      return
    }

    const sensors = resolveTopographySensors(frame, sensorPositions)
    let closestIndex = -1
    let closestDistance = Number.POSITIVE_INFINITY
    sensors.forEach((sensor, index) => {
      const distance = Math.hypot(sensor.x - point.x, sensor.y - point.y)
      if (distance < closestDistance) {
        closestDistance = distance
        closestIndex = index
      }
    })

    if (closestIndex >= 0 && closestDistance <= 0.16) {
      draggingSensorRef.current = closestIndex
      event.currentTarget.setPointerCapture(event.pointerId)
      setIsDragging(true)
    }
  }

  const handlePointerMove = (event: ReactPointerEvent<HTMLCanvasElement>) => {
    const sensorIndex = draggingSensorRef.current
    const point = normalizedPointerPosition(event)
    if (sensorIndex === null || !point) {
      return
    }

    event.preventDefault()
    const distance = Math.hypot(point.x, point.y)
    const scale = distance > 0.94 ? 0.94 / distance : 1
    const nextPosition: SensorPosition = [point.x * scale, point.y * scale]
    onSensorPositionsChange(
      sensorPositions.map((position, index) => (index === sensorIndex ? nextPosition : position)),
    )
  }

  const stopDragging = (event: ReactPointerEvent<HTMLCanvasElement>) => {
    if (draggingSensorRef.current !== null && event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
    draggingSensorRef.current = null
    setIsDragging(false)
  }

  const usesFallbackMontage = frame.topomap.channelNames.every((name) => /^CH\d+$/i.test(name))

  return (
    <div
      className={`scalp-topomap${isDragging ? ' is-dragging' : ''}`}
      aria-label="Realtime MNE-style EEG scalp topography with draggable electrodes"
    >
      <canvas
        ref={canvasRef}
        aria-label="Drag EEG electrodes to calibrate their positions"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={stopDragging}
        onPointerCancel={stopDragging}
      />
      <div className="scalp-topomap__legend" aria-hidden="true">
        <span>−</span>
        <div
          style={{
            background: `linear-gradient(90deg, ${TOPOGRAPHY_COLORS.negative}, ${TOPOGRAPHY_COLORS.neutral}, ${TOPOGRAPHY_COLORS.positive})`,
          }}
        />
        <span>+</span>
      </div>
      <div className="scalp-topomap__meta">
        <span>{frame.topomap.kind === 'instant' ? 'instantaneous amplitude' : 'temporal spatial energy'}</span>
        <span className="scalp-topomap__layout">
          {usesFallbackMontage ? 'drag electrodes · 8ch' : 'configured montage'}
          <button type="button" onClick={onResetSensorPositions}>
            reset
          </button>
        </span>
      </div>
    </div>
  )
}
