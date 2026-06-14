import { useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sparkles, Billboard, Text } from '@react-three/drei';
import type { MotionValue } from 'motion/react';
import * as THREE from 'three';

interface SceneProps {
  progress: MotionValue<number>;
}

const N = 3200; // number of cube blocks

// ── Shape target generators (each returns a Float32Array of N*3) ──────────────

// Sample N points from the opaque pixels of a 2D drawing, preserving aspect.
function sampleCanvas(draw: (ctx: CanvasRenderingContext2D, w: number, h: number) => void, w: number, h: number, height: number, depth = 0.12): Float32Array {
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d')!;
  draw(ctx, w, h);
  const data = ctx.getImageData(0, 0, w, h).data;

  const pts: [number, number][] = [];
  for (let y = 0; y < h; y += 2) {
    for (let x = 0; x < w; x += 2) {
      if (data[(y * w + x) * 4 + 3] > 128) pts.push([x, y]);
    }
  }
  const out = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const [px, py] = pts.length ? pts[(Math.random() * pts.length) | 0] : [w / 2, h / 2];
    out[i * 3] = ((px - w / 2) / h) * height;
    out[i * 3 + 1] = (-(py - h / 2) / h) * height;
    out[i * 3 + 2] = (Math.random() - 0.5) * depth;
  }
  return out;
}

function shieldTarget(): Float32Array {
  return sampleCanvas((ctx, w, h) => {
    const pad = w * 0.16;
    const x0 = pad;
    const x1 = w - pad;
    const y0 = h * 0.1;
    const y1 = h * 0.96;
    const mid = y0 + (y1 - y0) * 0.46;
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y0);
    ctx.lineTo(x1, mid);
    ctx.quadraticCurveTo(x1, y1, (x0 + x1) / 2, y1);
    ctx.quadraticCurveTo(x0, y1, x0, mid);
    ctx.closePath();
    ctx.fill();
  }, 512, 512, 3.0, 0.35);
}

function textTarget(text: string, height: number): Float32Array {
  return sampleCanvas((ctx, w, h) => {
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 200px Inter, Arial, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, w / 2, h / 2);
  }, 1200, 300, height, 0.18);
}

