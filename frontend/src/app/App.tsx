import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  Activity, ShieldAlert, Users, AudioLines, Wallet, BadgeCheck, FileLock2, Server, Plug,
} from 'lucide-react';

import Background from './components/shell/Background';
import LoadingScreen from './components/shell/LoadingScreen';
import TopNav, { type TabDef } from './components/shell/TopNav';
import CustomCursor from './components/shell/CustomCursor';
import Saturn from './components/shell/Saturn';
import Landing from './components/landing/Landing';
import AuthPage from './components/auth/AuthPage';
import AccountActionPage from './components/auth/AccountActionPage';
import { apiGet } from '../lib/api';
import { useAuth } from '../lib/auth';

// Detect a verify-email / reset-password deep link from the URL.
function readAccountAction():
  | { action: 'verify-email' | 'reset-password'; token: string }
  | null {
  if (typeof window === 'undefined') return null;
  const path = window.location.pathname;
  const token = new URLSearchParams(window.location.search).get('token');
  if (!token) return null;
  if (path.endsWith('/verify-email')) return { action: 'verify-email', token };
  if (path.endsWith('/reset-password')) return { action: 'reset-password', token };
  return null;
}

import Component01DashboardOverview from '../imports/01DashboardOverview';
import Component02SecurityCenter from '../imports/02SecurityCenter';
import Component03LeadPipeline from '../imports/03LeadPipeline';
import Component04Sessions from '../imports/04Sessions';
import Component05CostBilling from '../imports/05CostBilling';
import Component06Compliance from '../imports/06Compliance';
import Component07Evidence from '../imports/07Evidence';
import Component08GatewayConfig from '../imports/08GatewayConfig';
import Component09Integration from '../imports/09Integration';

const TABS: TabDef[] = [
  { id: 'dashboard', label: 'Overview', icon: Activity },
  { id: 'security', label: 'Security', icon: ShieldAlert },
  { id: 'gateway', label: 'Gateway', icon: Server },
  { id: 'integration', label: 'Integration', icon: Plug },
  { id: 'leads', label: 'Leads', icon: Users },
  { id: 'sessions', label: 'Sessions', icon: AudioLines },
  { id: 'billing', label: 'Billing', icon: Wallet },
  { id: 'compliance', label: 'Trust', icon: BadgeCheck },
  { id: 'evidence', label: 'Evidence', icon: FileLock2 },
];

const VIEWS: Record<string, React.ComponentType> = {
  dashboard: Component01DashboardOverview,
  security: Component02SecurityCenter,
  leads: Component03LeadPipeline,
  sessions: Component04Sessions,
  billing: Component05CostBilling,
  compliance: Component06Compliance,
  evidence: Component07Evidence,
  gateway: Component08GatewayConfig,
  integration: Component09Integration,
};

type Phase = 'loading' | 'landing' | 'auth' | 'app';

export default function App() {
  const { authed, ready, logout, user } = useAuth();
  const [currentView, setCurrentView] = useState('dashboard');
  const [phase, setPhase] = useState<Phase>('loading');
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');
  const [booted, setBooted] = useState(false);
  const [live, setLive] = useState(false);
  const [accountAction, setAccountAction] = useState(() => readAccountAction());

  const clearAccountAction = () => {
    setAccountAction(null);
    // Strip the token from the URL so it isn't reused or bookmarked.
    if (typeof window !== 'undefined') {
      window.history.replaceState({}, '', window.location.pathname.replace(/\/(verify-email|reset-password)$/, '/') || '/');
    }
    setPhase('auth');
    setAuthMode('login');
  };

  useEffect(() => {
    const t = setTimeout(() => setBooted(true), 1700);
    return () => clearTimeout(t);
  }, []);

  // Once the loading screen has played and the session is validated, route to
  // the dashboard if already signed in, otherwise the landing experience.
  useEffect(() => {
    if (phase === 'loading' && booted && ready) {
      setPhase(authed ? 'app' : 'landing');
    }
  }, [phase, booted, ready, authed]);

  // If the session is lost (logout or a 401), drop back to the landing page.
  useEffect(() => {
    if (ready && !authed && phase === 'app') setPhase('landing');
  }, [ready, authed, phase]);

  useEffect(() => {
    // Reset scroll when entering the dashboard.
    if (phase === 'app') window.scrollTo({ top: 0 });
  }, [phase]);

  const goAuth = (mode: 'login' | 'signup') => {
    setAuthMode(mode);
    setPhase('auth');
  };

  const handleExplore = () => {
    if (authed) setPhase('app');
    else goAuth('login');
  };

  const handleLogout = () => {
    logout();
    setCurrentView('dashboard');
    setPhase('landing');
  };

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

      <AnimatePresence>
        {phase === 'loading' && !accountAction && <LoadingScreen key="loader" />}
      </AnimatePresence>

      {accountAction && (
        <AccountActionPage
          action={accountAction.action}
          token={accountAction.token}
          onDone={clearAccountAction}
        />
      )}

      <AnimatePresence mode="wait">
        {!accountAction && phase === 'landing' && (
          <Landing
            key="landing"
            onExplore={handleExplore}
            onLogin={() => goAuth('login')}
            onSignup={() => goAuth('signup')}
            authed={authed}
          />
        )}

        {!accountAction && phase === 'auth' && (
          <AuthPage
            key="auth"
            initialMode={authMode}
            onBack={() => setPhase('landing')}
            onAuthed={() => setPhase('app')}
          />
        )}

        {!accountAction && phase === 'app' && (
          <motion.div
            key="app"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          >
            <TopNav
              tabs={TABS}
              current={currentView}
              onChange={setCurrentView}
              live={live}
              user={user}
              onLogout={handleLogout}
            />

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

            <Saturn />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
