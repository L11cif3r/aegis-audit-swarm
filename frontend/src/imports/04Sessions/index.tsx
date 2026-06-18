import { useEffect, useMemo, useState } from 'react';
import { MessagesSquare, CheckCircle2, ShieldAlert, Activity, Bot, Search, Sparkles, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import { PageHeader, Stat, Panel, SectionTitle, EmptyState, Bento, FeedRow } from '../../app/components/shell/primitives';
import Reveal from '../../app/components/shell/Reveal';

type Session = {
  id?: string; timestamp?: string; agent?: string; model?: string;
  prompt?: string; response?: string; status?: string;
  threat_type?: string | null; risk_score?: number | null;
  cost?: string; cost_usd?: number | null;
};

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'success', label: 'Success' },
  { id: 'blocked', label: 'Blocked' },
  { id: 'held', label: 'Held' },
  { id: 'error', label: 'Error' },
];

const STATUS_TONE: Record<string, string> = {
  success: 'text-ok bg-ok/10',
  blocked: 'text-bad bg-bad/10',
  held: 'text-warn bg-warn/10',
  error: 'text-bad bg-bad/10',
};

function timeAgo(ts?: string): string {
  if (!ts) return '';
  const d = new Date(ts).getTime();
  if (Number.isNaN(d)) return '';
  const s = Math.max(0, Math.floor((Date.now() - d) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

type Explain = { loading: boolean; text?: string; error?: string };

export default function Component04Sessions() {
  const [logs, setLogs] = useState<Session[]>([]);
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const [explained, setExplained] = useState<Record<string, Explain>>({});

  const explainSession = async (id?: string) => {
    if (!id) return;
    setExplained((m) => ({ ...m, [id]: { loading: true, text: undefined, error: undefined } }));
    try {
      const res = await api.analystExplain(id);
      setExplained((m) => ({ ...m, [id]: { loading: false, text: res.explanation } }));
    } catch (e: any) {
      setExplained((m) => ({ ...m, [id]: { loading: false, error: e?.message || 'Unavailable' } }));
    }
  };

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLogs(await api.logs(200));
      } catch {
        /* offline */
      }
    };
    fetchLogs();
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, []);

  const total = logs.length;
  const successful = logs.filter((l) => l.status === 'success').length;
  const intercepted = logs.filter((l) => l.status === 'blocked' || l.status === 'held').length;
  const avgRisk = useMemo(() => {
    const scored = logs.filter((l) => typeof l.risk_score === 'number');
    if (!scored.length) return 0;
    return (scored.reduce((a, l) => a + (l.risk_score || 0), 0) / scored.length) * 100;
  }, [logs]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return logs
      .filter((l) => (filter === 'all' ? true : l.status === filter))
      .filter((l) => !q
        || (l.agent || '').toLowerCase().includes(q)
        || (l.model || '').toLowerCase().includes(q)
        || (l.prompt || '').toLowerCase().includes(q))
      .slice(0, 40);
  }, [logs, filter, query]);

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        kicker="Sessions"
        title="Every agent session, refereed in real time."
        subtitle="A live stream of all requests through the gateway — prompts, responses, risk and cost, across every agent and model."
      />

      <Bento>
        <Reveal delay={0.05} className="lg:col-span-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-4 sm:gap-5 h-full">
            <Stat label="Total Sessions" count={total} icon={MessagesSquare} tone="brand" sub="Last 200" />
            <Stat label="Successful" count={successful} icon={CheckCircle2} tone="ok" />
            <Stat label="Intercepted" count={intercepted} icon={ShieldAlert} tone="bad" sub="Blocked + held" />
            <Stat label="Avg Risk" count={avgRisk} suffix="%" decimals={0} icon={Activity} tone="warn" />
          </div>
        </Reveal>

        <Reveal delay={0.1} className="lg:col-span-8">
          <Panel className="h-full">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <SectionTitle>Live Sessions</SectionTitle>
              <span className="size-1.5 rounded-full bg-ok animate-pulse" />
            </div>

            <div className="flex flex-wrap items-center gap-2 mt-4">
              <div className="flex flex-wrap gap-1.5">
                {FILTERS.map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setFilter(f.id)}
                    data-cursor="hover"
                    className={`rounded-lg px-3 py-1.5 text-[11px] font-medium transition-colors ${
                      filter === f.id ? 'bg-brand text-white' : 'border border-hairline text-soft hover:text-ink'
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
              <div className="relative ml-auto">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-soft pointer-events-none" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search agent, model, prompt…"
                  className="rounded-lg border border-hairline bg-surface2/60 pl-8 pr-3 py-1.5 text-[12px] text-ink outline-none focus:border-brand w-52"
                />
              </div>
            </div>

            <div className="flex flex-col gap-3 mt-4 max-h-[34rem] overflow-y-auto scrollbar-slim pr-1">
              {visible.length === 0 ? (
                <EmptyState>No sessions match.</EmptyState>
              ) : (
                visible.map((log, i) => (
                  <FeedRow key={log.id || i} i={i} className="rounded-xl border border-hairline bg-surface2/60 p-3.5 flex flex-col gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${STATUS_TONE[log.status || ''] || 'text-soft bg-hairline'}`}>
                        {log.status || 'unknown'}
                      </span>
                      <span className="text-[11px] font-semibold text-ink">{log.agent || 'agent'}</span>
                      <span className="text-[10px] text-soft">· {log.model}</span>
                      {log.threat_type && (
                        <span className="text-[10px] text-bad font-medium">· {log.threat_type}</span>
                      )}
                      <span className="ml-auto text-[10px] text-soft tabular-nums">{timeAgo(log.timestamp)}</span>
                    </div>
                    <p className="text-[11px] text-soft leading-relaxed line-clamp-2">
                      <span className="font-semibold text-ink">Prompt:</span> {log.prompt}
                    </p>
                    <div className="flex gap-2">
                      <Bot size={12} className="mt-0.5 shrink-0 text-brand" />
                      <p className="text-[11px] text-soft leading-relaxed line-clamp-2">{log.response}</p>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-soft tabular-nums">
                      {typeof log.risk_score === 'number' && <span>risk {(log.risk_score * 100).toFixed(0)}%</span>}
                      {log.cost && <span>· {log.cost}</span>}
                      {log.id && (
                        <button
                          onClick={() => explainSession(log.id)}
                          data-cursor="hover"
                          disabled={explained[log.id]?.loading}
                          className="ml-auto inline-flex items-center gap-1 rounded-md border border-hairline px-2 py-0.5 text-[10px] font-medium text-brand hover:bg-brandsoft transition-colors disabled:opacity-50"
                        >
                          {explained[log.id]?.loading
                            ? <Loader2 size={11} className="animate-spin" />
                            : <Sparkles size={11} />}
                          Explain
                        </button>
                      )}
                    </div>
                    {log.id && explained[log.id] && !explained[log.id].loading && (
                      <div className={`rounded-lg border border-hairline p-2.5 text-[11px] leading-relaxed ${explained[log.id].error ? 'text-bad' : 'text-soft bg-brandsoft/40'}`}>
                        {explained[log.id].error
                          ? `AI analyst unavailable: ${explained[log.id].error}`
                          : explained[log.id].text}
                      </div>
                    )}
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
