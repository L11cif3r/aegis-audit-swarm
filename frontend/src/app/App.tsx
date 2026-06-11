import { useState } from 'react';
import Component01DashboardOverview from '../imports/01DashboardOverview';
import Component02SecurityCenter from '../imports/02SecurityCenter';
import Component03LeadPipeline from '../imports/03LeadPipeline';
import Component04VoiceAgent from '../imports/04VoiceAgent';
import Component05CostBilling from '../imports/05CostBilling';

export default function App() {
  const [currentView, setCurrentView] = useState('dashboard');

  const renderView = () => {
    switch (currentView) {
      case 'dashboard': return <Component01DashboardOverview />;
      case 'security': return <Component02SecurityCenter />;
      case 'leads': return <Component03LeadPipeline />;
      case 'voice': return <Component04VoiceAgent />;
      case 'billing': return <Component05CostBilling />;
      default: return <Component01DashboardOverview />;
    }
  };

  const tabs = [
    { id: 'dashboard', label: 'Overview', color: '#64748B', activeColor: '#3B82F6' },
    { id: 'security', label: 'Security', color: '#64748B', activeColor: '#EF4444' },
    { id: 'leads', label: 'Leads', color: '#64748B', activeColor: '#3B82F6' },
    { id: 'voice', label: 'Voice', color: '#64748B', activeColor: '#10B981' },
    { id: 'billing', label: 'Billing', color: '#64748B', activeColor: '#F59E0B' }
  ];

  return (
    <div className="relative w-full h-screen bg-[#05080f] flex flex-col font-['Inter',sans-serif] text-[#e2e8f0] overflow-hidden selection:bg-blue-500/30">
      
      {/* Glassmorphism Header */}
      <header className="absolute top-0 w-full h-16 bg-[#05080f]/70 backdrop-blur-md border-b border-white/5 flex items-center justify-between px-5 shrink-0 z-40">
        <div className="flex flex-col gap-0.5">
          <span className="text-[9px] text-[#64748b] font-bold uppercase tracking-[0.2em]">Audit Swarm</span>
          <span className="text-sm font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-white/60 capitalize">
            {currentView}
          </span>
        </div>
      </header>

      {/* Main Scrollable Viewport (Added top padding for fixed header) */}
      <div className="flex-1 overflow-y-auto pt-20 pb-28 scrollbar-none">
        {renderView()}
      </div>

      {/* Floating Bottom Nav Dock */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[96%] max-w-lg h-16 bg-[#0d1420]/80 backdrop-blur-xl border border-white/10 rounded-2xl flex items-center justify-around px-2 z-50 shadow-2xl shadow-black/50">
        {tabs.map((tab) => {
          const isActive = currentView === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setCurrentView(tab.id)}
              className="relative flex flex-col items-center justify-center w-14 h-full gap-1.5 outline-none group"
            >
              {/* Animated Glow Backdrop */}
              {isActive && (
                <div 
                  className="absolute inset-0 m-auto size-8 rounded-full blur-md opacity-20"
                  style={{ backgroundColor: tab.activeColor }}
                />
              )}
              
              <div 
                className="size-1.5 rounded-full transition-all duration-300 ease-out z-10"
                style={{ 
                  backgroundColor: isActive ? tab.activeColor : tab.color, 
                  transform: isActive ? 'scale(1.2)' : 'scale(1)',
                  boxShadow: isActive ? `0 0 8px ${tab.activeColor}` : 'none'
                }}
              />
              <span 
                className={`text-[9px] tracking-wider transition-all duration-300 z-10 ${
                  isActive ? 'text-white font-bold translate-y-0' : 'text-[#64748b] font-medium translate-y-0.5 group-hover:text-[#94a3b8]'
                }`}
              >
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
      
    </div>
  );
}