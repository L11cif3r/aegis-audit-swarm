import { Mic, PhoneCall, Activity, Clock } from 'lucide-react';

export default function Component04VoiceAgent() {
  return (
    <div className="p-4 flex flex-col gap-5 w-full max-w-md mx-auto">
      <div>
        <h1 className="text-lg font-bold text-white tracking-tight">Voice Sessions</h1>
        <p className="text-xs text-[#64748b] mt-0.5 leading-relaxed">Live bidirectional audio agent monitoring.</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-3 flex flex-col gap-2">
          <div className="flex justify-between items-start"><span className="text-[10px] text-[#64748b] font-bold uppercase tracking-wider">Active Calls</span><PhoneCall size={14} color="#10b981" /></div>
          <span className="text-2xl font-bold text-[#e2e8f0] font-mono leading-none">3</span>
        </div>
        <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-3 flex flex-col gap-2">
          <div className="flex justify-between items-start"><span className="text-[10px] text-[#64748b] font-bold uppercase tracking-wider">Avg Duration</span><Clock size={14} color="#8b5cf6" /></div>
          <span className="text-2xl font-bold text-[#e2e8f0] font-mono leading-none">4m 12s</span>
        </div>
      </div>

      <div className="bg-[#0d1420] border border-[#1e2d45] rounded-xl p-4 flex flex-col gap-3">
        <div className="flex justify-between items-center">
          <h2 className="text-xs font-bold text-[#e2e8f0] tracking-wide">Live Transcript: Session #8892</h2>
          <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
        </div>
        <div className="bg-[#080c14] border border-[#1e2d45]/50 rounded-lg p-3 flex flex-col gap-3 h-48 overflow-y-auto">
          <div className="flex gap-2">
            <Mic size={12} color="#64748b" className="mt-0.5 shrink-0" />
            <p className="text-[10px] text-[#64748b] leading-relaxed"><span className="font-bold text-[#e2e8f0]">User:</span> Hello, I need to check the compliance status of the latest deployment.</p>
          </div>
          <div className="flex gap-2">
            <Activity size={12} color="#3b82f6" className="mt-0.5 shrink-0" />
            <p className="text-[10px] text-[#64748b] leading-relaxed"><span className="font-bold text-[#3b82f6]">Agent:</span> I can help with that. Looking at the Audit Swarm logs, the deployment passed 23 security checks and intercepted 1 prompt injection attempt. Would you like the full report?</p>
          </div>
        </div>
      </div>
    </div>
  );
}