import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { ShieldHalf, Loader2, CheckCircle2, XCircle, Lock, ArrowRight } from 'lucide-react';
import ThemeToggle from '../shell/ThemeToggle';
import { api } from '../../../lib/api';

type Action = 'verify-email' | 'reset-password';
type State = 'idle' | 'working' | 'done' | 'error';

interface Props {
  action: Action;
  token: string;
  onDone: () => void;
}

const MIN_LEN = 10;

export default function AccountActionPage({ action, token, onDone }: Props) {
  const [state, setState] = useState<State>('idle');
  const [message, setMessage] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');

  // Email verification runs automatically; password reset waits for input.
  useEffect(() => {
    if (action !== 'verify-email') return;
    let cancelled = false;
    (async () => {
      setState('working');
      try {
        await api.auth.verifyEmail(token);
        if (!cancelled) {
          setState('done');
          setMessage('Your email is verified. You can sign in now.');
        }
      } catch (err: any) {
        if (!cancelled) {
          setState('error');
          setMessage(clean(err) || 'This verification link is invalid or expired.');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [action, token]);

  async function submitReset(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < MIN_LEN) {
      setState('error');
      setMessage(`Password must be at least ${MIN_LEN} characters.`);
      return;
    }
    if (password !== confirm) {
      setState('error');
      setMessage('Passwords do not match.');
      return;
    }
    setState('working');
    try {
      await api.auth.resetPassword({ token, new_password: password });
      setState('done');
      setMessage('Password updated. You can sign in with your new password.');
    } catch (err: any) {
      setState('error');
      setMessage(clean(err) || 'This reset link is invalid or expired.');
    }
  }

  const title = action === 'verify-email' ? 'Verify your email' : 'Reset your password';

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="relative min-h-screen w-full grid place-items-center px-5 py-16"
    >
      <div className="fixed top-0 inset-x-0 z-40 flex items-center justify-end px-5 sm:px-8 py-5">
        <ThemeToggle />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 28, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-md"
      >
        <div className="rounded-3xl border border-hairline bg-surface/70 backdrop-blur-2xl p-7 sm:p-9 shadow-2xl shadow-black/20">
          <div className="flex flex-col items-center text-center mb-7">
            <div className="size-12 rounded-2xl grid place-items-center bg-brand text-brandink mb-4 shadow-lg shadow-brand/25">
              <ShieldHalf size={24} />
            </div>
            <h1 className="font-display text-2xl text-ink">{title}</h1>
          </div>

          {state === 'working' && (
            <div className="flex items-center justify-center gap-2 text-soft py-6">
              <Loader2 size={18} className="animate-spin" /> Working…
            </div>
          )}

          {(state === 'done' || (state === 'error' && action === 'verify-email')) && (
            <div className="flex flex-col items-center text-center gap-4 py-3">
              {state === 'done' ? (
                <CheckCircle2 size={40} className="text-ok" />
              ) : (
                <XCircle size={40} className="text-bad" />
              )}
              <p className="text-[13.5px] text-soft leading-relaxed">{message}</p>
              <button
                onClick={onDone}
                data-cursor="hover"
                className="mt-1 inline-flex items-center justify-center gap-2 rounded-2xl bg-brand text-brandink font-semibold text-sm px-6 py-3 shadow-xl shadow-brand/20 hover:opacity-95 transition-opacity"
              >
                Continue to sign in <ArrowRight size={16} />
              </button>
            </div>
          )}

          {action === 'reset-password' && state !== 'done' && (
            <form onSubmit={submitReset} className="flex flex-col gap-3.5">
              <Field
                type="password"
                placeholder="New password"
                value={password}
                onChange={setPassword}
              />
              <Field
                type="password"
                placeholder="Confirm new password"
                value={confirm}
                onChange={setConfirm}
              />
              {state === 'error' && (
                <p className="text-[12.5px] text-bad bg-bad/10 border border-bad/20 rounded-xl px-3.5 py-2.5">
                  {message}
                </p>
              )}
              <button
                type="submit"
                disabled={state === 'working'}
                data-cursor="hover"
                className="mt-1.5 w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-brand text-brandink font-semibold text-sm px-6 py-3.5 shadow-xl shadow-brand/20 hover:opacity-95 transition-opacity disabled:opacity-60"
              >
                {state === 'working' ? <Loader2 size={17} className="animate-spin" /> : 'Update password'}
              </button>
            </form>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

function clean(err: any): string {
  return err?.message?.replace(/^POST [^ ]+ -> /, '') ?? '';
}

function Field({
  type,
  placeholder,
  value,
  onChange,
}: {
  type: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="relative flex items-center">
      <Lock size={16} className="absolute left-3.5 text-soft pointer-events-none" />
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete="new-password"
        required
        className="w-full rounded-2xl border border-hairline bg-page/50 pl-10 pr-4 py-3 text-sm text-ink placeholder:text-soft/70 outline-none transition-colors focus:border-brand/60 focus:bg-page"
      />
    </label>
  );
}
