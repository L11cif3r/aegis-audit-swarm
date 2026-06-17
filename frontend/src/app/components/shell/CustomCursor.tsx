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
  // Native <select> popups are OS-drawn: while one is open the page receives no
  // mousemove, so the custom cursor would freeze in place. Hide it during that
  // window and let it reappear on the next real move.
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    setEnabled(true);
    document.documentElement.classList.add('cursor-none');

    const onMove = (e: MouseEvent) => {
      setHidden(false);
      x.set(e.clientX);
      y.set(e.clientY);
      const el = e.target as HTMLElement | null;
      setHovering(
        !!el?.closest('a, button, [role="button"], input, textarea, select, [data-cursor="hover"]'),
      );
    };
    const onDown = (e: MouseEvent) => {
      setPressed(true);
      const el = e.target as HTMLElement | null;
      if (el?.closest('select')) setHidden(true);
    };
    const onUp = () => setPressed(false);
    // ESC / tabbing away from an open select also closes the popup.
    const onKey = () => setHidden(false);

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mousedown', onDown);
    window.addEventListener('mouseup', onUp);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mousedown', onDown);
      window.removeEventListener('mouseup', onUp);
      window.removeEventListener('keydown', onKey);
      document.documentElement.classList.remove('cursor-none');
    };
  }, [x, y]);

  if (!enabled) return null;

  return (
    <>
      <motion.div
        className="pointer-events-none fixed left-0 top-0 z-[9999] rounded-full bg-brand mix-blend-difference"
        style={{ x, y, width: 7, height: 7, marginLeft: -3.5, marginTop: -3.5 }}
        animate={{ scale: pressed ? 0.6 : 1, opacity: hidden ? 0 : 1 }}
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
      />
      <motion.div
        className="pointer-events-none fixed left-0 top-0 z-[9999] rounded-full border border-brand/60"
        style={{ x: ringX, y: ringY, width: 34, height: 34, marginLeft: -17, marginTop: -17 }}
        animate={{
          scale: hovering ? 1.7 : pressed ? 0.8 : 1,
          opacity: hidden ? 0 : hovering ? 0.9 : 0.45,
          backgroundColor: hovering ? 'var(--brand-soft)' : 'rgba(0,0,0,0)',
        }}
        transition={{ type: 'spring', stiffness: 260, damping: 22 }}
      />
    </>
  );
}
