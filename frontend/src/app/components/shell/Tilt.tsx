import type { ReactNode } from 'react';
import { motion, useMotionValue, useSpring, useTransform, useMotionTemplate } from 'motion/react';

interface TiltProps {
  children: ReactNode;
  className?: string;
  max?: number;       // max rotation in degrees
  glare?: boolean;    // moving light reflection
  scale?: number;     // hover scale
}

// Interactive 3D tilt that follows the pointer, with an optional glare sweep.
// Children can use `translateZ(...)` to float above the surface (the inner
// layer keeps `transform-style: preserve-3d`).
export default function Tilt({ children, className = '', max = 9, glare = true, scale = 1.02 }: TiltProps) {
  const rx = useMotionValue(0);
  const ry = useMotionValue(0);
  const px = useMotionValue(50);
  const py = useMotionValue(50);

  const srx = useSpring(rx, { stiffness: 200, damping: 18 });
  const sry = useSpring(ry, { stiffness: 200, damping: 18 });

  const glareBg = useMotionTemplate`radial-gradient(circle at ${px}% ${py}%, rgba(255,255,255,0.22), transparent 45%)`;

  function handleMove(e: React.MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const fx = (e.clientX - rect.left) / rect.width;
    const fy = (e.clientY - rect.top) / rect.height;
    ry.set((fx - 0.5) * max * 2);
    rx.set(-(fy - 0.5) * max * 2);
    px.set(fx * 100);
    py.set(fy * 100);
  }

  function handleLeave() {
    rx.set(0);
    ry.set(0);
  }

  return (
    <motion.div
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      whileHover={{ scale }}
      style={{ rotateX: srx, rotateY: sry, transformPerspective: 900, transformStyle: 'preserve-3d' }}
      transition={{ type: 'spring', stiffness: 260, damping: 20 }}
      className={`group/tilt relative ${className}`}
    >
      {children}
      {glare && (
        <motion.div
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-300 group-hover/tilt:opacity-100"
          style={{ background: glareBg, mixBlendMode: 'overlay' }}
        />
      )}
    </motion.div>
  );
}
