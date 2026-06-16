import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ShieldHalf, LogOut, User as UserIcon } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import type { AuthUser } from '../../../lib/session';

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
  user?: AuthUser | null;
  onLogout?: () => void;
}

function UserMenu({ user, onLogout }: { user?: AuthUser | null; onLogout?: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const label = user?.email || user?.display_name || 'Account';
  const initial = (user?.display_name || user?.email || 'A').trim().charAt(0).toUpperCase();

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        onClick={() => setOpen((v) => !v)}
        data-cursor="hover"
        className="grid size-7 place-items-center rounded-full bg-brand text-brandink text-[12px] font-bold"
        title={label}
      >
        {initial}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.16 }}
            className="absolute right-0 mt-2 w-56 rounded-2xl border border-hairline bg-surface/95 backdrop-blur-xl p-2 shadow-xl shadow-black/10"
          >
            <div className="flex items-center gap-2.5 px-2.5 py-2">
              <span className="grid size-8 place-items-center rounded-full bg-brandsoft text-brand">
                <UserIcon size={15} />
              </span>
              <div className="min-w-0">
                <p className="text-[12.5px] font-semibold text-ink truncate">{label}</p>
                {user?.tenant && (
                  <p className="text-[10.5px] text-soft truncate">Tenant {user.tenant}</p>
                )}
              </div>
            </div>
            <div className="my-1 h-px bg-hairline" />
            <button
              onClick={() => {
                setOpen(false);
                onLogout?.();
              }}
              data-cursor="hover"
              className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-[12.5px] font-medium text-soft hover:text-ink hover:bg-page transition-colors"
            >
              <LogOut size={15} />
              Sign out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function TopNav({ tabs, current, onChange, live, user, onLogout }: TopNavProps) {
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

        <div className="flex items-center gap-1 pl-0.5 shrink-0">
          <ThemeToggle />
          <UserMenu user={user} onLogout={onLogout} />
        </div>
      </motion.nav>
    </div>
  );
}
