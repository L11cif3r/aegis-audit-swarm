import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  Activity, ShieldAlert, Users, AudioLines, Wallet, BadgeCheck, FileLock2,
} from 'lucide-react';

import Background from './components/shell/Background';
import LoadingScreen from './components/shell/LoadingScreen';
import TopNav, { type TabDef } from './components/shell/TopNav';
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

export default function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 1700);
    return () => clearTimeout(t);
  }, []);

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

      <AnimatePresence>{loading && <LoadingScreen key="loader" />}</AnimatePresence>

      <TopNav tabs={TABS} current={currentView} onChange={setCurrentView} live={live} />

      <main className="relative mx-auto w-full max-w-2xl px-4 pt-24 pb-20 sm:pt-28">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentView}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          >
            <View />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
