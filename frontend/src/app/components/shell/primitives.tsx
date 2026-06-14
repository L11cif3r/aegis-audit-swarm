import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import Reveal from './Reveal';

export function PageHeader({ title, subtitle, kicker }: { title: string; subtitle?: string; kicker?: string }) {
  return (
    <Reveal>
      <div className="flex flex-col gap-2">
        {kicker && (
          <span className="text-[11px] font-semibold tracking-[0.22em] uppercase text-brand">{kicker}</span>
        )}
        <h1 className="font-display text-3xl sm:text-4xl text-ink text-balance">{title}</h1>
        {subtitle && <p className="text-sm text-soft max-w-md leading-relaxed">{subtitle}</p>}
      </div>
    </Reveal>
  );
}

export function Panel({ children, className = '', padded = true }: { children: ReactNode; className?: string; padded?: boolean }) {
  return (
    <div className={`rounded-2xl border border-hairline bg-surface/70 backdrop-blur-sm ${padded ? 'p-5' : ''} ${className}`}>
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
  label, value, icon: Icon, tone = 'brand', sub,
}: { label: string; value: ReactNode; icon?: LucideIcon; tone?: keyof typeof TONES; sub?: string }) {
  const color = TONES[tone] ?? TONES.brand;
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-hairline bg-surface/70 backdrop-blur-sm p-4 flex flex-col gap-3">
      <div
        className="absolute -right-6 -top-6 size-20 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ background: color }}
      />
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-wider text-soft">{label}</span>
        {Icon && <Icon size={15} style={{ color }} />}
      </div>
      <span className="text-3xl font-bold font-display tracking-tight text-ink leading-none tabular-nums">{value}</span>
      {sub && <span className="text-[11px] text-soft">{sub}</span>}
    </div>
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
  return <p className="text-xs text-soft italic text-center py-6">{children}</p>;
}
