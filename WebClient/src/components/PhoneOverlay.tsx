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
    san, money, gpa, chapter, turn, history, affinity, active_roommates, player_name
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
      <div className="w-[380px] h-[780px] bg-slate-900 rounded-[3.5rem] p-3 shadow-2xl border border-slate-700 relative z-10 pointer-events-auto ring-8 ring-slate-800">
        
        {/* Dynamic Island / Earpiece Decoration */}
        <div className="absolute top-6 left-1/2 -translate-x-1/2 w-28 h-6 bg-black rounded-full z-[1100] border border-white/5 flex items-center justify-center shadow-inner" />

        {/* Status Bar */}
        <div className="absolute top-6 inset-x-10 h-8 flex justify-between items-center z-[1050] px-6 select-none">
            <div className="text-[12px] font-bold text-slate-800 font-sans tracking-tight">
                {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
            <div className="flex items-center space-x-1.5 opacity-80 scale-90 text-slate-800">
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
                    className={`absolute inset-0 bg-cover bg-center transition-all duration-1000 ${currentApp ? 'scale-110 blur-2xl opacity-40' : 'scale-100 opacity-100'}`} 
                    style={{ backgroundImage: "url('https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?q=80&w=2070&auto=format&fit=crop')" }}
                />
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
                    notifications={wechatNotifications} 
                    clearNotifications={clearWechatNotifications} 
                    affinity={affinity}
                    activeRoommates={active_roommates}
                    playerName={player_name}
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

            {/* HOME INDICATOR (Minimalist Flat) */}
            <div className="absolute bottom-3 inset-x-0 h-10 flex items-center justify-center z-[1500] pointer-events-none">
              <button 
                  onClick={handleHomeClick}
                  className="w-32 h-1.5 bg-slate-800/10 hover:bg-slate-800/20 rounded-full transition-all duration-300 pointer-events-auto active:scale-95"
                  title="回到桌面"
              />
            </div>
        </div>

        {/* Floating Side Button (Power/Exit) */}
        <button 
            onClick={() => togglePhone(false)}
            className="absolute top-1/2 -left-20 w-14 h-14 bg-white/90 backdrop-blur-md rounded-2xl border border-slate-200 text-slate-600 flex items-center justify-center shadow-lg transition-all hover:scale-110 hover:text-rose-500 active:scale-95 pointer-events-auto group"
            title="关闭手机"
        >
            <X size={28} className="group-hover:rotate-90 transition-transform duration-500" />
            <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-[9px] font-bold uppercase text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">Exit</span>
        </button>

      </div>
    </div>
  );
};
