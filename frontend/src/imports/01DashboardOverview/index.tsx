import { useState, useEffect } from 'react';
import { Activity, Bot, DollarSign, ShieldAlert } from 'lucide-react';
import {
  AreaChart, Area, ResponsiveContainer, Tooltip, XAxis,
} from 'recharts';
import { api } from '../../lib/api';
import { PageHeader, Stat, Panel, SectionTitle, Badge, EmptyState, Bento, FeedRow } from '../../app/components/shell/primitives';
import Reveal from '../../app/components/shell/Reveal';

function statusTone(status: string) {
  if (status === 'success') return 'ok';
  if (status === 'held') return 'warn';
  return 'bad';
}

export default function Component01DashboardOverview() {
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLogs(await api.logs());
      } catch {
        /* offline */
      }
    };
    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, []);

  const totalRequests = logs.length;
  const blockedRequests = logs.filter((l) => l.status === 'blocked' || l.status === 'held').length;
  const totalCost = logs.reduce((acc, log) => acc + (parseFloat((log.cost || '$0').replace('$', '')) || 0), 0);
  const activeAgents = totalRequests > 0 ? [...new Set(logs.map((l) => l.agent))].length : 0;

  const series = [...logs]
    .reverse()
    .reduce<{ i: number; cost: number }[]>((acc, log) => {
      const prev = acc.length ? acc[acc.length - 1].cost : 0;
      acc.push({ i: acc.length, cost: +(prev + (parseFloat((log.cost || '$0').replace('$', '')) || 0)).toFixed(6) });
      return acc;
    }, []);

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        kicker="Control Plane"
        title="Every agent action, refereed in real time."
        subtitle="Live interception, security screening, and cost telemetry across your AI swarm."
      />

      <Reveal delay={0.05}>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
          <Stat label="Total Handled" count={totalRequests} icon={Activity} tone="brand" />
          <Stat label="Live Cost" count={totalCost} prefix="$" decimals={4} icon={DollarSign} tone="ok" />
          <Stat label="Threats Stopped" count={blockedRequests} icon={ShieldAlert} tone="bad" />
          <Stat label="Active Agents" count={activeAgents} icon={Bot} tone="warn" />
        </div>
      </Reveal>

      <Bento>
        <Reveal delay={0.1} className="lg:col-span-7">
          <Panel className="h-full">
            <SectionTitle hint="cumulative">Spend Trajectory</SectionTitle>
            <div className="h-64 mt-4 -mx-2">
              {series.length > 1 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={series}>
                    <defs>
                      <linearGradient id="costFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--brand)" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="var(--brand)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="i" hide />
                    <Tooltip
                      contentStyle={{ background: 'var(--surface)', border: '1px solid var(--hairline)', borderRadius: 12, fontSize: 11, color: 'var(--ink)' }}
                      labelStyle={{ display: 'none' }}
                      formatter={(v: any) => [`$${v}`, 'cost']}
                    />
                    <Area type="monotone" dataKey="cost" stroke="var(--brand)" strokeWidth={2.5} fill="url(#costFill)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState>Send traffic to chart cumulative spend.</EmptyState>
              )}
            </div>
          </Panel>
        </Reveal>

        <Reveal delay={0.15} className="lg:col-span-5">
          <Panel className="h-full">
            <SectionTitle hint="last 8">Live Interception Stream</SectionTitle>
            <div className="flex flex-col gap-2 mt-4 max-h-72 overflow-y-auto scrollbar-slim pr-1">
              {logs.length === 0 ? (
                <EmptyState>No traffic detected yet.</EmptyState>
              ) : (
                logs.slice(0, 8).map((log, i) => (
                  <FeedRow key={log.id || i} i={i} className="rounded-xl border border-hairline bg-surface2/60 p-3 flex flex-col gap-1.5">
                    <div className="flex justify-between items-center">
                      <span className="text-[12px] font-semibold text-ink">{log.agent}</span>
                      <Badge tone={statusTone(log.status) as any}>{(log.status || 'unknown')}</Badge>
                    </div>
                    <span className="text-[11px] text-soft truncate">{log.prompt}</span>
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
