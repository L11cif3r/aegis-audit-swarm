import { motion } from 'motion/react';
import { ShieldHalf } from 'lucide-react';

export default function LoadingScreen() {
  return (
    <motion.div
      className="fixed inset-0 z-[100] grid place-items-center bg-page"
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.6, ease: 'easeInOut' }}
    >
      <div className="flex flex-col items-center gap-6">
        <motion.div
          initial={{ scale: 0.7, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="relative grid place-items-center"
        >
          <motion.span
            className="absolute size-20 rounded-full"
            style={{ background: 'radial-gradient(circle, var(--glow-1), transparent 70%)' }}
            animate={{ scale: [1, 1.3, 1], opacity: [0.5, 0.2, 0.5] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <div className="size-14 rounded-2xl grid place-items-center bg-brand text-brandink shadow-lg">
            <ShieldHalf size={26} />
          </div>
        </motion.div>

        <div className="flex flex-col items-center gap-3">
          <motion.h1
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="font-display text-2xl text-ink"
          >
            AEGIS
          </motion.h1>
          <div className="h-[3px] w-40 rounded-full bg-hairline overflow-hidden">
            <motion.div
              className="h-full rounded-full bg-brand"
              initial={{ width: '0%' }}
              animate={{ width: '100%' }}
              transition={{ duration: 1.4, ease: 'easeInOut' }}
            />
          </div>
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-[11px] tracking-[0.25em] uppercase text-soft"
          >
            Trust Layer
          </motion.span>
        </div>
      </div>
    </motion.div>
  );
}
