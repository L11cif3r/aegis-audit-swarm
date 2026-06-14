import { useEffect, useState } from 'react';
import { Wallet, Cpu } from 'lucide-react';
import {
  BarChart, Bar, ResponsiveContainer, Tooltip, XAxis, Cell,
} from 'recharts';
import { api } from '../../lib/api';
import { PageHeader, Stat, Panel, SectionTitle, EmptyState } from '../../app/components/shell/primitives';
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
    <div className="flex flex-col gap-7">
      <PageHeader
        kicker="Cost & Billing"
        title="Spend, measured to the fraction of a cent."
        subtitle="Live token economics across every model the swarm routes to."
      />

      <Reveal delay={0.05}>
        <div className="grid grid-cols-2 gap-3">
          <Stat label="Total Spend" value={`$${totalCost.toFixed(4)}`} icon={Wallet} tone="warn" sub="Live, all-time" />
          <Stat label="Tokens" value={totalTokens.toLocaleString()} icon={Cpu} tone="brand" sub="In + out" />
        </div>
      </Reveal>

      {models.length > 0 && (
        <Reveal delay={0.1}>
          <Panel>
            <SectionTitle hint="by model">Cost Distribution</SectionTitle>
            <div className="h-40 mt-3 -mx-2">
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
            </div>
          </Panel>
        </Reveal>
      )}

      <Reveal delay={0.15}>
        <Panel>
          <SectionTitle hint="usage">Model Breakdown</SectionTitle>
          <div className="flex flex-col divide-y divide-[var(--hairline)] mt-2">
            {models.length === 0 ? (
              <EmptyState>No usage recorded yet.</EmptyState>
            ) : (
              models.map((m, i) => (
                <div key={m.name} className="py-3 flex justify-between items-center">
                  <div className="flex items-center gap-2.5">
                    <span className="size-2 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} />
                    <div>
                      <p className="text-[13px] font-semibold text-ink">{m.name}</p>
                      <p className="text-[10px] text-soft">{m.requests} requests · {m.tokens.toLocaleString()} tokens</p>
                    </div>
                  </div>
                  <span className="font-mono text-[13px] text-ink tabular-nums">${m.cost.toFixed(6)}</span>
                </div>
              ))
            )}
          </div>
        </Panel>
      </Reveal>
    </div>
  );
}
