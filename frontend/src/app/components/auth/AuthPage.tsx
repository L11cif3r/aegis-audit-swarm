import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ShieldHalf, ArrowRight, ArrowLeft, Loader2, Mail, Lock, User } from 'lucide-react';
import ThemeToggle from '../shell/ThemeToggle';
import Magnetic from '../shell/Magnetic';
import { useAuth } from '../../../lib/auth';
import { api } from '../../../lib/api';

interface AuthPageProps {
  onBack: () => void;
  onAuthed: () => void;
  initialMode?: 'login' | 'signup';
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_LEN = 10;

type Mode = 'login' | 'signup' | 'forgot';

export default function AuthPage({ onBack, onAuthed, initialMode = 'login' }: AuthPageProps) {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const isSignup = mode === 'signup';
  const isForgot = mode === 'forgot';

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);

    if (!EMAIL_RE.test(email)) {
      setError('Enter a valid email address.');
      return;
    }

    if (isForgot) {
      setBusy(true);
      try {
        const res = await api.auth.forgotPassword(email.trim());
        setNotice(res.message || 'If that email exists, a reset link has been sent.');
      } catch {
        setNotice('If that email exists, a reset link has been sent.');
      } finally {
        setBusy(false);
      }
      return;
    }

    if (password.length < MIN_LEN) {
      setError(`Password must be at least ${MIN_LEN} characters.`);
      return;
    }
    if (isSignup && password !== confirm) {
      setError('Passwords do not match.');
      return;
    }

    setBusy(true);
    try {
      if (isSignup) await signup(email.trim(), password, name.trim() || undefined);
      else await login(email.trim(), password);
      onAuthed();
    } catch (err: any) {
      setError(err?.message?.replace(/^POST [^ ]+ -> /, '') || 'Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  }

  function swap(next: Mode) {
    setMode(next);
    setError(null);
    setNotice(null);
    setConfirm('');
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, filter: 'blur(8px)' }}
      transition={{ duration: 0.5 }}
      className="relative min-h-screen w-full grid place-items-center px-5 py-16"
    >
      {/* Top bar */}
      <div className="fixed top-0 inset-x-0 z-40 flex items-center justify-between px-5 sm:px-8 py-5">
        <button
          onClick={onBack}
          data-cursor="hover"
          className="flex items-center gap-2 text-soft hover:text-ink transition-colors"
        >
          <ArrowLeft size={16} />
          <span className="text-[13px] font-medium">Back</span>
        </button>
        <ThemeToggle />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 28, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-md"
      >
        <div className="rounded-3xl border border-hairline bg-surface/70 backdrop-blur-2xl p-7 sm:p-9 shadow-2xl shadow-black/20">
          {/* Brand */}
          <div className="flex flex-col items-center text-center mb-7">
            <div className="size-12 rounded-2xl grid place-items-center bg-brand text-brandink mb-4 shadow-lg shadow-brand/25">
              <ShieldHalf size={24} />
            </div>
            <h1 className="font-display text-2xl text-ink">
              {isForgot ? 'Reset your password' : isSignup ? 'Create your trust layer' : 'Welcome back'}
            </h1>
            <p className="mt-2 text-[13px] text-soft leading-relaxed">
              {isForgot
                ? "Enter your email and we'll send you a reset link."
                : isSignup
                  ? 'One account, one isolated tenant — your keys, logs, and evidence stay yours.'
                  : 'Sign in to your Aegis control plane.'}
            </p>
          </div>

          <form onSubmit={submit} className="flex flex-col gap-3.5">
            <AnimatePresence initial={false}>
              {isSignup && (
                <motion.div
                  key="name"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.3 }}
                  className="overflow-hidden"
                >
                  <Field
                    icon={User}
                    type="text"
                    placeholder="Name (optional)"
                    value={name}
                    onChange={setName}
                    autoComplete="name"
                  />
                </motion.div>
              )}
            </AnimatePresence>

            <Field
              icon={Mail}
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={setEmail}
              autoComplete="email"
              required
            />
            {!isForgot && (
              <Field
                icon={Lock}
                type="password"
                placeholder="Password"
                value={password}
                onChange={setPassword}
                autoComplete={isSignup ? 'new-password' : 'current-password'}
                required
              />
            )}

            {mode === 'login' && (
              <div className="-mt-1 text-right">
                <button
                  type="button"
                  onClick={() => swap('forgot')}
                  data-cursor="hover"
                  className="text-[12.5px] text-soft hover:text-brand transition-colors"
                >
                  Forgot password?
                </button>
              </div>
            )}

            <AnimatePresence initial={false}>
              {isSignup && (
                <motion.div
                  key="confirm"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.3 }}
                  className="overflow-hidden"
                >
                  <Field
                    icon={Lock}
                    type="password"
                    placeholder="Confirm password"
                    value={confirm}
                    onChange={setConfirm}
                    autoComplete="new-password"
                  />
                </motion.div>
              )}
            </AnimatePresence>

            <AnimatePresence>
              {error && (
                <motion.p
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-[12.5px] text-bad bg-bad/10 border border-bad/20 rounded-xl px-3.5 py-2.5"
                >
                  {error}
                </motion.p>
              )}
              {notice && (
                <motion.p
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-[12.5px] text-ok bg-ok/10 border border-ok/20 rounded-xl px-3.5 py-2.5"
                >
                  {notice}
                </motion.p>
              )}
            </AnimatePresence>

            <Magnetic strength={0.25} className="mt-1.5 w-full">
              <button
                type="submit"
                disabled={busy}
                data-cursor="hover"
                className="group w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-brand text-brandink font-semibold text-sm px-6 py-3.5 shadow-xl shadow-brand/20 hover:opacity-95 transition-opacity disabled:opacity-60"
              >
                {busy ? (
                  <Loader2 size={17} className="animate-spin" />
                ) : (
                  <>
                    {isForgot ? 'Send reset link' : isSignup ? 'Create account' : 'Sign in'}
                    <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
                  </>
                )}
              </button>
            </Magnetic>
          </form>

          <div className="mt-6 text-center text-[13px] text-soft">
            {isForgot ? (
              <>
                Remembered it?{' '}
                <button
                  onClick={() => swap('login')}
                  data-cursor="hover"
                  className="font-semibold text-brand hover:underline"
                >
                  Back to sign in
                </button>
              </>
            ) : (
              <>
                {isSignup ? 'Already have an account?' : "Don't have an account?"}{' '}
                <button
                  onClick={() => swap(isSignup ? 'login' : 'signup')}
                  data-cursor="hover"
                  className="font-semibold text-brand hover:underline"
                >
                  {isSignup ? 'Sign in' : 'Sign up'}
                </button>
              </>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

function Field({
  icon: Icon,
  type,
  placeholder,
  value,
  onChange,
  autoComplete,
  required,
}: {
  icon: typeof Mail;
  type: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
  required?: boolean;
}) {
  return (
    <label className="relative flex items-center">
      <Icon size={16} className="absolute left-3.5 text-soft pointer-events-none" />
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required={required}
        className="w-full rounded-2xl border border-hairline bg-page/50 pl-10 pr-4 py-3 text-sm text-ink placeholder:text-soft/70 outline-none transition-colors focus:border-brand/60 focus:bg-page"
      />
    </label>
  );
}
