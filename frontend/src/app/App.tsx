import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  Activity, ShieldAlert, Users, AudioLines, Wallet, BadgeCheck, FileLock2,
} from 'lucide-react';

import Background from './components/shell/Background';
import LoadingScreen from './components/shell/LoadingScreen';
import TopNav, { type TabDef } from './components/shell/TopNav';
import CustomCursor from './components/shell/CustomCursor';
import Landing from './components/landing/Landing';
import { apiGet } from '../lib/api';

import Component01DashboardOverview from '../imports/01DashboardOverview';
import Component02SecurityCenter from '../imports/02SecurityCenter';
import Component03LeadPipeline from '../imports/03LeadPipeline';
import Component04VoiceAgent from '../imports/04VoiceAgent';
import Component05CostBilling from '../imports/05CostBilling';
import Component06Compliance from '../imports/06Compliance';
import Component07Evidence from '../imports/07Evidence';

const TABS: TabDef[] = [
  { id: 'dashboard', label: 'Overview', icon: Activity },
  { id: 'security', label: 'Security', icon: ShieldAlert },
  { id: 'leads', label: 'Leads', icon: Users },
  { id: 'voice', label: 'Voice', icon: AudioLines },
  { id: 'billing', label: 'Billing', icon: Wallet },
  { id: 'compliance', label: 'Trust', icon: BadgeCheck },
  { id: 'evidence', label: 'Evidence', icon: FileLock2 },
];

const VIEWS: Record<string, React.ComponentType> = {
  dashboard: Component01DashboardOverview,
  security: Component02SecurityCenter,
  leads: Component03LeadPipeline,
  voice: Component04VoiceAgent,
  billing: Component05CostBilling,
  compliance: Component06Compliance,
  evidence: Component07Evidence,
};

type Phase = 'loading' | 'landing' | 'app';

export default function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [phase, setPhase] = useState<Phase>('loading');
  const [live, setLive] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setPhase('landing'), 1700);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    // Reset scroll when leaving the landing experience.
    if (phase === 'app') window.scrollTo({ top: 0 });
  }, [phase]);

  useEffect(() => {
    const ping = async () => {
      try {
        await apiGet('/health');
        setLive(true);
      } catch {
        setLive(false);
      }
    };
    ping();
    const interval = setInterval(ping, 5000);
    return () => clearInterval(interval);
  }, []);

  const View = VIEWS[currentView] ?? Component01DashboardOverview;

  return (
    <div className="relative min-h-screen w-full text-ink font-['Inter',sans-serif] selection:bg-brand/30">
      <Background />
      <CustomCursor />

      <AnimatePresence>{phase === 'loading' && <LoadingScreen key="loader" />}</AnimatePresence>

      <AnimatePresence mode="wait">
        {phase === 'landing' && (
          <Landing key="landing" onEnter={() => setPhase('app')} />
        )}

        {phase === 'app' && (
          <motion.div
            key="app"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          >
            <TopNav tabs={TABS} current={currentView} onChange={setCurrentView} live={live} />

            <main className="relative mx-auto w-full max-w-7xl px-5 sm:px-8 lg:px-10 pt-28 pb-24 sm:pt-32">
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentView}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                >
                  <View />
                </motion.div>
              </AnimatePresence>

              <footer className="mt-20 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-hairline pt-6 text-[11px] text-soft">
                <span>Aegis Audit Swarm — Talamanda AI Trust Layer</span>
                <span className="flex items-center gap-1.5">
                  <span className={`size-1.5 rounded-full ${live ? 'bg-ok' : 'bg-bad'}`} />
                  {live ? 'Gateway connected' : 'Gateway offline'}
                </span>
              </footer>
            </main>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
