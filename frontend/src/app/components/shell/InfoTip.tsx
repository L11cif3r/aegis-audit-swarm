import { useId, useState } from 'react';
import { Info } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';

/** Small (i) with a hover/focus tooltip — for complex metrics & labels. */
export default function InfoTip({ text, className = '' }: { text: string; className?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span
      className={`relative inline-flex align-middle ${className}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <button
        type="button"
        aria-describedby={open ? id : undefined}
        aria-label="More information"
        data-cursor="hover"
        className="grid size-4 place-items-center rounded-full border border-hairline bg-surface2/80 text-soft hover:text-brand hover:border-brand/40 transition-colors"
      >
        <Info size={10} strokeWidth={2.5} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            id={id}
            role="tooltip"
            initial={{ opacity: 0, y: 4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            className="absolute left-1/2 bottom-full z-50 mb-2 w-64 -translate-x-1/2 rounded-xl border border-hairline bg-surface/98 px-3 py-2.5 text-[11px] leading-relaxed text-soft shadow-xl shadow-black/10 backdrop-blur-md"
          >
            {text}
            <span className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-[var(--hairline)]" />
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  );
}
