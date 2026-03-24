import { Contact2, Heart, ShieldEllipsis, ChevronRight, User, Trophy } from 'lucide-react';
import { useEffect, useState } from 'react';

interface WeChatAppProps {
  notifications: any[];
  clearNotifications: () => void;
  affinity: Record<string, number>;
  activeRoommates: string[];
  playerName: string;
}

const WECHAT_CONFIG: Record<string, { nickName: string; avatar?: string; bio: string }> = {};

export const WeChatApp = ({ notifications, clearNotifications, affinity, activeRoommates, playerName }: WeChatAppProps) => {
  const [activeProfile, setActiveProfile] = useState<any | null>(null);
  useEffect(() => {
    if (notifications.length > 0) {
      clearNotifications();
    }
  }, [notifications.length, clearNotifications]);

  const getFriendInfo = (name: string) => {
    return WECHAT_CONFIG[name] || { nickName: name, bio: '这个同学暂时还没有更多公开资料。' };
  };

  const allFriends = Array.from(new Set([...activeRoommates, ...Object.keys(affinity)]))
    .filter(name => name && name !== playerName);

  const renderLevel = (score: number) => {
    if (score >= 85) return { label: 'EX', cls: 'text-amber-500 border-amber-300' };
    if (score >= 65) return { label: 'A', cls: 'text-emerald-500 border-emerald-300' };
    if (score >= 40) return { label: 'B', cls: 'text-cyan-500 border-cyan-300' };
    return { label: 'C', cls: 'text-slate-400 border-slate-300' };
  };

  const renderContactsList = () => (
    <div className="flex-1 flex flex-col bg-slate-50 animate-in fade-in duration-300">
      <div className="px-6 pt-12 pb-4 bg-white/90 backdrop-blur-sm shrink-0 border-b border-slate-100">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-black text-slate-800 tracking-tight">关系面板</h3>
          <Contact2 size={22} className="text-cyan-500" />
        </div>
        <div className="text-[11px] font-bold text-slate-500">
          当前显示舍友关系变化，不提供即时聊天。
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar divide-y divide-slate-100 pb-24">
        <div className="bg-slate-50 px-6 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
          <ShieldEllipsis size={14} className="text-cyan-500" /> 舍友好感监测
        </div>

        {allFriends.length === 0 ? (
          <div className="px-6 py-16 text-center text-slate-400 text-xs font-bold">
            暂无可显示的舍友关系数据
          </div>
        ) : (
          allFriends.map((name) => {
            const score = Number(affinity[name] || 0);
            const info = getFriendInfo(name);
            const level = renderLevel(score);
            return (
              <button
                key={name}
                onClick={() => setActiveProfile({ name, score, level, info })}
                className="w-full text-left flex items-center px-6 py-4 hover:bg-cyan-50/30 transition-all group"
              >
                <div className="w-14 h-14 rounded-2xl bg-white shadow-sm overflow-hidden flex items-center justify-center mr-4 shrink-0 border border-cyan-100/70">
                  {info.avatar ? <img src={info.avatar} className="w-full h-full object-cover" /> : <User size={30} className="text-slate-400" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-black text-slate-800 text-[16px] truncate">{info.nickName || name}</span>
                    <span className={`text-[10px] font-black border px-1.5 rounded-md shrink-0 ${level.cls}`}>{level.label}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1.5">
                    <div className="flex gap-0.5 shrink-0">
                      {[...Array(5)].map((_, i) => (
                        <Heart
                          key={i}
                          size={11}
                          fill={i < Math.floor(score / 20) ? '#f43f5e' : 'transparent'}
                          className={i < Math.floor(score / 20) ? 'text-rose-500' : 'text-slate-200'}
                        />
                      ))}
                    </div>
                    <div className="h-1 flex-1 bg-slate-100 rounded-full max-w-[80px] overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-cyan-400 to-rose-400" style={{ width: `${Math.max(0, Math.min(100, score))}%` }} />
                    </div>
                    <span className="text-[10px] font-black text-slate-400 tabular-nums">VAL:{score}</span>
                  </div>
                </div>
                <ChevronRight size={18} className="text-slate-300 group-hover:translate-x-1 transition-transform" />
              </button>
            );
          })
        )}
      </div>
    </div>
  );

  const renderProfileDetail = (p: any) => (
    <div className="flex-1 flex flex-col bg-slate-50 animate-in slide-in-from-right duration-300">
      <div className="bg-white/90 backdrop-blur-sm px-4 py-1 flex items-center shrink-0 border-b border-slate-200/50 pt-10">
        <button onClick={() => setActiveProfile(null)} className="p-2 text-slate-600 hover:text-cyan-600">
          <ChevronRight size={24} className="rotate-180" />
        </button>
        <div className="flex-1 text-center font-black text-slate-800 text-[16px] truncate">关系详情</div>
        <div className="w-10" />
      </div>

      <div className="flex-1 py-8 px-6 space-y-4 overflow-y-auto custom-scrollbar pb-20">
        <div className="bg-white rounded-[1.6rem] px-6 py-8 border border-cyan-100/70 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="w-20 h-20 rounded-2xl bg-slate-100 overflow-hidden flex items-center justify-center border border-slate-200">
              {p.info.avatar ? <img src={p.info.avatar} className="w-full h-full object-cover" /> : <User size={40} className="text-slate-400" />}
            </div>
            <div className="min-w-0">
              <h4 className="text-2xl font-black text-slate-800 truncate">{p.info.nickName || p.name}</h4>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">@{p.name}</p>
            </div>
          </div>

          <p className="text-xs text-slate-500 font-bold mt-5">“{p.info.bio}”</p>

          <div className="grid grid-cols-2 gap-3 mt-6">
            <div className="bg-cyan-50 p-4 rounded-2xl text-center">
              <span className="text-[10px] font-black text-slate-500 uppercase block">好感值</span>
              <span className="text-2xl font-black text-slate-800 tabular-nums">{p.score}</span>
            </div>
            <div className="bg-amber-50 p-4 rounded-2xl text-center">
              <Trophy className="text-amber-500 mx-auto mb-1" size={18} />
              <span className="text-[10px] font-black text-slate-500 uppercase block">等级</span>
              <span className="text-2xl font-black text-slate-800">{p.level.label}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col relative overflow-hidden bg-white">
      {activeProfile ? renderProfileDetail(activeProfile) : renderContactsList()}
    </div>
  );
};
