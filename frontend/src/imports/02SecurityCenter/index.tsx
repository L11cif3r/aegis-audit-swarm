import { useEffect, useState } from 'react';
import { ShieldAlert, KeyRound, ScanLine, Fingerprint } from 'lucide-react';
import { api } from '../../lib/api';
import { PageHeader, Stat, Panel, SectionTitle, Badge, EmptyState, Bento, FeedRow } from '../../app/components/shell/primitives';
import Reveal from '../../app/components/shell/Reveal';

export default function Component02SecurityCenter() {
  const [threats, setThreats] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [t, s] = await Promise.all([api.threats(), api.stats()]);
        setThreats(t);
        setStats(s);
      } catch {
        /* offline */
      }
    };
    fetchAll();
    const interval = setInterval(fetchAll, 2000);
    return () => clearInterval(interval);
  }, []);

  const sec = stats?.security;
  const totalBlocked = sec?.blocked ?? threats.length;
  const injections = sec?.injections ?? threats.filter((l) => /injection/i.test(l.threat_type || '')).length;
  const secrets = sec?.secrets ?? threats.filter((l) => /secret/i.test(l.threat_type || '')).length;
  const held = sec?.held ?? stats?.total_held ?? 0;
  const pii = threats.filter((l) => /pii/i.test(l.threat_type || '')).length;

  const policies = [
    { name: 'Prompt Injection', desc: 'Jailbreaks, DAN, role-play', action: 'BLOCK', tone: 'warn' as const },
    { name: 'API Keys & Secrets', desc: 'sk-…, AKIA, bearer tokens', action: 'REDACT', tone: 'bad' as const },
    { name: 'PII Exposure', desc: 'SSN, cards, emails', action: 'REDACT', tone: 'brand' as const },
  ];

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        kicker="Security Center"
        title="Threats, intercepted before they land."
        subtitle="Inline inspection, redaction, and real-time mitigation at the gateway edge."
      />

      <Reveal delay={0.05}>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 sm:gap-5">
          <Stat label="Blocked" count={totalBlocked} icon={ShieldAlert} tone="bad" sub="Total mitigated" />
          <Stat label="Held" count={held} icon={ShieldAlert} tone="warn" sub="Awaiting review" />
          <Stat label="Injections" count={injections} icon={ScanLine} tone="warn" sub="Jailbreak patterns" />
          <Stat label="Secrets" count={secrets} icon={KeyRound} tone="brand" sub="Keys redacted" />
          <Stat label="PII Cleaned" count={pii} icon={Fingerprint} tone="ok" sub="Identifiers" />
        </div>
      </Reveal>

      <Bento>
        <Reveal delay={0.1} className="lg:col-span-5">
          <Panel className="h-full">
            <SectionTitle hint="active rules">Filter Policies</SectionTitle>
            <div className="flex flex-col divide-y divide-[var(--hairline)] mt-2">
              {policies.map((p) => (
                <div key={p.name} className="py-3.5 flex justify-between items-center">
                  <div>
                    <p className="text-[13px] font-semibold text-ink">{p.name}</p>
                    <p className="text-[10px] text-soft">{p.desc}</p>
                  </div>
                  <Badge tone={p.tone}>{p.action}</Badge>
                </div>
              ))}
            </div>
          </Panel>
        </Reveal>

        <Reveal delay={0.15} className="lg:col-span-7">
          <Panel className="h-full">
            <div className="flex items-center justify-between">
              <SectionTitle>Live Threat Feed</SectionTitle>
              <span className="size-1.5 rounded-full bg-bad animate-ping" />
            </div>
            <div className="grid sm:grid-cols-2 gap-2.5 mt-4">
              {threats.length === 0 ? (
                <div className="sm:col-span-2"><EmptyState>No active threats detected.</EmptyState></div>
              ) : (
                threats.slice(0, 8).map((log, i) => (
                  <FeedRow
                    key={log.id || i}
                    i={i}
                    className="rounded-xl border p-3 flex flex-col gap-1.5"
                    style={{ borderColor: 'rgba(244,63,94,0.25)', background: 'rgba(244,63,94,0.06)' }}
                  >
                    <div className="flex justify-between items-center">
                      <div className="flex flex-col">
                        <span className="text-[12px] font-semibold text-ink">{log.agent}</span>
                        <span className="text-[9px] text-soft font-mono">{log.threat_type || 'THREAT'} · {log.model}</span>
                      </div>
                      <Badge tone="bad">Blocked</Badge>
                    </div>
                    <span className="text-[11px] truncate" style={{ color: 'var(--bad)' }}>{log.prompt}</span>
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
