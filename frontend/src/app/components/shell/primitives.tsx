import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { motion } from 'motion/react';
import Reveal from './Reveal';
import Tilt from './Tilt';
import CountUp from './CountUp';

export function PageHeader({ title, subtitle, kicker }: { title: string; subtitle?: string; kicker?: string }) {
  return (
    <Reveal>
      <div className="flex flex-col gap-3 max-w-3xl">
        {kicker && (
          <div className="flex items-center gap-2.5">
            <span className="h-px w-8 bg-brand/60" />
            <span className="text-[11px] font-semibold tracking-[0.24em] uppercase text-brand">{kicker}</span>
          </div>
        )}
        <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl text-ink text-balance">{title}</h1>
        {subtitle && <p className="text-sm sm:text-base text-soft max-w-xl leading-relaxed">{subtitle}</p>}
      </div>
    </Reveal>
  );
}

export function Panel({ children, className = '', padded = true }: { children: ReactNode; className?: string; padded?: boolean }) {
  return (
    <div className={`card-surface card-lift rounded-2xl backdrop-blur-sm ${padded ? 'p-5 sm:p-6' : ''} ${className}`}>
      {children}
    </div>
  );
}

const TONES: Record<string, string> = {
  brand: 'var(--brand)',
  ok: 'var(--ok)',
  warn: 'var(--warn)',
  bad: 'var(--bad)',
};

export function Stat({
  label, value, count, prefix = '', suffix = '', decimals = 0, icon: Icon, tone = 'brand', sub,
}: {
  label: string;
  value?: ReactNode;
  count?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  icon?: LucideIcon;
  tone?: keyof typeof TONES;
  sub?: string;
}) {
  const color = TONES[tone] ?? TONES.brand;
  return (
    <Tilt className="h-full" max={8}>
      <div className="card-surface card-lift group relative h-full overflow-hidden rounded-2xl p-5 flex flex-col gap-3 preserve-3d">
        <div
          className="absolute -right-8 -top-8 size-28 rounded-full blur-2xl opacity-0 group-hover:opacity-80 transition-opacity duration-500"
          style={{ background: color }}
        />
        <div className="relative flex items-center justify-between pop-z-sm">
          <span className="text-[10px] font-bold uppercase tracking-wider text-soft">{label}</span>
          {Icon && (
            <span className="grid size-8 place-items-center rounded-xl" style={{ background: 'var(--brand-soft)', color }}>
              <Icon size={15} />
            </span>
          )}
        </div>
        <span className="relative pop-z text-3xl sm:text-4xl font-bold font-display tracking-tight text-ink leading-none">
          {count !== undefined ? (
            <CountUp value={count} decimals={decimals} prefix={prefix} suffix={suffix} />
          ) : (
            value
          )}
        </span>
        {sub && <span className="relative text-[11px] text-soft pop-z-sm">{sub}</span>}
      </div>
    </Tilt>
  );
}

export function Badge({ children, tone = 'brand' }: { children: ReactNode; tone?: 'brand' | 'ok' | 'warn' | 'bad' | 'neutral' }) {
  const map = {
    brand: 'text-brand bg-brandsoft border-brand/20',
    ok: 'text-ok border-current/20',
    warn: 'text-warn border-current/20',
    bad: 'text-bad border-current/20',
    neutral: 'text-soft border-hairline',
  } as const;
  const bg = tone === 'ok' ? 'rgba(16,185,129,0.12)' : tone === 'warn' ? 'rgba(245,158,11,0.12)' : tone === 'bad' ? 'rgba(244,63,94,0.12)' : undefined;
  return (
    <span
      className={`inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-wide px-2 py-0.5 rounded-full border ${map[tone]}`}
      style={bg ? { backgroundColor: bg } : undefined}
    >
      {children}
    </span>
  );
}

export function SectionTitle({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="flex items-baseline justify-between">
      <h2 className="text-sm font-bold text-ink tracking-tight">{children}</h2>
      {hint && <span className="text-[10px] text-soft">{hint}</span>}
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="text-xs text-soft italic text-center py-10">{children}</p>;
}

// Bento grid container — lets views spread content across the full width.
export function Bento({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-5 ${className}`}>{children}</div>;
}

// Animated list-row wrapper for live feeds.
export function FeedRow({ children, i = 0, className = '', style }: { children: ReactNode; i?: number; className?: string; style?: React.CSSProperties }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(i * 0.04, 0.4) }}
      className={className}
      style={style}
    >
      {children}
    </motion.div>
  );
}
