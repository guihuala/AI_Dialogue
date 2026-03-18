import { X } from 'lucide-react';
import { useGameStore } from '../store/gameStore';
import { useState, useEffect } from 'react';
import { HomeView } from './phone/HomeView';
import { WeChatApp } from './phone/apps/WeChatApp';
import { CalendarApp } from './phone/apps/CalendarApp';
import { JMUApp } from './phone/apps/JMUApp';
import { AlipayApp } from './phone/apps/AlipayApp';
import { WellnessApp } from './phone/apps/WellnessApp';

export const PhoneOverlay = () => {
  const { 
    wechatNotifications, 
    clearWechatNotifications, 
    isPhoneOpen, 
    togglePhone,
    san, money, gpa, chapter, turn, history, affinity, active_roommates
  } = useGameStore();
  
  const [currentApp, setCurrentApp] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleHomeClick = () => {
    setCurrentApp(null);
  };

  return (
    <div className={`fixed inset-y-0 right-0 z-[1000] flex items-center justify-end p-4 md:p-10 pointer-events-none transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] ${isPhoneOpen ? 'translate-x-0' : 'translate-x-[150%]'}`}>
      <div className="w-[400px] h-[820px] bg-slate-900 rounded-[4rem] p-4 shadow-[-40px_0_80px_rgba(0,0,0,0.6)] border-[14px] border-slate-800 relative z-10 pointer-events-auto ring-1 ring-white/10 ring-inset">
        
        {/* Power Button */}
        <button 
          onClick={() => togglePhone(false)}
          className="absolute top-1/2 -right-4 translate-x-3.5 w-4 h-24 bg-slate-800 rounded-full border border-white/10 hover:bg-rose-500 transition-colors shadow-2xl z-50 group pointer-events-auto"
        >
          <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity rounded-full blur-sm" />
        </button>

        {/* Dynamic Island */}
        <div className="absolute top-8 left-1/2 -translate-x-1/2 w-32 h-8 bg-black rounded-full z-[1100] border border-white/5 shadow-inner flex items-center justify-center gap-2">
            <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,211,238,0.8)]" />
            <div className="w-3 h-3 bg-slate-900 rounded-full border border-white/5" />
        </div>

        {/* Status Bar */}
        <div className="absolute top-8 inset-x-12 h-8 flex justify-between items-center z-[1050] px-4 select-none">
            <div className="text-[12px] font-black text-white/90 font-mono tracking-tighter">
                {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
            <div className="flex items-center space-x-2">
                <div className="w-6 h-[10px] rounded-[2px] border border-white/30 relative flex items-center p-[1px]">
                    <div className="h-full bg-white/90 rounded-[1px]" style={{ width: '85%' }} />
                    <div className="absolute -right-1 w-0.5 h-1 bg-white/30 rounded-full" />
                </div>
            </div>
        </div>

        {/* SCREEN CONTAINER */}
        <div className="w-full h-full rounded-[3rem] overflow-hidden relative flex flex-col shadow-inner bg-black ring-1 ring-white/5">
            {/* Wallpaper Overlay */}
            <div className="absolute inset-0 z-0">
                <div 
                    className={`absolute inset-0 bg-cover bg-center transition-all duration-[2000ms] ${currentApp ? 'scale-105 blur-2xl opacity-60' : 'scale-100 blur-0 opacity-100'}`} 
                    style={{ backgroundImage: "url('https://images.unsplash.com/photo-1557683316-973673baf926?q=80&w=2029&auto=format&fit=crop')" }}
                />
                <div className="absolute inset-0 bg-white/10 backdrop-blur-[2px]" />
            </div>

            <div className="relative z-10 flex-1 flex flex-col overflow-hidden">
                {!currentApp && (
                  <HomeView 
                    onAppClick={setCurrentApp} 
                    wechatNotificationsCount={wechatNotifications.length} 
                  />
                )}
                {currentApp === 'wechat' && (
                  <WeChatApp 
                    notifications={wechatNotifications} 
                    clearNotifications={clearWechatNotifications} 
                    affinity={affinity}
                    activeRoommates={active_roommates}
                  />
                )}
                {currentApp === 'calendar' && (
                  <CalendarApp chapter={chapter} turn={turn} history={history} />
                )}
                {currentApp === 'jmu' && (
                  <JMUApp gpa={gpa} history={history} />
                )}
                {currentApp === 'alipay' && (
                  <AlipayApp money={money} history={history} />
                )}
                {currentApp === 'wellness' && (
                  <WellnessApp san={san} />
                )}
            </div>

            {/* HOME INDICATOR */}
            <div className="absolute bottom-4 inset-x-0 h-14 flex items-center justify-center z-[1500] pointer-events-none">
              <button 
                  onClick={handleHomeClick}
                  className="w-40 h-2.5 bg-white/80 hover:bg-white rounded-full transition-all duration-300 pointer-events-auto hover:h-4 hover:scale-105 active:scale-90 shadow-[0_0_25px_rgba(0,0,0,0.8),0_0_10px_rgba(255,255,255,0.4)] group relative overflow-hidden ring-1 ring-black/20"
                  title="回到桌面"
              >
                  <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 bg-gradient-to-r from-transparent via-white/50 to-transparent" />
              </button>
            </div>
        </div>

        {/* Close Button */}
        <button 
            onClick={() => togglePhone(false)}
            className="absolute top-1/2 -left-20 w-14 h-14 bg-black group hover:bg-[var(--color-cyan-main)] backdrop-blur-md rounded-[1.2rem] border border-white/10 text-white flex items-center justify-center shadow-2xl transition-all scale-100 hover:scale-110 active:scale-95 pointer-events-auto"
            title="关闭手机"
        >
            <X size={28} className="group-hover:rotate-90 transition-transform duration-500" />
            <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-[9px] font-black uppercase text-white/40 tracking-[0.2em] opacity-0 group-hover:opacity-100 transition-opacity">Exit</span>
        </button>

      </div>
    </div>
  );
};
