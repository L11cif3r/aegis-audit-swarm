import { useEffect, useState } from 'react';
import { Wallet, Cpu, Layers } from 'lucide-react';
import {
  BarChart, Bar, ResponsiveContainer, Tooltip, XAxis, Cell,
} from 'recharts';
import { api } from '../../lib/api';
import { PageHeader, Stat, Panel, SectionTitle, EmptyState, Bento } from '../../app/components/shell/primitives';
import Reveal from '../../app/components/shell/Reveal';

const PALETTE = ['var(--brand)', 'var(--ok)', 'var(--warn)', 'var(--bad)', '#a78bfa'];

export default function Component05CostBilling() {
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setStats(await api.stats());
      } catch {
        /* offline */
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, []);

  const totalCost = stats?.total_cost_usd || 0;
  const byModel: Record<string, any> = stats?.by_model || {};
  const models = Object.entries(byModel)
    .map(([name, m]: any) => ({ name, cost: +(m.cost || 0).toFixed(6), requests: m.requests, tokens: (m.input_tokens || 0) + (m.output_tokens || 0) }))
    .sort((a, b) => b.cost - a.cost);
  const totalTokens = stats ? (stats.total_input_tokens || 0) + (stats.total_output_tokens || 0) : 0;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        kicker="Cost & Billing"
        title="Spend, measured to the fraction of a cent."
        subtitle="Live token economics across every model the swarm routes to."
      />

      <Bento>
        <Reveal delay={0.05} className="lg:col-span-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-4 sm:gap-5 h-full">
            <Stat label="Total Spend" count={totalCost} prefix="$" decimals={4} icon={Wallet} tone="warn" sub="Live, all-time" />
            <Stat label="Tokens" count={totalTokens} icon={Cpu} tone="brand" sub="In + out" />
            <Stat label="Models Routed" count={models.length} icon={Layers} tone="ok" sub="Distinct models" />
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