function scatterTarget(): Float32Array {
  const out = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const r = 2.2 + Math.random() * 1.6;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    out[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    out[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    out[i * 3 + 2] = r * Math.cos(phi);
  }
  return out;
}

function sphereTarget(radius: number): Float32Array {
  const out = new Float32Array(N * 3);
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < N; i++) {
    const y = 1 - (i / (N - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const theta = golden * i;
    out[i * 3] = Math.cos(theta) * r * radius;
    out[i * 3 + 1] = y * radius;
    out[i * 3 + 2] = Math.sin(theta) * r * radius;
  }
  return out;
}

// ── Palette per stage ─────────────────────────────────────────────────────────
const PALETTE = ['#6366f1', '#22d3ee', '#818cf8', '#f472b6', '#a78bfa'].map((c) => new THREE.Color(c));

const smoothstep = (t: number) => t * t * (3 - 2 * t);

function Morph({ progress }: SceneProps) {
  const mesh = useRef<THREE.InstancedMesh>(null);
  const group = useRef<THREE.Group>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const tmpColor = useMemo(() => new THREE.Color(), []);

  // Ordered keyframe shapes.
  const targets = useMemo(
    () => [
      shieldTarget(),    // 0 — shield
      scatterTarget(),   // 1 — disintegrated cubes
      sphereTarget(1.45),// 2 — sphere (AI)
      scatterTarget(),   // 3 — split / explode
      textTarget('AEGIS', 1.15), // 4 — logo wordmark
    ],
    [],
  );

  // Per-cube spin offset for shimmer.
  const spins = useMemo(() => {
    const a = new Float32Array(N);
    for (let i = 0; i < N; i++) a[i] = Math.random() * Math.PI * 2;
    return a;
  }, []);

  useEffect(() => {
    if (mesh.current) mesh.current.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  }, []);

  useFrame((state) => {
    const p = THREE.MathUtils.clamp(progress.get(), 0, 1);
    const segs = targets.length - 1;
    const scaled = p * segs;
    let idx = Math.floor(scaled);
    if (idx >= segs) idx = segs - 1;
    const te = smoothstep(scaled - idx);
    const A = targets[idx];
    const B = targets[idx + 1];

    const t = state.clock.elapsedTime;
    // cubes shrink a touch while scattered (stages around p=0.25 and p=0.75)
    const scatterAmt =
      Math.max(0, 1 - Math.abs(p - 0.25) / 0.18) +
      Math.max(0, 1 - Math.abs(p - 0.75) / 0.18);
    const baseScale = 0.05 * (1 - 0.35 * Math.min(1, scatterAmt));

    if (mesh.current) {
      for (let i = 0; i < N; i++) {
        const ix = i * 3;
        dummy.position.set(
          A[ix] + (B[ix] - A[ix]) * te,
          A[ix + 1] + (B[ix + 1] - A[ix + 1]) * te,
          A[ix + 2] + (B[ix + 2] - A[ix + 2]) * te,
        );
        const rot = spins[i] + t * 0.3;
        dummy.rotation.set(rot, rot * 0.7, 0);
        dummy.scale.setScalar(baseScale);
        dummy.updateMatrix();
        mesh.current.setMatrixAt(i, dummy.matrix);
      }
      mesh.current.instanceMatrix.needsUpdate = true;

      // stage color
      const cScaled = p * (PALETTE.length - 1);
      const ci = Math.min(PALETTE.length - 2, Math.floor(cScaled));
      tmpColor.copy(PALETTE[ci]).lerp(PALETTE[ci + 1], cScaled - ci);
      (mesh.current.material as THREE.MeshStandardMaterial).color.copy(tmpColor);
      (mesh.current.material as THREE.MeshStandardMaterial).emissive.copy(tmpColor).multiplyScalar(0.25);
    }

    if (group.current) {
      group.current.rotation.y = t * 0.12 + p * Math.PI * 0.5;
      group.current.rotation.x = Math.sin(t * 0.2) * 0.08;
    }
  });

  return (
    <group ref={group}>
      <instancedMesh ref={mesh} args={[undefined as any, undefined as any, N]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial roughness={0.25} metalness={0.6} />
      </instancedMesh>
    </group>
  );
}

// "AI" label that pops in while the sphere is assembled (~p 0.5).
function AILabel({ progress }: SceneProps) {
  const ref = useRef<THREE.Group>(null);
  const shown = useRef(0);
  useFrame(() => {
    const p = progress.get();
    const target = p > 0.43 && p < 0.6 ? 1 : 0;
    shown.current += (target - shown.current) * 0.12;
    if (ref.current) {
      ref.current.scale.setScalar(0.001 + shown.current * 1.2);
      ref.current.visible = shown.current > 0.01;
    }
  });
  return (
    <Billboard>
      <group ref={ref}>
        <Text fontSize={0.95} color="#ffffff" anchorX="center" anchorY="middle" outlineWidth={0.02} outlineColor="#6366f1">
          AI
        </Text>
      </group>
    </Billboard>
  );
}

function CameraRig({ progress }: SceneProps) {
  useFrame((state) => {
    const p = progress.get();
    state.camera.position.z = 6.2 - p * 1.6;
    state.camera.position.x = Math.sin(p * Math.PI * 2) * 0.7;
    state.camera.position.y = Math.sin(p * Math.PI) * 0.4;
    state.camera.lookAt(0, 0, 0);
  });
  return null;
}

export default function Scene3D({ progress }: SceneProps) {
  return (
    <Canvas
      camera={{ position: [0, 0, 6.2], fov: 45 }}
      gl={{ alpha: true, antialias: true }}
      dpr={[1, 1.8]}
    >
      <ambientLight intensity={0.7} />
      <pointLight position={[5, 5, 6]} intensity={150} color="#a5b4fc" />
      <pointLight position={[-6, -3, 2]} intensity={90} color="#22d3ee" />
      <pointLight position={[0, 5, -5]} intensity={70} color="#f472b6" />
      <Morph progress={progress} />
      <AILabel progress={progress} />
      <Sparkles count={120} scale={14} size={2.2} speed={0.25} opacity={0.4} color="#a5b4fc" />
      <CameraRig progress={progress} />
    </Canvas>
  );
}
