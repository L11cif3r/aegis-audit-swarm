import { ShieldHalf, Mail } from 'lucide-react';
import type { MouseEvent } from 'react';
import Magnetic from './Magnetic';

const LINKS = [
  { label: 'Overview', href: '#dashboard' },
  { label: 'Integration', href: '#integration' },
  { label: 'Gateway', href: '#gateway' },
];
const COMPANY = [
  { label: 'Contact', href: 'mailto:hello@aegis.trust' },
  { label: 'Privacy', href: 'mailto:privacy@aegis.trust' },
  { label: 'Support', href: 'mailto:support@aegis.trust' },
];

interface ContactFooterProps {
  live?: boolean;
  onNavigate?: (tab: string) => void;
}

export default function ContactFooter({ live, onNavigate }: ContactFooterProps) {
  const year = new Date().getFullYear();

  const navClick = (tab: string) => (e: MouseEvent) => {
    if (onNavigate) {
      e.preventDefault();
      onNavigate(tab);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  return (
    <footer className="relative mt-24 overflow-hidden">
      {/* Large background contact placeholder — inspired by editorial footers */}
      <p
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 select-none text-center font-display text-[clamp(2.5rem,12vw,7rem)] leading-none text-ink/[0.04] dark:text-ink/[0.06] tracking-tight"
      >
        hello@aegis.trust
      </p>

      <div className="relative grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
        {/* Brand card */}
        <div className="flex flex-col justify-between rounded-3xl bg-brand p-6 sm:p-8 min-h-[220px] text-brandink shadow-lg shadow-brand/20">
          <div className="flex items-center gap-2.5">
            <span className="grid size-10 place-items-center rounded-xl bg-white/15">
              <ShieldHalf size={20} />
            </span>
            <span className="font-display text-xl tracking-tight">AEGIS</span>
          </div>
          <p className="text-[13px] sm:text-sm leading-relaxed text-white/90 max-w-xs">
            Sovereign AI governance — intercept, red-team, and certify every agent action.
          </p>
        </div>

        {/* Links + CTA card */}
        <div className="relative rounded-3xl border border-hairline bg-surface/90 backdrop-blur-sm p-6 sm:p-8 flex flex-col gap-6">
          <span className="absolute right-5 top-5 grid size-9 place-items-center rounded-xl bg-brand text-brandink shadow-md">
            <ShieldHalf size={16} />
          </span>

          <div className="grid sm:grid-cols-2 gap-8 pt-2">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-soft mb-3">Links</p>
              <ul className="space-y-2">
                {LINKS.map((l) => (
                  <li key={l.label}>
                    <a
                      href={l.href}
                      onClick={navClick(l.href.slice(1))}
                      data-cursor="hover"
                      className="text-[13px] text-ink/80 hover:text-brand transition-colors"
                    >
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-soft mb-3">Company</p>
              <ul className="space-y-2">
                {COMPANY.map((l) => (
                  <li key={l.label}>
                    <a
                      href={l.href}
                      data-cursor="hover"
                      className="text-[13px] text-ink/80 hover:text-brand transition-colors"
                    >
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2 border-t border-hairline">
            <div className="flex flex-col gap-1">
              <p className="text-[11px] text-soft">
                © {year} AEGIS — Talamanda AI Trust Layer. All rights reserved.
              </p>
              <p className="flex items-center gap-1.5 text-[11px] text-soft">
                <span className={`size-1.5 rounded-full ${live ? 'bg-ok' : 'bg-bad'}`} />
                {live ? 'Gateway connected' : 'Gateway offline'}
              </p>
            </div>
            <Magnetic>
              <a
                href="mailto:hello@aegis.trust?subject=AEGIS%20demo%20request"
                data-cursor="hover"
                className="inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-[12px] font-semibold text-surface hover:opacity-90 transition-opacity"
              >
                <Mail size={14} />
                Book a call
              </a>
            </Magnetic>
          </div>
        </div>
      </div>
    </footer>
  );
}
