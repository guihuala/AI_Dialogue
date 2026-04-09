import { X } from 'lucide-react';
import { useGameStore } from '../store/gameStore';
import { useState, useEffect } from 'react';
import { HomeView } from './phone/HomeView';
import { WeChatApp } from './phone/apps/WeChatApp';
import { CalendarApp } from './phone/apps/CalendarApp';
import { JMUApp } from './phone/apps/JMUApp';
import { AlipayApp } from './phone/apps/AlipayApp';

export const PhoneOverlay = () => {
  const { 
    wechatNotifications, 
    wechatSessions,
    clearWechatNotifications, 
    isPhoneOpen, 
    togglePhone,
    money, gpa, chapter, turn, maxTurns, currentEventName, current_scene, history
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
      <div className="w-[380px] h-[780px] bg-gradient-to-b from-slate-900 to-slate-800 rounded-[3.5rem] p-3 shadow-[0_40px_90px_rgba(15,23,42,0.65)] border border-cyan-200/10 relative z-10 pointer-events-auto ring-8 ring-slate-900/70">
        
        {/* Dynamic Island / Earpiece Decoration */}
        <div className="absolute top-6 left-1/2 -translate-x-1/2 w-28 h-6 bg-black rounded-full z-[1100] border border-white/10 flex items-center justify-center shadow-inner" />

        {/* Status Bar */}
        <div className="absolute top-6 inset-x-10 h-8 flex justify-between items-center z-[1050] px-6 select-none">
            <div className="text-[12px] font-black text-slate-700 font-sans tracking-tight">
                {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
            <div className="flex items-center space-x-1.5 opacity-80 scale-90 text-slate-700">
                <div className="w-5 h-[10px] rounded-[2px] border border-current relative flex items-center p-[1px]">
                    <div className="h-full bg-current rounded-[1px]" style={{ width: '85%' }} />
                </div>
            </div>
        </div>

        {/* SCREEN CONTAINER */}
        <div className="w-full h-full rounded-[2.8rem] overflow-hidden relative flex flex-col bg-slate-50 shadow-inner">
            {/* Minimalist Wallpaper */}
            <div className="absolute inset-0 z-0 overflow-hidden">
                <div 
                    className={`absolute inset-0 transition-all duration-700 ${currentApp ? 'scale-105 blur-xl opacity-70' : 'scale-100 opacity-100'}`}
                    style={{
                      background:
                        "radial-gradient(120% 80% at 20% 10%, rgba(6,182,212,0.2) 0%, rgba(6,182,212,0) 55%), radial-gradient(100% 60% at 90% 80%, rgba(59,130,246,0.22) 0%, rgba(59,130,246,0) 60%), linear-gradient(160deg, #f8fdff 0%, #eef8ff 48%, #eaf6ff 100%)",
                    }}
                />
                <div className="absolute inset-0 bg-[linear-gradient(130deg,rgba(255,255,255,0.15)_0%,rgba(255,255,255,0)_55%)]" />
                {!currentApp && <div className="absolute inset-0 bg-white/30 backdrop-blur-[1px]" />}
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
                    sessions={wechatSessions}
                    notifications={wechatNotifications} 
                    clearNotifications={clearWechatNotifications} 
                  />
                )}
                {currentApp === 'calendar' && (
                  <CalendarApp chapter={chapter} turn={turn} maxTurns={maxTurns} currentEventName={currentEventName} currentScene={current_scene} history={history} />
                )}
                {currentApp === 'jmu' && (
                  <JMUApp gpa={gpa} history={history} />
                )}
                {currentApp === 'alipay' && (
                  <AlipayApp money={money} history={history} />
                )}
            </div>

            {/* HOME INDICATOR (Minimalist Flat) */}
            <div className="absolute bottom-3 inset-x-0 h-10 flex items-center justify-center z-[1500] pointer-events-none">
              <button 
                  onClick={handleHomeClick}
                  className="w-32 h-1.5 bg-slate-700/20 hover:bg-cyan-500/40 rounded-full transition-all duration-300 pointer-events-auto active:scale-95"
                  title="回到桌面"
              />
            </div>
        </div>

        {/* Floating Side Button (Power/Exit) */}
        <button 
            onClick={() => togglePhone(false)}
            className="absolute top-1/2 -left-20 w-14 h-14 bg-white/85 backdrop-blur-md rounded-2xl border border-cyan-100 text-slate-600 flex items-center justify-center shadow-lg transition-all hover:scale-110 hover:text-rose-500 active:scale-95 pointer-events-auto group"
            title="关闭手机"
        >
            <X size={28} className="group-hover:rotate-90 transition-transform duration-500" />
            <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-[9px] font-bold uppercase text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">Exit</span>
        </button>

      </div>
    </div>
  );
};
