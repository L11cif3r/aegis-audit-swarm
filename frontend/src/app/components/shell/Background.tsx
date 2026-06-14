import { motion } from 'motion/react';

// Abstract, slowly drifting gradient field + subtle grid. Theme-aware via
// CSS variables (--glow-1/2/3). Sits fixed behind all content.
export default function Background() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden bg-page">
      <motion.div
        className="absolute -top-40 -left-32 size-[42rem] rounded-full blur-[120px]"
        style={{ background: 'radial-gradient(circle at center, var(--glow-1), transparent 70%)' }}
        animate={{ x: [0, 60, 0], y: [0, 40, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute top-1/3 -right-40 size-[38rem] rounded-full blur-[120px]"
        style={{ background: 'radial-gradient(circle at center, var(--glow-2), transparent 70%)' }}
        animate={{ x: [0, -50, 0], y: [0, 60, 0] }}
        transition={{ duration: 32, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute -bottom-48 left-1/4 size-[36rem] rounded-full blur-[130px]"
        style={{ background: 'radial-gradient(circle at center, var(--glow-3), transparent 70%)' }}
        animate={{ x: [0, 40, 0], y: [0, -40, 0] }}
        transition={{ duration: 30, repeat: Infinity, ease: 'easeInOut' }}
      />
      {/* faint dotted grid */}
      <div
        className="absolute inset-0 opacity-[0.4]"
        style={{
          backgroundImage:
            'radial-gradient(var(--hairline) 1px, transparent 1px)',
          backgroundSize: '28px 28px',
          maskImage: 'radial-gradient(ellipse at center, black 30%, transparent 80%)',
        }}
      />
    </div>
  );
}
