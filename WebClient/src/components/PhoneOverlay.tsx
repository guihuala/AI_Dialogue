import { Send, MessageCircle, Calendar, ClipboardList, ChevronLeft, Clock, DollarSign, Brain, Heart, Sparkles, X } from 'lucide-react';
import { useGameStore } from '../store/gameStore';
import { useEffect, useRef, useState } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';

export const PhoneOverlay = () => {
  const { 
    wechatNotifications, 
    clearWechatNotifications, 
    isPhoneOpen, 
    togglePhone,
    san, money, hygiene, reputation, gpa, chapter, turn, history
  } = useGameStore();
  
  const [currentApp, setCurrentApp] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (currentApp === 'wechat') {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [wechatNotifications, currentApp]);

  const renderAppIcon = (id: string, name: string, icon: any, color: string) => (
    <div 
        onClick={() => setCurrentApp(id)}
        className="flex flex-col items-center space-y-2 group cursor-pointer"
    >
        <div className={`w-16 h-16 rounded-[1.4rem] ${color} flex items-center justify-center text-white shadow-xl group-hover:scale-110 active:scale-95 transition-all duration-300 relative`}>
            {icon}
            {id === 'wechat' && wechatNotifications.length > 0 && (
                <div className="absolute -top-1 -right-1 w-6 h-6 bg-rose-500 rounded-full border-2 border-white text-[10px] font-black flex items-center justify-center shadow-lg animate-bounce">
                    {wechatNotifications.length}
                </div>
            )}
        </div>
        <span className="text-[10px] font-black text-white/90 tracking-widest uppercase text-shadow-sm">{name}</span>
    </div>
  );

  const HomeView = () => (
    <div className="flex-1 p-8 pt-20 animate-in fade-in zoom-in duration-500">
        <div className="grid grid-cols-3 gap-y-10">
            {renderAppIcon('wechat', '微信', <MessageCircle size={32} />, 'bg-emerald-500')}
            {renderAppIcon('calendar', '日历', <Calendar size={32} />, 'bg-rose-500')}
            {renderAppIcon('memo', '备忘录', <ClipboardList size={32} />, 'bg-amber-500')}
        </div>
    </div>
  );

  const WeChatApp = () => (
    <div className="flex-1 flex flex-col bg-[#F3F4F6] animate-in slide-in-from-right duration-300">
        <div className="bg-white/90 backdrop-blur-md px-6 py-4 flex items-center shrink-0 border-b border-gray-200">
            <button onClick={() => setCurrentApp(null)} className="mr-4 text-gray-500 hover:text-emerald-500 transition-colors">
                <ChevronLeft size={24} />
            </button>
            <h3 className="font-black text-slate-800">微信</h3>
            {wechatNotifications.length > 0 && (
                <button 
                  onClick={clearWechatNotifications}
                  className="ml-auto text-[10px] font-black text-rose-500 bg-rose-50 px-2 py-1 rounded-full uppercase tracking-widest"
                >
                  清除
                </button>
            )}
        </div>
        <div className="flex-1 p-4 overflow-y-auto custom-scrollbar flex flex-col space-y-4">
            {wechatNotifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full opacity-20 grayscale">
                    <MessageCircle size={64} className="mb-4" />
                    <p className="text-xs font-black uppercase tracking-widest">暂无新消息</p>
                </div>
            ) : (
                wechatNotifications.map((msg, idx) => (
                    <div key={idx} className="flex flex-col items-start animate-fade-in-up">
                        <span className="text-[10px] text-gray-400 mb-1 ml-1 font-black uppercase tracking-widest">{msg.sender}</span>
                        <div className="bg-white text-slate-800 px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm max-w-[85%] border border-gray-100 text-sm leading-relaxed whitespace-pre-wrap relative font-medium">
                            {msg.message}
                        </div>
                    </div>
                ))
            )}
            <div ref={messagesEndRef} />
        </div>
        <div className="bg-gray-100 border-t border-gray-200 p-4 flex items-center pb-8 shrink-0">
            <div className="flex-1 bg-white rounded-full h-10 px-4 border border-gray-300 flex items-center text-xs text-gray-400 font-bold uppercase tracking-widest">
                暂不可用
            </div>
            <button className="ml-3 w-10 h-10 rounded-full bg-emerald-500 text-white flex items-center justify-center shadow-md opacity-30 cursor-not-allowed">
                <Send size={16} />
            </button>
        </div>
    </div>
  );

  const CalendarApp = () => (
    <div className="flex-1 flex flex-col bg-white animate-in slide-in-from-right duration-300">
        <div className="bg-rose-500/10 backdrop-blur-md px-6 py-6 border-b border-rose-500/10 flex items-center shrink-0">
            <button onClick={() => setCurrentApp(null)} className="mr-4 text-rose-500 hover:text-rose-700 transition-colors">
                <ChevronLeft size={24} />
            </button>
            <h3 className="font-black text-rose-600 flex items-center">
                <Calendar size={18} className="mr-2" /> 日历 / 时间线
            </h3>
        </div>
        <div className="flex-1 p-6 overflow-y-auto custom-scrollbar space-y-6">
            <div className="bg-rose-500 text-white p-6 rounded-3xl shadow-lg shadow-rose-900/20 mb-8">
                <div className="text-4xl font-black mb-1">CH.{chapter}</div>
                <div className="text-xs font-black tracking-[0.2em] opacity-80 uppercase italic">Chapter Sequence / Current Term</div>
                <div className="mt-4 flex items-center text-sm font-black">
                    <Clock size={16} className="mr-2" /> 当前对局回合: {turn}
                </div>
            </div>

            <h4 className="text-[10px] font-black text-rose-300 uppercase tracking-[0.3em] mb-4">历史节点 (Timeline)</h4>
            <div className="space-y-4">
                {history.slice(-10).reverse().map((h, i) => (
                    <div key={i} className="flex space-x-4 group">
                        <div className="flex flex-col items-center shrink-0">
                            <div className="w-8 h-8 rounded-full bg-rose-100 text-rose-500 flex items-center justify-center text-[10px] font-black border-2 border-white shadow-sm">
                                T{h.turn}
                            </div>
                            <div className="flex-1 w-[2px] bg-rose-100 group-last:hidden mt-2" />
                        </div>
                        <div className="flex-1 bg-slate-50 p-4 rounded-2xl border border-slate-100 text-[10px] font-bold text-slate-500 leading-relaxed truncate">
                            {h.text.split('\n')[0]}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    </div>
  );

  const MemoApp = () => (
    <div className="flex-1 flex flex-col bg-[#FFFAF0] animate-in slide-in-from-right duration-300">
        <div className="bg-amber-500/10 backdrop-blur-md px-6 py-6 border-b border-amber-500/10 flex items-center shrink-0">
            <button onClick={() => setCurrentApp(null)} className="mr-4 text-amber-600 hover:text-amber-800 transition-colors">
                <ChevronLeft size={24} />
            </button>
            <h3 className="font-black text-amber-700 flex items-center">
                <ClipboardList size={18} className="mr-2" /> 备忘录 / 个人属性
            </h3>
        </div>
        <div className="flex-1 p-8 overflow-y-auto custom-scrollbar">
            <div className="grid grid-cols-2 gap-4">
                <div className="bg-white p-6 rounded-[2rem] border border-amber-100 shadow-sm space-y-2">
                    <Brain className="text-indigo-500" size={24} />
                    <div className="text-[8px] font-black text-slate-400 uppercase tracking-widest">理智 (SAN)</div>
                    <div className="text-2xl font-black text-indigo-600">{san}</div>
                </div>
                <div className="bg-white p-6 rounded-[2rem] border border-amber-100 shadow-sm space-y-2">
                    <DollarSign className="text-emerald-500" size={24} />
                    <div className="text-[8px] font-black text-slate-400 uppercase tracking-widest">资产 (¥)</div>
                    <div className="text-2xl font-black text-emerald-600">{money}</div>
                </div>
                <div className="bg-white p-6 rounded-[2rem] border border-amber-100 shadow-sm space-y-2">
                    <Sparkles className="text-amber-500" size={24} />
                    <div className="text-[8px] font-black text-slate-400 uppercase tracking-widest">绩点 (GPA)</div>
                    <div className="text-2xl font-black text-amber-600">{gpa.toFixed(1)}</div>
                </div>
                <div className="bg-white p-6 rounded-[2rem] border border-amber-100 shadow-sm space-y-2">
                    <Heart className="text-rose-500" size={24} />
                    <div className="text-[8px] font-black text-slate-400 uppercase tracking-widest">声望</div>
                    <div className="text-2xl font-black text-rose-600">{reputation}</div>
                </div>
            </div>
            
            <div className="mt-8 bg-white p-6 rounded-[2.5rem] border border-amber-100 shadow-sm">
                <h5 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6 flex justify-center">角色雷达图</h5>
                <div className="h-48 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={[
                            { subject: '理智', A: san, fullMark: 100 },
                            { subject: '声望', A: reputation, fullMark: 100 },
                            { subject: '学业', A: Math.min((gpa / 4.0) * 100, 100), fullMark: 100 },
                            { subject: '整洁', A: hygiene, fullMark: 100 },
                            { subject: '财富', A: Math.min((money / 1000) * 100, 100), fullMark: 100 },
                        ]}>
                            <PolarGrid stroke="#fcd34d" strokeOpacity={0.3} />
                            <PolarAngleAxis dataKey="subject" tick={{ fill: '#d97706', fontSize: 10, fontWeight: 900 }} />
                            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                            <Radar name="Status" dataKey="A" stroke="#f59e0b" fill="#fbbf24" fillOpacity={0.5} />
                            <Tooltip 
                                contentStyle={{ backgroundColor: 'rgba(255,255,255,0.9)', borderRadius: '12px', border: '1px solid rgba(245,158,11,0.2)', fontSize: '12px', fontWeight: 'bold', color: '#b45309' }}
                                itemStyle={{ color: '#d97706' }}
                                formatter={(value: any) => [Math.round(value as number), '']}
                            />
                        </RadarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    </div>
  );

  return (
    <div className={`fixed top-0 right-0 h-full z-[1000] flex items-center justify-end p-4 md:p-8 pointer-events-none transition-transform duration-700 ease-in-out ${isPhoneOpen ? 'translate-x-0' : 'translate-x-[150%]'}`}>
      
      {/* Phone Case Simulator */}
      <div className="w-[380px] h-[780px] bg-slate-900 rounded-[3.5rem] p-4 shadow-[-20px_0_50px_rgba(0,0,0,0.5)] border-[12px] border-slate-800 relative z-10 ring-[20px] ring-black/10 pointer-events-auto">
        
        {/* Floating Close Button */}
        <button 
            onClick={() => togglePhone(false)}
            title="关闭手机"
            className="absolute top-1/2 -left-16 w-12 h-12 bg-black/50 hover:bg-rose-500 backdrop-blur-md rounded-full border border-white/20 text-white flex items-center justify-center shadow-[0_0_20px_rgba(0,0,0,0.5)] transition-all pointer-events-auto"
        >
            <X size={24} />
        </button>
        
        {/* Dynamic Island */}
        <div className="absolute top-8 left-1/2 -translate-x-1/2 w-32 h-7 bg-black rounded-full z-[1100] border border-white/5 flex items-center justify-center">
            <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse shadow-[0_0_5px_rgba(59,130,246,0.8)]" />
        </div>

        {/* Status Bar */}
        <div className="absolute top-8 inset-x-10 h-7 flex justify-between items-center z-[1050] px-4">
            <div className="text-[10px] font-black text-white">12:00</div>
            <div className="flex items-center space-x-2">
                <div className="w-4 h-2 rounded-sm border border-white/40 relative">
                    <div className="absolute inset-x-0 inset-y-0.5 bg-white/80 rounded-[1px] m-0.5" style={{ width: '80%' }} />
                </div>
            </div>
        </div>

        {/* Screen Container */}
        <div className="w-full h-full rounded-[2.8rem] overflow-hidden relative flex flex-col shadow-inner bg-black">
            {/* Wallpaper (if not in an app) */}
            {!currentApp && (
                <div 
                    className="absolute inset-0 bg-cover bg-center transition-transform duration-[2000ms] group-hover:scale-110 flex items-center justify-center" 
                    style={{ backgroundImage: "url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?ixlib=rb-4.0.3&auto=format&fit=crop&w=1364&q=80')" }}
                >
                    <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/60" />
                </div>
            )}

            {/* App Content */}
            {currentApp === 'wechat' ? <WeChatApp /> : 
             currentApp === 'calendar' ? <CalendarApp /> : 
             currentApp === 'memo' ? <MemoApp /> : 
             <HomeView />}

            {/* Home Indicator */}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 w-1/3 h-1.5 bg-white/40 rounded-full z-[1200] cursor-pointer hover:bg-white transition-colors shadow-sm" onClick={() => setCurrentApp(null)} />
        </div>

        {/* Close Button UI (Physical-like) */}
        <button 
            onClick={() => togglePhone(false)}
            title="关闭手机"
            className="absolute top-1/2 -right-4 translate-x-3 w-3 h-20 bg-slate-800 rounded-full border border-white/10 hover:bg-rose-500 transition-colors shadow-lg cursor-pointer group active:translate-x-2 flex items-center justify-center -mr-2"
        >
            <span className="w-1 h-10 bg-white/20 rounded-full group-hover:bg-white/50"></span>
        </button>
        <button 
            className="absolute top-40 -left-4 -translate-x-3 w-1.5 h-10 bg-slate-800 rounded-full border border-white/10 shadow-lg"
        />
        <button 
            className="absolute top-56 -left-4 -translate-x-3 w-1.5 h-10 bg-slate-800 rounded-full border border-white/10 shadow-lg"
        />
      </div>
    </div>
  );
};
