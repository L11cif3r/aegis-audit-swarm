import { useEffect, useState } from 'react';
import { PhoneCall, Activity, Mic, Bot } from 'lucide-react';
import { api } from '../../lib/api';
import { PageHeader, Stat, Panel, SectionTitle, EmptyState, Bento, FeedRow } from '../../app/components/shell/primitives';
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
  const completion = sessions ? (successful / sessions) * 100 : 0;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        kicker="Voice Sessions"
        title="Conversations, monitored as they happen."
        subtitle="Live audio agent traffic, transcribed and audited through the gateway."
      />

      <Bento>
        <Reveal delay={0.05} className="lg:col-span-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-4 sm:gap-5 h-full">
            <Stat label="Sessions" count={sessions} icon={PhoneCall} tone="ok" />
            <Stat label="Completed" count={successful} icon={Activity} tone="brand" />
            <Stat label="Completion" count={completion} suffix="%" decimals={0} icon={Mic} tone="warn" />
          </div>
        </Reveal>

        <Reveal delay={0.1} className="lg:col-span-8">
          <Panel className="h-full">
            <div className="flex items-center justify-between">
              <SectionTitle>Recent Transcripts</SectionTitle>
              <span className="size-1.5 rounded-full bg-ok animate-pulse" />
            </div>
            <div className="flex flex-col gap-3 mt-4 max-h-[32rem] overflow-y-auto scrollbar-slim pr-1">
              {voiceLogs.length === 0 ? (
                <EmptyState>No voice sessions yet.</EmptyState>
              ) : (
                voiceLogs.slice(0, 10).map((log, i) => (
                  <FeedRow key={log.id || i} i={i} className="rounded-xl border border-hairline bg-surface2/60 p-3.5 flex flex-col gap-2">
                    <div className="flex gap-2">
                      <Mic size={12} className="mt-0.5 shrink-0 text-soft" />
                      <p className="text-[11px] text-soft leading-relaxed"><span className="font-semibold text-ink">User:</span> {log.prompt}</p>
                    </div>
                    <div className="flex gap-2">
                      <Bot size={12} className="mt-0.5 shrink-0 text-brand" />
                      <p className="text-[11px] text-soft leading-relaxed line-clamp-3"><span className="font-semibold text-brand">Agent:</span> {log.response}</p>
                    </div>
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
