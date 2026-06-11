import { useState, useEffect } from 'react';
import { Activity, Bot, DollarSign, Shield } from 'lucide-react';

function MobileMetricCard({ label, value, icon: Icon, color }: { label: string, value: string | number, icon: any, color: string }) {
  return (
    <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-3 flex flex-col gap-2 relative overflow-hidden w-full">
      <div className="flex justify-between items-start">
        <span className="text-[10px] text-[#64748b] font-bold uppercase tracking-wider">{label}</span>
        <Icon size={14} color={color} />
      </div>
      <span className="text-2xl font-bold text-[#e2e8f0] font-mono leading-none">{value}</span>
    </div>
  );
}

export default function Component01DashboardOverview() {
  const [logs, setLogs] = useState<any[]>([]);
  const [isLive, setIsLive] = useState(false);

  // Fetch live data from the FastAPI Backend
  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/audit/logs');
        if (res.ok) {
          const data = await res.json();
          setLogs(data);
          setIsLive(true);
        }
      } catch (err) {
        setIsLive(false);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, []);

  const totalRequests = logs.length;
  const blockedRequests = logs.filter(l => l.status === 'blocked').length;
  const totalCost = logs.reduce((acc, log) => acc + (parseFloat(log.cost.replace('$', '')) || 0), 0).toFixed(4);
  const activeAgents = totalRequests > 0 ? [...new Set(logs.map(l => l.agent))].length : 0;

  return (
    <div className="p-4 flex flex-col gap-5 w-full max-w-md mx-auto">
      
      {/* Gateway Status */}
      <div className="flex items-center justify-between bg-[#0d1420] p-3 rounded-lg border border-[#1e2d45]">
        <div className="flex flex-col">
          <span className="text-xs text-[#64748b] font-medium">Gateway Status</span>
          <span className="text-sm font-bold text-white">
            {isLive ? 'Connected to Swarm' : 'Waiting for Backend...'}
          </span>
        </div>
        <div className={`size-3 rounded-full ${isLive ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 gap-3">
        <MobileMetricCard label="Total Handled" value={totalRequests} icon={Activity} color="#3b82f6" />
        <MobileMetricCard label="Live Token Cost" value={`$${totalCost}`} icon={DollarSign} color="#10b981" />
        <MobileMetricCard label="Threats Blocked" value={blockedRequests} icon={Shield} color="#ef4444" />
        <MobileMetricCard label="Active Agents" value={activeAgents} icon={Bot} color="#8b5cf6" />
      </div>

      {/* Live Interception Stream */}
      <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-4 flex flex-col gap-3">
        <h2 className="text-xs font-bold text-[#e2e8f0] tracking-wide">Live Interception Stream</h2>
        <div className="flex flex-col gap-2">
          {logs.length === 0 ? (
            <p className="text-xs text-[#64748b] italic text-center">No traffic detected.</p>
          ) : (
            logs.slice(0, 5).map((log, i) => (
              <div key={i} className="bg-[#080c14] border border-[#1e2d45]/50 rounded-lg p-3 flex flex-col gap-2">
                <div className="flex justify-between items-center">
                  <span className="text-[11px] font-bold text-white">{log.agent}</span>
                  <span className={`text-[9px] font-black px-2 py-0.5 rounded ${
                    log.status === 'success' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
                  }`}>
                    {log.status.toUpperCase()}
                  </span>
                </div>
                <span className="text-[10px] text-[#64748b] truncate">Prompt: {log.prompt}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}