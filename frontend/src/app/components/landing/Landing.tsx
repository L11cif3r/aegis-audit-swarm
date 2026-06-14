import { Suspense, lazy, useRef } from 'react';
import type { ReactNode } from 'react';
import { motion, useScroll, useTransform, useSpring } from 'motion/react';
import { ShieldHalf, ChevronDown, ScanLine, Crosshair, BadgeCheck, ArrowRight } from 'lucide-react';
import ThemeToggle from '../shell/ThemeToggle';
import Magnetic from '../shell/Magnetic';

const Scene3D = lazy(() => import('./Scene3D'));

interface LandingProps {
  onEnter: () => void;
}

// One full-height section whose content drifts + fades based on its own scroll
// position — gives the "scroll-integrated" feel across the whole page.
function ScrollSection({ children, align = 'center' }: { children: ReactNode; align?: 'center' | 'left' }) {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] });
  const opacity = useTransform(scrollYProgress, [0, 0.28, 0.72, 1], [0, 1, 1, 0]);
  const y = useTransform(scrollYProgress, [0, 0.5, 1], [80, 0, -80]);
  const scale = useTransform(scrollYProgress, [0, 0.5, 1], [0.95, 1, 0.95]);

  const justify = align === 'left' ? 'justify-center lg:justify-start' : 'justify-center';
  const textAlign = align === 'left' ? 'text-center lg:text-left' : 'text-center';

  return (
    <section ref={ref} className={`relative min-h-screen flex items-center px-6 sm:px-12 lg:px-24 ${justify}`}>
      <motion.div style={{ opacity, y, scale }} className={`${align === 'left' ? 'max-w-md' : 'max-w-3xl'} ${textAlign}`}>
        {children}
      </motion.div>
    </section>
  );
}

function Kicker({ children, align = 'center' }: { children: ReactNode; align?: 'center' | 'left' }) {
  return (
    <div className={`flex items-center gap-2.5 mb-5 ${align === 'left' ? 'justify-center lg:justify-start' : 'justify-center'}`}>
      <span className="h-px w-8 bg-brand/60" />
      <span className="text-[11px] font-semibold tracking-[0.28em] uppercase text-brand">{children}</span>
      {align === 'center' && <span className="h-px w-8 bg-brand/60" />}
    </div>
  );
}

const STEPS = [
  { icon: ScanLine, kicker: 'Intercept', title: 'Every agent action, refereed.', body: 'Aegis sits inline between your AI agents and the world — scanning, redacting, and gating every action before it can ever land.' },
  { icon: Crosshair, kicker: 'Red-team', title: 'Adversaries, simulated in real time.', body: 'A continuous probe battery attacks each action — injection, jailbreak, logic manipulation — and scores the risk in milliseconds.' },
  { icon: BadgeCheck, kicker: 'Certify', title: 'Proof that stands up in court.', body: 'Outcomes are hash-chained and cryptographically signed into an immutable ledger — a live Trust Score and audit-ready evidence.' },
];

export default function Landing({ onEnter }: LandingProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ['start start', 'end end'] });
  const smooth = useSpring(scrollYProgress, { stiffness: 80, damping: 24, mass: 0.4 });

  const scrollHintOpacity = useTransform(scrollYProgress, [0, 0.06], [1, 0]);
  const barScaleX = useTransform(smooth, [0, 1], [0, 1]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, filter: 'blur(8px)' }}
      transition={{ duration: 0.6 }}
      ref={containerRef}
      className="relative"
    >
      {/* Fixed 3D canvas behind the scrolling copy */}
      <div className="fixed inset-0 -z-[5] pointer-events-none">
        <Suspense fallback={null}>
          <Scene3D progress={smooth} />
        </Suspense>
      </div>

      {/* Minimal top bar */}
      <div className="fixed top-0 inset-x-0 z-40 flex items-center justify-between px-5 sm:px-8 py-5">
        <div className="flex items-center gap-2">
          <div className="size-7 rounded-xl grid place-items-center bg-brand text-brandink">
            <ShieldHalf size={15} />
          </div>
          <span className="font-display text-sm text-ink">AEGIS</span>
        </div>
        <ThemeToggle />
      </div>

      {/* Scroll progress bar */}
      <motion.div
        className="fixed top-0 left-0 right-0 z-50 h-[3px] origin-left bg-brand"
        style={{ scaleX: barScaleX }}
      />

      {/* Hero */}
      <section className="relative min-h-screen grid place-items-center px-6">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          className="text-center"
        >
          <Kicker>Talamanda AI Trust Layer</Kicker>
          <h1 className="font-display text-[20vw] sm:text-[16vw] lg:text-[12rem] leading-[0.85] text-ink">
            AEGIS
          </h1>
          <p className="mt-6 text-base sm:text-lg text-soft max-w-xl mx-auto leading-relaxed">
            A sovereign trust &amp; governance layer for enterprise AI — intercept, red-team, and certify every agent action.
          </p>
        </motion.div>

        <motion.div
          style={{ opacity: scrollHintOpacity }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-soft"
        >
          <span className="text-[10px] uppercase tracking-[0.25em]">Scroll</span>
          <motion.div animate={{ y: [0, 8, 0] }} transition={{ duration: 1.6, repeat: Infinity }}>
            <ChevronDown size={18} />
          </motion.div>
        </motion.div>
      </section>

      {/* Narrative steps — frosted side panels so copy stays readable over the 3D */}
      {STEPS.map((s) => {
        const Icon = s.icon;
        return (
          <ScrollSection key={s.kicker} align="left">
            <div className="rounded-3xl border border-hairline bg-surface/60 backdrop-blur-xl p-7 sm:p-9 shadow-2xl shadow-black/10">
              <span className="inline-grid size-14 place-items-center rounded-2xl bg-brandsoft text-brand mb-6 mx-auto lg:mx-0">
                <Icon size={26} />
              </span>
              <Kicker align="left">{s.kicker}</Kicker>
              <h2 className="font-display text-4xl sm:text-5xl text-ink text-balance">{s.title}</h2>
              <p className="mt-5 text-base text-soft leading-relaxed">{s.body}</p>
            </div>
          </ScrollSection>
        );
      })}

      {/* Explore / enter */}
      <ScrollSection>
        <Kicker>Enter</Kicker>
        <h2 className="font-display text-5xl sm:text-7xl text-ink text-balance">The Control Plane awaits.</h2>
        <p className="mt-5 text-base sm:text-lg text-soft max-w-lg mx-auto leading-relaxed">
          Step inside the live dashboard and watch your AI swarm being refereed in real time.
        </p>
        <Magnetic className="mt-10" strength={0.5}>
          <button
            onClick={onEnter}
            data-cursor="hover"
            className="group inline-flex items-center gap-2.5 rounded-full bg-brand text-brandink font-semibold text-sm px-7 py-4 shadow-xl shadow-brand/20 hover:opacity-95 transition-opacity"
          >
            Explore
            <ArrowRight size={17} className="transition-transform group-hover:translate-x-1" />
          </button>
        </Magnetic>
      </ScrollSection>
    </motion.div>
  );
}
