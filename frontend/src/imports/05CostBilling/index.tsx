import { useEffect, useState } from 'react';
import { Wallet, Cpu, Layers, Cloud } from 'lucide-react';
import {
  BarChart, Bar, ResponsiveContainer, Tooltip, XAxis, Cell,
} from 'recharts';
import { api } from '../../lib/api';
import { PageHeader, Stat, Panel, SectionTitle, EmptyState, Bento } from '../../app/components/shell/primitives';
import Reveal from '../../app/components/shell/Reveal';

const PALETTE = ['var(--brand)', 'var(--ok)', 'var(--warn)', 'var(--bad)', '#a78bfa'];

function BudgetMeter({ label, window: w }: { label: string; window: any }) {
  const spent = w?.spent_usd ?? 0;
  const limit = w?.limit_usd ?? null;
  const frac = limit ? Math.min(spent / limit, 1) : 0;
  const pct = Math.round(frac * 100);
  const tone = frac >= 1 ? 'var(--bad)' : frac >= 0.8 ? 'var(--warn)' : 'var(--ok)';
  return (
    <div className="rounded-xl border border-hairline bg-surface2/60 p-4">
      <div className="flex justify-between items-baseline gap-2">
        <span className="text-[12px] font-semibold text-ink">{label}</span>
        <span className="font-mono text-[12px] text-ink tabular-nums">
          ${spent.toFixed(4)}{limit != null ? ` / $${Number(limit).toFixed(2)}` : ''}
        </span>
      </div>
      <div className="mt-3 h-2 rounded-full bg-hairline overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${limit ? pct : 0}%`, background: tone }} />
      </div>
      <p className="text-[10px] text-soft mt-2">{limit != null ? `${pct}% of cap` : 'No cap set'}</p>
    </div>
  );
}
const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google',
};

