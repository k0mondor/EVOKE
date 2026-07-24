import { useFrame } from '@react-three/fiber'
import { Canvas } from '@react-three/fiber'
import { useMemo, useRef } from 'react'
import * as THREE from 'three'

import { usePageMotionStore } from '@/stores/pageMotionStore'

const vertexShader = `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = vec4(position, 1.0);
}
`

const fragmentShader = `
precision highp float;

varying vec2 vUv;

uniform vec2 u_resolution;
uniform float u_time;
uniform float u_scroll;

// Background palette
const vec3 C_DARK = vec3(0.03, 0.03, 0.03);
const vec3 C_LIGHT = vec3(0.85, 0.86, 0.88);

// Contour tuning
const float DENSITY = 5.2;
const vec3 LINE_DARK_COLOR = vec3(0.88, 0.88, 0.88);
const vec3 LINE_LIGHT_COLOR = vec3(0.06, 0.06, 0.06);

vec3 mod289(vec3 x) {
  return x - floor(x * (1.0 / 289.0)) * 289.0;
}

vec4 mod289(vec4 x) {
  return x - floor(x * (1.0 / 289.0)) * 289.0;
}

vec4 permute(vec4 x) {
  return mod289(((x * 34.0) + 1.0) * x);
}

vec4 taylorInvSqrt(vec4 r) {
  return 1.79284291400159 - 0.85373472095314 * r;
}

float simplex3d(vec3 v) {
  const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

  vec3 i = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);

  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);

  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;

  i = mod289(i);
  vec4 p = permute(permute(permute(
      i.z + vec4(0.0, i1.z, i2.z, 1.0))
    + i.y + vec4(0.0, i1.y, i2.y, 1.0))
    + i.x + vec4(0.0, i1.x, i2.x, 1.0));

  float n_ = 1.0 / 7.0;
  vec3 ns = n_ * D.wyz - D.xzx;

  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);

  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);

  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);

  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));

  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;

  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);

  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x;
  p1 *= norm.y;
  p2 *= norm.z;
  p3 *= norm.w;

  vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}

float ditherNoise(vec2 uv) {
  return fract(sin(dot(uv, vec2(12.9898, 78.233))) * 43758.5453123) - 0.5;
}

void main() {
  vec2 uv = vUv;
  vec2 fieldUv = uv;
  fieldUv.x *= u_resolution.x / u_resolution.y;
  float viewportY = 1.0 - uv.y;

  // Layer 1: one-way tone expansion from bottom to top, avoiding a symmetric bell-shaped light field
  float progress = smoothstep(0.0, 1.0, u_scroll);
  float liftBoundary = mix(1.12, -0.08, progress);
  float boundarySoftness = mix(0.28, 0.62, progress);
  float upwardLift = smoothstep(liftBoundary - boundarySoftness, liftBoundary + boundarySoftness, viewportY);
  float globalLift = progress * 0.16;
  float finalLight = clamp(max(upwardLift, globalLift), 0.0, 1.0);
  vec3 bgGradient = mix(C_DARK, C_LIGHT, finalLight);

  // Layer 2: independent contour overlay
  float Z = simplex3d(vec3(fieldUv * 2.1, u_time * 0.026 + u_scroll * 0.06));
  float Z_line = Z * 0.5 + 0.5;
  float linePattern = abs(sin(Z_line * DENSITY * 3.14159));
  float line = smoothstep(0.03, 0.0, linePattern);
  vec3 currentLineColor = mix(LINE_DARK_COLOR, LINE_LIGHT_COLOR, finalLight);
  float lineAlphaMax = mix(0.16, 0.12, finalLight);
  float lineAlpha = line * lineAlphaMax;

  vec3 finalColor = mix(bgGradient, currentLineColor, lineAlpha);
  finalColor += ditherNoise(uv + fract(u_time)) * 0.008;
  finalColor = clamp(finalColor, 0.0, 1.0);

  gl_FragColor = vec4(finalColor, 1.0);
}
`

const FluidPlane = () => {
  const materialRef = useRef<THREE.ShaderMaterial>(null)
  const scrollProgress = usePageMotionStore((state) => state.scrollProgress)
  const applicationProgress = usePageMotionStore((state) => state.applicationProgress)

  const uniforms = useMemo(
    () => ({
      u_time: { value: 0 },
      u_resolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
      u_scroll: { value: 0 },
    }),
    [],
  )

  useFrame(() => {
    if (!materialRef.current) {
      return
    }

    uniforms.u_time.value = performance.now() * 0.001
    uniforms.u_scroll.value = Math.max(scrollProgress * 0.16, applicationProgress)
    uniforms.u_resolution.value.set(window.innerWidth, window.innerHeight)
  })

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial ref={materialRef} uniforms={uniforms} vertexShader={vertexShader} fragmentShader={fragmentShader} />
    </mesh>
  )
}

export const GlobalBackground = () => {
  return (
    <div className="pointer-events-none fixed inset-0 z-0">
      <Canvas orthographic camera={{ position: [0, 0, 1], zoom: 1 }} gl={{ alpha: false, antialias: true }}>
        <FluidPlane />
      </Canvas>
    </div>
  )
}
