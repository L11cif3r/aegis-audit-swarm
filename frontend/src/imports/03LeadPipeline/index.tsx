import { useEffect, useState } from 'react';
import { Users, TrendingUp } from 'lucide-react';
import { motion } from 'motion/react';
import { api } from '../../lib/api';
import { PageHeader, Stat, Panel, SectionTitle, Badge, EmptyState } from '../../app/components/shell/primitives';
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
  const conversion = totalLeads ? ((successful / totalLeads) * 100).toFixed(1) : '0.0';

  return (
    <div className="flex flex-col gap-7">
      <PageHeader
        kicker="Lead Pipeline"
        title="Prospects, discovered by your agents."
        subtitle="Live AI-driven prospect activity flowing through the gateway."
      />

      <Reveal delay={0.05}>
        <div className="grid grid-cols-2 gap-3">
          <Stat label="Lead Requests" value={totalLeads} icon={Users} tone="brand" />
          <Stat label="Success Rate" value={`${conversion}%`} icon={TrendingUp} tone="ok" />
        </div>
      </Reveal>

      <Reveal delay={0.1}>
        <Panel>
          <SectionTitle hint="recent">Lead Activity</SectionTitle>
          <div className="flex flex-col gap-2 mt-3">
            {leadLogs.length === 0 ? (
              <EmptyState>No lead-agent traffic yet. Send a request with a “Lead” agent.</EmptyState>
            ) : (
              leadLogs.slice(0, 8).map((lead, i) => (
                <motion.div
                  key={lead.id || i}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="rounded-xl border border-hairline bg-surface2/60 p-3 flex items-center justify-between"
                >
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <span className="text-[12px] font-semibold text-ink">{lead.agent}</span>
                    <span className="text-[10px] text-soft truncate max-w-[200px]">{lead.prompt}</span>
                  </div>
                  <Badge tone={lead.status === 'success' ? 'ok' : 'warn'}>{lead.status}</Badge>
                </motion.div>
              ))
            )}
          </div>
        </Panel>
      </Reveal>
    </div>
  );
}
