import { useEffect, useState } from 'react';
import { PhoneCall, Activity, Mic, Bot } from 'lucide-react';
import { motion } from 'motion/react';
import { api } from '../../lib/api';
import { PageHeader, Stat, Panel, SectionTitle, EmptyState } from '../../app/components/shell/primitives';
import Reveal from '../../app/components/shell/Reveal';

export default function Component04VoiceAgent() {
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

  const voiceLogs = logs.filter((l) => /voice/i.test(l.agent || '') || /gemini/i.test(l.model || ''));
  const sessions = voiceLogs.length;
  const successful = voiceLogs.filter((l) => l.status === 'success').length;

  return (
    <div className="flex flex-col gap-7">
      <PageHeader
        kicker="Voice Sessions"
        title="Conversations, monitored as they happen."
        subtitle="Live audio agent traffic, transcribed and audited through the gateway."
      />

      <Reveal delay={0.05}>
        <div className="grid grid-cols-2 gap-3">
          <Stat label="Sessions" value={sessions} icon={PhoneCall} tone="ok" />
          <Stat label="Completed" value={successful} icon={Activity} tone="brand" />
        </div>
      </Reveal>

      <Reveal delay={0.1}>
        <Panel>
          <div className="flex items-center justify-between">
            <SectionTitle>Recent Transcripts</SectionTitle>
            <span className="size-1.5 rounded-full bg-ok animate-pulse" />
          </div>
          <div className="flex flex-col gap-3 mt-3 max-h-[28rem] overflow-y-auto scrollbar-slim">
            {voiceLogs.length === 0 ? (
              <EmptyState>No voice sessions yet.</EmptyState>
            ) : (
              voiceLogs.slice(0, 8).map((log, i) => (
                <motion.div
                  key={log.id || i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="rounded-xl border border-hairline bg-surface2/60 p-3 flex flex-col gap-2"
                >
                  <div className="flex gap-2">
                    <Mic size={12} className="mt-0.5 shrink-0 text-soft" />
                    <p className="text-[11px] text-soft leading-relaxed"><span className="font-semibold text-ink">User:</span> {log.prompt}</p>
                  </div>
                  <div className="flex gap-2">
                    <Bot size={12} className="mt-0.5 shrink-0 text-brand" />
                    <p className="text-[11px] text-soft leading-relaxed line-clamp-3"><span className="font-semibold text-brand">Agent:</span> {log.response}</p>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        </Panel>
      </Reveal>
    </div>
  );
}
