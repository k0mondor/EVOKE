import { Suspense, useEffect, useMemo, useRef } from 'react'
import { Html, OrbitControls, useGLTF } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

import type { BrainSignalFrame } from '@/brainSignal'
import {
  colorChannelsForValue,
  resolveTopographySensors,
  type SensorPosition,
} from '@/brainTopography'

const MODEL_URL = '/models/fsaverage-pial.glb'

interface BrainModelProps {
  frame: BrainSignalFrame
  sensorPositions: SensorPosition[]
}

interface ColorizedSurface {
  geometry: THREE.BufferGeometry
  normalizedPositions: Float32Array
  colors: THREE.BufferAttribute
}

const BASE_SURFACE_COLOR = [0.075, 0.105, 0.13] as const

const buildCorticalAnchors = (sensorPositions: SensorPosition[]) =>
  sensorPositions.map(([x, y]) => ({
    x: x * 0.88,
    y: -0.08 + y * 0.52,
    z: 0.78 - Math.abs(x) * 0.34,
  }))

function FsaverageBrain({ frame, sensorPositions }: BrainModelProps) {
  const { scene } = useGLTF(MODEL_URL)
  const model = useMemo(() => scene.clone(true), [scene])
  const surfacesRef = useRef<ColorizedSurface[]>([])
  const material = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#ffffff',
        vertexColors: true,
        emissive: '#03090d',
        emissiveIntensity: 0.24,
        metalness: 0,
        roughness: 0.72,
      }),
    [],
  )
  const sensors = resolveTopographySensors(frame, sensorPositions)
  const meanStrength =
    sensors.reduce((sum, sensor) => sum + Math.abs(sensor.value), 0) / Math.max(1, sensors.length)

  useEffect(() => {
    const meshes: THREE.Mesh[] = []
    const modelBounds = new THREE.Box3().setFromObject(model)
    const modelSize = modelBounds.getSize(new THREE.Vector3())
    const modelCenter = modelBounds.getCenter(new THREE.Vector3())
    const inverseRoot = new THREE.Matrix4().copy(model.matrixWorld).invert()

    model.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) {
        return
      }

      object.geometry = object.geometry.clone()
      object.geometry.computeVertexNormals()
      object.material = material
      meshes.push(object)
    })
    model.updateMatrixWorld(true)

    surfacesRef.current = meshes.map((mesh) => {
      const position = mesh.geometry.getAttribute('position')
      const normalizedPositions = new Float32Array(position.count * 3)
      const point = new THREE.Vector3()
      const meshToRoot = new THREE.Matrix4().multiplyMatrices(inverseRoot, mesh.matrixWorld)
      for (let index = 0; index < position.count; index += 1) {
        point.fromBufferAttribute(position, index).applyMatrix4(meshToRoot)
        normalizedPositions[index * 3] = (point.x - modelCenter.x) / Math.max(modelSize.x * 0.5, 1e-6)
        normalizedPositions[index * 3 + 1] =
          (point.y - modelCenter.y) / Math.max(modelSize.y * 0.5, 1e-6)
        normalizedPositions[index * 3 + 2] =
          (point.z - modelCenter.z) / Math.max(modelSize.z * 0.5, 1e-6)
      }
      const colors = new THREE.BufferAttribute(new Float32Array(position.count * 3), 3)
      mesh.geometry.setAttribute('color', colors)
      return { geometry: mesh.geometry, normalizedPositions, colors }
    })

    return () => {
      surfacesRef.current.forEach(({ geometry }) => geometry.dispose())
      surfacesRef.current = []
      material.dispose()
    }
  }, [material, model])

  useEffect(() => {
    const anchors = buildCorticalAnchors(sensorPositions)
    for (const surface of surfacesRef.current) {
      const target = surface.colors.array as Float32Array
      for (let index = 0; index < surface.colors.count; index += 1) {
        const x = surface.normalizedPositions[index * 3]
        const y = surface.normalizedPositions[index * 3 + 1]
        const z = surface.normalizedPositions[index * 3 + 2]
        let weightedValue = 0
        let weightTotal = 0
        let nearestDistanceSquared = Number.POSITIVE_INFINITY

        anchors.forEach((anchor, sensorIndex) => {
          const distanceSquared =
            (x - anchor.x) ** 2 + (y - anchor.y) ** 2 + (z - anchor.z) ** 2
          const weight = Math.exp(-distanceSquared / 0.3)
          weightedValue += weight * (sensors[sensorIndex]?.value ?? 0)
          weightTotal += weight
          nearestDistanceSquared = Math.min(nearestDistanceSquared, distanceSquared)
        })

        const value = weightTotal > 1e-8 ? weightedValue / weightTotal : 0
        const influence = Math.min(1, Math.exp(-nearestDistanceSquared / 0.4) * 1.42)
        const [red, green, blue] = colorChannelsForValue(value).map((channel) => channel / 255)
        target[index * 3] = BASE_SURFACE_COLOR[0] + (red - BASE_SURFACE_COLOR[0]) * influence
        target[index * 3 + 1] = BASE_SURFACE_COLOR[1] + (green - BASE_SURFACE_COLOR[1]) * influence
        target[index * 3 + 2] = BASE_SURFACE_COLOR[2] + (blue - BASE_SURFACE_COLOR[2]) * influence
      }
      surface.colors.needsUpdate = true
    }
  }, [sensorPositions, sensors])

  useFrame(({ clock }) => {
    material.emissiveIntensity =
      0.16 + meanStrength * 0.22 + Math.sin(clock.elapsedTime * 2.2) * 0.018
  })

  return (
    <group rotation={[-0.04, -0.35, 0.02]}>
      <primitive object={model} />
    </group>
  )
}

function LoadingModel() {
  return (
    <Html center>
      <span className="brain-model-loading">Loading cortex</span>
    </Html>
  )
}

export default function BrainModel({ frame, sensorPositions }: BrainModelProps) {
  return (
    <div className="brain-model" aria-label="Interactive fsaverage cortical surface model">
      <Canvas
        dpr={[1, 1.65]}
        camera={{ position: [0, 0.12, 3.8], fov: 34 }}
        gl={{ alpha: true, antialias: true, powerPreference: 'high-performance' }}
      >
        <ambientLight intensity={0.28} />
        <hemisphereLight args={['#b9eaff', '#100b17', 0.72]} />
        <directionalLight color="#fff7f0" position={[3, 4, 4]} intensity={1.2} />
        <directionalLight color="#846bff" position={[-4, 0, -2]} intensity={0.55} />

        <Suspense fallback={<LoadingModel />}>
          <FsaverageBrain frame={frame} sensorPositions={sensorPositions} />
        </Suspense>

        <OrbitControls
          enableDamping
          dampingFactor={0.08}
          enablePan={false}
          minDistance={3.1}
          maxDistance={5.4}
          rotateSpeed={0.55}
          zoomSpeed={0.6}
        />
      </Canvas>
      <div className="brain-model__hint">SURFACE FIELD · DRAG TO ROTATE · SCROLL TO ZOOM</div>
    </div>
  )
}

useGLTF.preload(MODEL_URL)
