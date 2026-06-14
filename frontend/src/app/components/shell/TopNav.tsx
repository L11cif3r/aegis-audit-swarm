import { motion } from 'motion/react';
import { ShieldHalf } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import ThemeToggle from './ThemeToggle';

export interface TabDef {
  id: string;
  label: string;
  icon: LucideIcon;
}

interface TopNavProps {
  tabs: TabDef[];
  current: string;
  onChange: (id: string) => void;
  live: boolean;
}

export default function TopNav({ tabs, current, onChange, live }: TopNavProps) {
  return (
    <div className="fixed top-0 inset-x-0 z-50 flex justify-center px-3 pt-3 sm:pt-4">
      <motion.nav
        initial={{ y: -24, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="flex items-center gap-1 sm:gap-2 max-w-full rounded-full border border-hairline bg-surface/80 backdrop-blur-xl pl-2 pr-2 py-1.5 shadow-lg shadow-black/5"
      >
        {/* Brand */}
        <div className="flex items-center gap-2 pl-1.5 pr-2.5 shrink-0">
          <div className="size-7 rounded-xl grid place-items-center bg-brand text-brandink">
            <ShieldHalf size={15} />
          </div>
          <span className="font-display text-sm text-ink hidden sm:block">AEGIS</span>
          <span
            className={`size-1.5 rounded-full ${live ? 'bg-ok' : 'bg-bad'}`}
            style={live ? { boxShadow: '0 0 8px var(--ok)' } : undefined}
          />
        </div>

        <span className="h-5 w-px bg-hairline shrink-0" />

        {/* Tabs */}
        <div className="flex items-center gap-0.5 overflow-x-auto scrollbar-none">
          {tabs.map((tab) => {
            const active = current === tab.id;
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => onChange(tab.id)}
                className="relative shrink-0 flex items-center gap-1.5 rounded-full px-3 py-1.5 transition-colors"
              >
                {active && (
                  <motion.span
                    layoutId="nav-active"
                    className="absolute inset-0 rounded-full bg-brand"
                    transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                  />
                )}
                <span className={`relative z-10 flex items-center gap-1.5 ${active ? 'text-brandink' : 'text-soft hover:text-ink'}`}>
                  <Icon size={14} />
                  <span className="text-[12px] font-semibold tracking-tight hidden md:block">{tab.label}</span>
                </span>
              </button>
            );
          })}
        </div>

        <span className="h-5 w-px bg-hairline shrink-0" />

        <div className="pl-0.5 shrink-0">
          <ThemeToggle />
        </div>
      </motion.nav>
    </div>
  );
}
