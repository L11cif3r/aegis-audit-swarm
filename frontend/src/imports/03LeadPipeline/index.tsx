import { useEffect, useState } from 'react';
import { Users, TrendingUp, Target } from 'lucide-react';
import { api } from '../../lib/api';
import { PageHeader, Stat, Panel, SectionTitle, Badge, EmptyState, Bento, FeedRow } from '../../app/components/shell/primitives';
import Reveal from '../../app/components/shell/Reveal';

export default function Component03LeadPipeline() {
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
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, []);

  const leadLogs = logs.filter((l) => /lead/i.test(l.agent || '') || /lead/i.test(l.model || ''));
  const totalLeads = leadLogs.length;
  const successful = leadLogs.filter((l) => l.status === 'success').length;
  const conversion = totalLeads ? (successful / totalLeads) * 100 : 0;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        kicker="Lead Pipeline"
        title="Prospects, discovered by your agents."
        subtitle="Live AI-driven prospect activity flowing through the gateway."
      />

      <Bento>
        <Reveal delay={0.05} className="lg:col-span-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-4 sm:gap-5 h-full">
            <Stat label="Lead Requests" count={totalLeads} icon={Users} tone="brand" />
            <Stat label="Conversions" count={successful} icon={Target} tone="warn" />
            <Stat label="Success Rate" count={conversion} suffix="%" decimals={1} icon={TrendingUp} tone="ok" />
          </div>
        </Reveal>

        <Reveal delay={0.1} className="lg:col-span-8">
          <Panel className="h-full">
            <SectionTitle hint="recent">Lead Activity</SectionTitle>
            <div className="grid sm:grid-cols-2 gap-2.5 mt-4">
              {leadLogs.length === 0 ? (
                <div className="sm:col-span-2"><EmptyState>No lead-agent traffic yet. Send a request with a “Lead” agent.</EmptyState></div>
              ) : (
                leadLogs.slice(0, 10).map((lead, i) => (
                  <FeedRow key={lead.id || i} i={i} className="rounded-xl border border-hairline bg-surface2/60 p-3 flex items-center justify-between gap-3">
                    <div className="flex flex-col gap-0.5 min-w-0">
                      <span className="text-[12px] font-semibold text-ink">{lead.agent}</span>
                      <span className="text-[10px] text-soft truncate">{lead.prompt}</span>
                    </div>
                    <Badge tone={lead.status === 'success' ? 'ok' : 'warn'}>{lead.status}</Badge>
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
