import { useEffect, useState } from 'react';
import { FileLock2, CheckCircle2, XCircle, Gavel } from 'lucide-react';
import { motion } from 'motion/react';
import { api } from '../../lib/api';
import { PageHeader, Panel, SectionTitle, Badge, EmptyState, Bento, FeedRow } from '../../app/components/shell/primitives';
import Reveal from '../../app/components/shell/Reveal';

export default function Component07Evidence() {
  const [ledger, setLedger] = useState<any[]>([]);
  const [verify, setVerify] = useState<any>(null);
  const [pending, setPending] = useState<any[]>([]);

  const refresh = async () => {
    try {
      const [l, v, p] = await Promise.all([api.ledger(30), api.verifyLedger(), api.reviewPending()]);
      setLedger([...l].reverse());
      setVerify(v);
      setPending(p);
    } catch {
      /* offline */
    }
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 4000);
    return () => clearInterval(interval);
  }, []);

  const resolve = async (id: string, decision: 'approved' | 'rejected') => {
    try {
      await api.resolveReview(id, decision);
      refresh();
    } catch {
      /* ignore */
    }
  };

  const valid = verify?.valid;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        kicker="Evidence Ledger"
        title="Proof that can stand up in court."
        subtitle="Cryptographically signed, hash-chained, tamper-evident audit records."
      />

      {/* Chain integrity */}
      <Reveal delay={0.05}>
        <Panel className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="size-12 rounded-xl grid place-items-center" style={{ background: valid ? 'rgba(16,185,129,0.12)' : 'rgba(244,63,94,0.12)' }}>
              <FileLock2 size={20} style={{ color: valid ? 'var(--ok)' : 'var(--bad)' }} />
            </div>
            <div className="flex flex-col">
              <span className="text-[14px] font-semibold text-ink">Chain Integrity</span>
              <span className="text-[11px] text-soft">{verify?.records ?? 0} signed records · SHA-256 hash-chained · RSA-2048</span>
            </div>
          </div>
          <Badge tone={valid === undefined ? 'neutral' : valid ? 'ok' : 'bad'}>
            {valid === undefined ? '…' : valid ? 'Verified' : 'Tampered'}
          </Badge>
        </Panel>
      </Reveal>

      <Bento>
        {/* Review queue */}
        <Reveal delay={0.1} className="lg:col-span-5">
          <Panel className="h-full">
            <div className="flex items-center gap-2">
              <Gavel size={15} className="text-warn" />
              <SectionTitle hint={`${pending.length} pending`}>Human Review Queue</SectionTitle>
            </div>
            <div className="flex flex-col gap-2.5 mt-4">
              {pending.length === 0 ? (
                <EmptyState>No actions held for review.</EmptyState>
              ) : (
                pending.map((r, i) => (
                  <FeedRow key={r.id} i={i} className="rounded-xl border border-hairline bg-surface2/60 p-3.5 flex flex-col gap-2">
                    <div className="flex justify-between items-center">
                      <span className="text-[12px] font-semibold text-ink">{r.agent}</span>
                      <Badge tone="warn">Risk {(r.risk_score ?? 0).toFixed(2)}</Badge>
                    </div>
                    <span className="text-[10px] text-soft truncate">{r.prompt}</span>
                    <div className="flex gap-2 mt-1">
                      <button onClick={() => resolve(r.id, 'approved')} className="flex-1 flex items-center justify-center gap-1.5 text-[11px] font-semibold rounded-lg py-2 transition-opacity hover:opacity-90" style={{ color: 'var(--ok)', background: 'rgba(16,185,129,0.12)' }}>
                        <CheckCircle2 size={13} /> Approve
                      </button>
                      <button onClick={() => resolve(r.id, 'rejected')} className="flex-1 flex items-center justify-center gap-1.5 text-[11px] font-semibold rounded-lg py-2 transition-opacity hover:opacity-90" style={{ color: 'var(--bad)', background: 'rgba(244,63,94,0.12)' }}>
                        <XCircle size={13} /> Reject
                      </button>
                    </div>
                  </FeedRow>
                ))
              )}
            </div>
          </Panel>
        </Reveal>

        {/* Ledger stream */}
        <Reveal delay={0.15} className="lg:col-span-7">
          <Panel className="h-full">
            <SectionTitle hint="latest">Evidence Records</SectionTitle>
            <div className="grid sm:grid-cols-2 gap-2.5 mt-4 max-h-[34rem] overflow-y-auto scrollbar-slim pr-1">
              {ledger.length === 0 ? (
                <div className="sm:col-span-2"><EmptyState>No evidence recorded yet.</EmptyState></div>
              ) : (
                ledger.map((rec, i) => (
                  <FeedRow key={rec.id || i} i={i} className="rounded-xl border border-hairline bg-surface2/60 p-3 flex flex-col gap-1">
                    <div className="flex justify-between items-center">
                      <span className="text-[11px] font-semibold text-brand">{rec.event_type}</span>
                      <span className="text-[9px] text-soft font-mono">#{rec.seq}</span>
                    </div>
                    <span className="text-[9px] text-soft font-mono truncate">hash {rec.record_hash?.slice(0, 24)}…</span>
                  </FeedRow>
                ))
              )}
            </div>
          </Panel>
        </Reveal>
      </Bento>
    </div>
  );
}
