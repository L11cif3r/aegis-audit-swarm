import { useEffect } from 'react';
import { motion, useMotionValue, useSpring, useMotionTemplate } from 'motion/react';

// Abstract, slowly drifting gradient field that also reacts to the pointer,
// plus a subtle dotted grid and film grain. Theme-aware via CSS variables.
export default function Background() {
  const mx = useMotionValue(50);
  const my = useMotionValue(28);
  const sx = useSpring(mx, { stiffness: 50, damping: 20 });
  const sy = useSpring(my, { stiffness: 50, damping: 20 });

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      mx.set((e.clientX / window.innerWidth) * 100);
      my.set((e.clientY / window.innerHeight) * 100);
    };
    window.addEventListener('mousemove', onMove);
    return () => window.removeEventListener('mousemove', onMove);
  }, [mx, my]);

  const pointerGlow = useMotionTemplate`radial-gradient(620px circle at ${sx}% ${sy}%, var(--glow-1), transparent 60%)`;

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden bg-page">
      {/* drifting blobs */}
      <motion.div
        className="absolute -top-48 -left-40 size-[48rem] rounded-full blur-[130px]"
        style={{ background: 'radial-gradient(circle at center, var(--glow-1), transparent 70%)' }}
        animate={{ x: [0, 80, 0], y: [0, 50, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute top-1/4 -right-48 size-[44rem] rounded-full blur-[130px]"
        style={{ background: 'radial-gradient(circle at center, var(--glow-2), transparent 70%)' }}
        animate={{ x: [0, -70, 0], y: [0, 70, 0] }}
        transition={{ duration: 32, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute -bottom-56 left-1/3 size-[42rem] rounded-full blur-[140px]"
        style={{ background: 'radial-gradient(circle at center, var(--glow-3), transparent 70%)' }}
        animate={{ x: [0, 50, 0], y: [0, -50, 0] }}
        transition={{ duration: 30, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* pointer-reactive glow */}
      <motion.div className="absolute inset-0 opacity-70" style={{ background: pointerGlow }} />

      {/* faint dotted grid */}
      <div
        className="absolute inset-0 opacity-[0.4]"
        style={{
          backgroundImage: 'radial-gradient(var(--hairline) 1px, transparent 1px)',
          backgroundSize: '30px 30px',
          maskImage: 'radial-gradient(ellipse at center, black 25%, transparent 80%)',
        }}
      />

      {/* film grain */}
      <div className="grain absolute inset-0 opacity-[0.04] mix-blend-overlay" />
    </div>
  );
}