export default function Component05CostBilling() {
  const [stats, setStats] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [dayLimit, setDayLimit] = useState('');
  const [monthLimit, setMonthLimit] = useState('');
  const [budgetTouched, setBudgetTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [budgetMsg, setBudgetMsg] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [s, sum] = await Promise.all([api.stats(), api.costSummary()]);
        setStats(s);
        setSummary(sum);
        if (!budgetTouched) {
          setDayLimit(sum?.day?.limit_usd != null ? String(sum.day.limit_usd) : '');
          setMonthLimit(sum?.month?.limit_usd != null ? String(sum.month.limit_usd) : '');
        }
      } catch {
        /* offline */
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, [budgetTouched]);

  const saveBudget = async () => {
    setSaving(true);
    setBudgetMsg(null);
    try {
      await api.setBudget({
        daily_limit_usd: dayLimit ? Number(dayLimit) : null,
        monthly_limit_usd: monthLimit ? Number(monthLimit) : null,
      });
      setBudgetTouched(false);
      setBudgetMsg('Budget saved.');
    } catch (e: any) {
      const msg = String(e?.message || '');
      setBudgetMsg(/403|role|permission/i.test(msg) ? 'Operator role required to set budgets.' : 'Could not save budget.');
    } finally {
      setSaving(false);
    }
  };

  const totalCost = stats?.total_cost_usd || 0;
  const byModel: Record<string, any> = stats?.by_model || {};
  const byProvider: Record<string, any> = stats?.by_provider || {};
  const models = Object.entries(byModel)
    .map(([name, m]: any) => ({ name, cost: +(m.cost || 0).toFixed(6), requests: m.requests, tokens: (m.input_tokens || 0) + (m.output_tokens || 0) }))
    .sort((a, b) => b.cost - a.cost);
  const providers = Object.entries(byProvider)
    .map(([name, p]: any) => ({
      name: PROVIDER_LABELS[name] || name,
      id: name,
      cost: +(p.cost || 0).toFixed(6),
      requests: p.requests,
      tokens: (p.input_tokens || 0) + (p.output_tokens || 0),
    }))
    .sort((a, b) => b.cost - a.cost);
  const totalTokens = stats ? (stats.total_input_tokens || 0) + (stats.total_output_tokens || 0) : 0;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        kicker="Cost & Billing"
        title="Spend, measured to the fraction of a cent."
        subtitle="Live token economics across every model and provider the gateway routes to."
      />

      <Bento>
        <Reveal delay={0.05} className="lg:col-span-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-4 sm:gap-5 h-full">
            <Stat label="Total Spend" count={totalCost} prefix="$" decimals={4} icon={Wallet} tone="warn" sub="Live, all-time" />
            <Stat label="Tokens" count={totalTokens} icon={Cpu} tone="brand" sub="In + out" />
            <Stat label="Providers" count={providers.length} icon={Cloud} tone="ok" sub="With usage" />
          </div>
        </Reveal>

        <Reveal delay={0.1} className="lg:col-span-8">
          <Panel className="h-full">
            <SectionTitle hint="by model">Cost Distribution</SectionTitle>
            <div className="h-64 mt-4 -mx-2">
              {models.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={models} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 9, fill: 'var(--soft)' }} tickFormatter={(v) => v.split('-')[0]} axisLine={false} tickLine={false} />
                    <Tooltip
                      cursor={{ fill: 'var(--hairline)' }}
                      contentStyle={{ background: 'var(--surface)', border: '1px solid var(--hairline)', borderRadius: 12, fontSize: 11, color: 'var(--ink)' }}
                      formatter={(v: any) => [`$${v}`, 'cost']}
                    />
                    <Bar dataKey="cost" radius={[6, 6, 0, 0]}>
                      {models.map((_, i) => (
                        <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState>No usage recorded yet.</EmptyState>
              )}
            </div>
          </Panel>
        </Reveal>
      </Bento>

      <Reveal delay={0.11}>
        <Panel>
          <SectionTitle hint="spend caps">Budgets</SectionTitle>
          <div className="grid md:grid-cols-2 gap-4 mt-4">
            <BudgetMeter label="Today" window={summary?.day} />
            <BudgetMeter label="This month" window={summary?.month} />
          </div>
          <div className="grid sm:grid-cols-2 gap-3 mt-5">
            <label className="flex flex-col gap-1.5">
              <span className="text-[11px] text-soft">Daily limit (USD)</span>
              <input
                type="number" min="0" step="0.01" inputMode="decimal"
                value={dayLimit}
                onChange={(e) => { setDayLimit(e.target.value); setBudgetTouched(true); }}
                placeholder="No cap"
                className="rounded-xl border border-hairline bg-surface2/60 px-3 py-2 text-[13px] text-ink font-mono tabular-nums outline-none focus:border-brand"
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[11px] text-soft">Monthly limit (USD)</span>
              <input
                type="number" min="0" step="0.01" inputMode="decimal"
                value={monthLimit}
                onChange={(e) => { setMonthLimit(e.target.value); setBudgetTouched(true); }}
                placeholder="No cap"
                className="rounded-xl border border-hairline bg-surface2/60 px-3 py-2 text-[13px] text-ink font-mono tabular-nums outline-none focus:border-brand"
              />
            </label>
          </div>
          <div className="flex items-center gap-3 mt-4">
            <button
              onClick={saveBudget}
              disabled={saving || !budgetTouched}
              className="rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-white disabled:opacity-40 transition-opacity"
            >
              {saving ? 'Saving…' : 'Save budget'}
            </button>
            {budgetMsg && <span className="text-[11px] text-soft">{budgetMsg}</span>}
            <span className="text-[11px] text-soft ml-auto">Requests are blocked once a cap is reached.</span>
          </div>
        </Panel>
      </Reveal>

      <Reveal delay={0.12}>
        <Panel>
          <SectionTitle hint="by provider">Provider Spend</SectionTitle>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2.5 mt-4">
            {providers.length === 0 ? (
              <div className="sm:col-span-2 lg:col-span-3"><EmptyState>No provider usage yet.</EmptyState></div>
            ) : (
              providers.map((p, i) => (
                <div key={p.id} className="rounded-xl border border-hairline bg-surface2/60 p-3.5 flex justify-between items-center gap-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="size-2 shrink-0 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} />
                    <div className="min-w-0">
                      <p className="text-[13px] font-semibold text-ink truncate">{p.name}</p>
                      <p className="text-[10px] text-soft">{p.requests} req · {p.tokens.toLocaleString()} tok</p>
                    </div>
                  </div>
                  <span className="font-mono text-[12px] text-ink tabular-nums shrink-0">${p.cost.toFixed(6)}</span>
                </div>
              ))
            )}
          </div>
        </Panel>
      </Reveal>

      <Reveal delay={0.15}>
        <Panel>
          <SectionTitle hint="usage">Model Breakdown</SectionTitle>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2.5 mt-4">
            {models.length === 0 ? (
              <div className="sm:col-span-2 lg:col-span-3"><EmptyState>No usage recorded yet.</EmptyState></div>
            ) : (
              models.map((m, i) => (
                <div key={m.name} className="rounded-xl border border-hairline bg-surface2/60 p-3.5 flex justify-between items-center gap-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="size-2 shrink-0 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} />
                    <div className="min-w-0">
                      <p className="text-[13px] font-semibold text-ink truncate">{m.name}</p>
                      <p className="text-[10px] text-soft">{m.requests} req · {m.tokens.toLocaleString()} tok</p>
                    </div>
                  </div>
                  <span className="font-mono text-[12px] text-ink tabular-nums shrink-0">${m.cost.toFixed(6)}</span>
                </div>
              ))
            )}
          </div>
        </Panel>
      </Reveal>
    </div>
  );
}
