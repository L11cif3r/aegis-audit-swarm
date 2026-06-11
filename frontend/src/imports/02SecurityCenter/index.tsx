import { useState, useEffect } from 'react';

function MobileThreatCard({ title, value, subtext, color }: { title: string, value: string | number, subtext: string, color: string }) {
  return (
    <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-4 flex flex-col gap-1 relative overflow-hidden w-full">
      <div className="absolute left-0 top-0 bottom-0 w-1" style={{ backgroundColor: color }} />
      <span className="text-[10px] font-medium text-[#64748b] uppercase tracking-wider">{title}</span>
      <span className="text-3xl font-bold text-[#e2e8f0] font-mono leading-none my-1">{value}</span>
      <span className="text-[10px] text-[#64748b] font-medium">{subtext}</span>
    </div>
  );
}

export default function Component02SecurityCenter() {
  const [logs, setLogs] = useState<any[]>([]);

  // Fetch live data from your FastAPI Gateway
  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/audit/logs');
        if (res.ok) {
          const data = await res.json();
          setLogs(data);
        }
      } catch (err) {
        console.error("Gateway offline");
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 2000); // Poll every 2 seconds
    return () => clearInterval(interval);
  }, []);

  // Filter logs to isolate only the blocked payloads
  const blockedLogs = logs.filter(l => l.status === 'blocked');
  const totalBlocked = blockedLogs.length;
  
  // Basic packet inspection simulation to classify threats based on your mock backend logic
  const injections = blockedLogs.filter(l => l.prompt?.toLowerCase().includes('ignore')).length;
  const secrets = blockedLogs.filter(l => l.prompt?.includes('sk-')).length;

  return (
    <div className="p-4 flex flex-col gap-5 w-full max-w-md mx-auto">
      
      <div>
        <h1 className="text-lg font-bold text-white tracking-tight">Threat Analytics</h1>
        <p className="text-xs text-[#64748b] mt-0.5 leading-relaxed">Inline inspection monitoring and real-time mitigation.</p>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 gap-3">
        <MobileThreatCard title="Blocked Today" value={totalBlocked} subtext="Total mitigated" color="#ef4444" />
        <MobileThreatCard title="Injections" value={injections} subtext="Jailbreak patterns" color="#f59e0b" />
        <MobileThreatCard title="Secrets Redacted" value={secrets} subtext="API keys hidden" color="#8b5cf6" />
        <MobileThreatCard title="PII Cleaned" value="0" subtext="SSN / Identifiers" color="#06b6d4" />
      </div>

      {/* Security Policies */}
      <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-4 flex flex-col gap-3">
        <div>
          <h2 className="text-xs font-bold text-[#e2e8f0] tracking-wide">Security Filter Policies</h2>
          <p className="text-[10px] text-[#64748b]">Active network proxy rules.</p>
        </div>
        <div className="divide-y divide-[#1e2d45]/40 text-xs">
          <div className="py-2.5 flex justify-between items-center">
            <div>
              <p className="font-semibold text-white">Prompt Injection</p>
              <p className="text-[10px] text-[#64748b]">Jailbreaks & DAN</p>
            </div>
            <span className="bg-amber-500/10 border border-amber-500/20 text-amber-500 text-[9px] font-bold px-2 py-0.5 rounded-md">BLOCK</span>
          </div>
          <div className="py-2.5 flex justify-between items-center">
            <div>
              <p className="font-semibold text-white">API Keys & Secrets</p>
              <p className="text-[10px] text-[#64748b]">sk-..., bearer hashes</p>
            </div>
            <span className="bg-red-500/10 border border-red-500/20 text-red-500 text-[9px] font-bold px-2 py-0.5 rounded-md">REDACT</span>
          </div>
        </div>
      </div>

      {/* Live Threat Feed */}
      <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-4 flex flex-col gap-3">
        <div className="flex justify-between items-center">
          <h2 className="text-xs font-bold text-[#e2e8f0]">Live Threat Feed</h2>
          <span className="size-1.5 rounded-full bg-red-500 animate-ping" />
        </div>
        <div className="flex flex-col gap-2">
          {blockedLogs.length === 0 ? (
            <p className="text-xs text-[#64748b] italic py-4 text-center">No active threats detected.</p>
          ) : (
            blockedLogs.slice(0, 5).map((log, i) => (
              <div key={i} className="bg-[#080c14] border border-[#1e2d45]/50 rounded-lg p-3 flex flex-col gap-2">
                <div className="flex justify-between items-center">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[11px] font-bold text-white">{log.agent} Breach</span>
                    <span className="text-[9px] text-[#64748b] font-mono">Model: {log.model}</span>
                  </div>
                  <span className="bg-red-500/15 text-red-400 border border-red-500/30 text-[9px] font-black px-2 py-0.5 rounded">BLOCKED</span>
                </div>
                <span className="text-[10px] text-[#ef4444] truncate">Payload: {log.prompt}</span>
              </div>
            ))
          )}
        </div>
      </div>

    </div>
  );
}