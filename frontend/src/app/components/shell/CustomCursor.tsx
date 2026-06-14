import { useEffect, useState } from 'react';
import { motion, useMotionValue, useSpring } from 'motion/react';

// A clean two-part cursor: a precise dot that tracks 1:1, and a soft ring that
// lags behind with spring physics and reacts to interactive elements. Only
// enabled on devices with a fine pointer (desktop); native cursor is hidden.
export default function CustomCursor() {
  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  const ringX = useSpring(x, { stiffness: 320, damping: 28, mass: 0.5 });
  const ringY = useSpring(y, { stiffness: 320, damping: 28, mass: 0.5 });

  const [enabled, setEnabled] = useState(false);
  const [hovering, setHovering] = useState(false);
  const [pressed, setPressed] = useState(false);

  useEffect(() => {
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    setEnabled(true);
    document.documentElement.classList.add('cursor-none');

    const onMove = (e: MouseEvent) => {
      x.set(e.clientX);
      y.set(e.clientY);
      const el = e.target as HTMLElement | null;
      setHovering(
        !!el?.closest('a, button, [role="button"], input, textarea, select, [data-cursor="hover"]'),
      );
    };
    const onDown = () => setPressed(true);
    const onUp = () => setPressed(false);

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mousedown', onDown);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mousedown', onDown);
      window.removeEventListener('mouseup', onUp);
      document.documentElement.classList.remove('cursor-none');
    };
  }, [x, y]);

  if (!enabled) return null;

  return (
    <>
      <motion.div
        className="pointer-events-none fixed left-0 top-0 z-[9999] rounded-full bg-brand mix-blend-difference"
        style={{ x, y, width: 7, height: 7, marginLeft: -3.5, marginTop: -3.5 }}
        animate={{ scale: pressed ? 0.6 : 1 }}
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      />
      <motion.div
        className="pointer-events-none fixed left-0 top-0 z-[9999] rounded-full border border-brand/60"
        style={{ x: ringX, y: ringY, width: 34, height: 34, marginLeft: -17, marginTop: -17 }}
        animate={{
          scale: hovering ? 1.7 : pressed ? 0.8 : 1,
          opacity: hovering ? 0.9 : 0.45,
          backgroundColor: hovering ? 'var(--brand-soft)' : 'rgba(0,0,0,0)',
        }}
        transition={{ type: 'spring', stiffness: 260, damping: 22 }}
      />
    </>
  );
}
