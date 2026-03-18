import { Users, User, ChevronRight, Search, PlusCircle, MessageSquare, Contact2, Heart, ShieldEllipsis, Trophy, Video, Phone } from 'lucide-react';
import { useRef, useEffect, useState } from 'react';

interface WeChatAppProps {
  notifications: any[];
  clearNotifications: () => void;
  affinity: Record<string, number>;
  activeRoommates: string[];
}

// Roommate WeChat Configuration
const WECHAT_CONFIG: Record<string, { nickName: string; avatar?: string; bio: string }> = {
  '小明': { nickName: '明明努力中', bio: '生活不止眼前的苟且，还有远方的兼职。', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=XiaoMing' },
  '二哥': { nickName: '狂暴补给站', bio: '干饭人，干饭魂。', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=ErGe' },
  '舍长': { nickName: '404 守护者', bio: '为了宿舍的和平。', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Boss' },
  '苏梦': { nickName: '梦里有流星', bio: '繁星闪烁。', avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=SuMeng' },
};

export const WeChatApp = ({ notifications, clearNotifications, affinity, activeRoommates }: WeChatAppProps) => {
  const [activeTab, setActiveTab] = useState<'chats' | 'contacts' | 'discovery'>('chats');
  const [activeChat, setActiveChat] = useState<any | null>(null);
  const [activeProfile, setActiveProfile] = useState<any | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeChat) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      // Clear notifications when entering a chat to satisfy "OCD"
      if (notifications.length > 0) {
        clearNotifications();
      }
    }
  }, [activeChat, notifications, clearNotifications]);

  const getFriendInfo = (name: string) => {
    return WECHAT_CONFIG[name] || { nickName: name, bio: '这个同学很神秘，什么都没写。' };
  };

  // Group real notifications by sender
  const realConversations = notifications.reduce((acc: any, curr) => {
    if (!acc[curr.sender]) {
      const info = getFriendInfo(curr.sender);
      acc[curr.sender] = {
        id: curr.sender,
        name: curr.sender,
        nickName: info.nickName,
        avatar: info.avatar,
        messages: [],
        isGroup: false,
        lastTime: '刚刚'
      };
    }
    acc[curr.sender].messages = [...acc[curr.sender].messages, curr];
    return acc;
  }, {});

  // Predefined Mock conversations
  const mockChats: any[] = [
    { 
      id: 'dorm_group', 
      name: '404 宿舍研讨组', 
      isGroup: true, 
      lastMsg: '今天晚上有人带饭吗？', 
      time: '09:41',
      messages: [
        { sender: '舍长', message: '今天晚上有人带饭吗？' },
        { sender: '二哥', message: '我想吃食堂那家牛肉面，有人去吗？' },
        { sender: '小明', message: '我在外面兼职呢，回不去。' }
      ]
    },
    { 
      id: 'academic', 
      name: '教务处通知群', 
      isGroup: true, 
      lastMsg: '关于本周选修课调整的通知', 
      time: '昨日',
      messages: [
        { sender: '教务处系统', message: '关于本周选修课调整的通知：部分由于教授出差，课程顺延。' }
      ]
    }
  ];

  const allChats = [
    ...Object.values(realConversations),
    ...mockChats
  ];

  const renderChatList = () => (
    <div className="flex-1 flex flex-col bg-white animate-in fade-in duration-300">
      <div className="px-6 pt-12 pb-4 bg-[#ededed] shrink-0">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-slate-800">微信</h3>
          <div className="flex gap-4 text-slate-600">
            <Search size={22} className="cursor-pointer hover:text-emerald-500 transition-colors" />
            <PlusCircle size={22} className="cursor-pointer hover:text-emerald-500 transition-colors" />
          </div>
        </div>
        <div className="bg-white rounded-lg py-2 px-4 shadow-sm flex items-center gap-2 cursor-pointer group">
          <Search size={14} className="text-slate-400 group-hover:text-emerald-500 transition-colors" />
          <span className="text-xs text-slate-400 font-medium">搜索记录</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar divide-y divide-gray-50 pb-32">
        {allChats.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 opacity-20 text-slate-400">
            <MessageSquare size={48} className="mb-4" />
            <p className="text-[10px] font-black uppercase tracking-widest">暂无聊天记录</p>
          </div>
        ) : (
          allChats.map((chat: any) => (
            <div 
              key={chat.id}
              onClick={() => setActiveChat(chat)}
              className="flex items-center px-6 py-4 hover:bg-slate-50 cursor-pointer active:bg-slate-100 transition-colors"
            >
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center mr-4 shrink-0 relative overflow-hidden ${chat.isGroup ? 'bg-slate-200 p-0.5 grid grid-cols-2 gap-0.5' : 'bg-slate-100 shadow-sm'}`}>
                {chat.isGroup ? (
                   <>
                    <div className="bg-slate-300 rounded-sm" /> <div className="bg-slate-300 rounded-sm" />
                    <div className="bg-slate-300 rounded-sm" /> <div className="bg-slate-300 rounded-sm" />
                   </>
                ) : (
                  chat.avatar ? <img src={chat.avatar} className="w-full h-full object-cover" /> : <User size={24} className="text-slate-400" />
                )}
                {notifications.some(n => n.sender === chat.id) && (
                  <div className="absolute top-0 right-0 w-3.5 h-3.5 bg-rose-500 rounded-full border-2 border-white shadow-sm" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-baseline mb-1">
                  <span className="font-bold text-slate-800 text-[15px] truncate">{chat.nickName || chat.name}</span>
                  <span className="text-[10px] text-slate-400 font-medium">{chat.time || chat.lastTime || '刚刚'}</span>
                </div>
                <p className="text-xs text-slate-400 truncate font-medium">
                  {chat.messages?.[chat.messages.length - 1]?.message || chat.lastMsg}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );

  const renderContactsList = () => {
    // Exclude player name "陆陈安然" and filter roommates
    const allFriends = Array.from(new Set([...activeRoommates, ...Object.keys(affinity)]))
      .filter(name => name !== '陆陈安然');

    return (
      <div className="flex-1 flex flex-col bg-white animate-in fade-in duration-300">
        <div className="px-6 pt-12 pb-4 bg-[#ededed] shrink-0">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-bold text-slate-800">通讯录</h3>
            <Contact2 size={24} className="text-slate-400" />
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto custom-scrollbar divide-y divide-gray-50 pb-32">
          <div className="px-6 py-4 space-y-4">
            <div className="flex items-center gap-4 group cursor-pointer active:scale-95 transition-all">
              <div className="w-10 h-10 bg-orange-500 rounded-xl flex items-center justify-center text-white shadow-lg"><PlusCircle size={20} /></div>
              <span className="text-sm font-bold text-slate-700">新的朋友</span>
            </div>
            <div className="flex items-center gap-4 group cursor-pointer active:scale-95 transition-all">
              <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center text-white shadow-lg"><Users size={20} /></div>
              <span className="text-sm font-bold text-slate-700">群聊</span>
            </div>
          </div>

          <div className="bg-slate-50 px-6 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
            <ShieldEllipsis size={14} className="text-cyan-500" /> 好感度检测系统 / Relationships
          </div>

          {allFriends.map((name) => {
            const score = affinity[name] || 0;
            const level = score >= 80 ? 'EX' : score >= 60 ? 'A' : score >= 30 ? 'B' : 'C';
            const levelColor = score >= 80 ? 'text-amber-500' : score >= 60 ? 'text-emerald-500' : score >= 30 ? 'text-cyan-500' : 'text-slate-400';
            const info = getFriendInfo(name);

            return (
              <div key={name} className="flex items-center px-6 py-4 hover:bg-slate-50 transition-all group cursor-pointer" onClick={() => setActiveProfile({ name, score, level, info })}>
                  <div className="w-14 h-14 rounded-2xl bg-slate-100 shadow-sm overflow-hidden flex items-center justify-center mr-4 shrink-0 transition-transform group-hover:scale-105 border border-slate-200">
                     {info.avatar ? <img src={info.avatar} className="w-full h-full object-cover" /> : <User size={32} className="text-slate-400" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-black text-slate-800 text-[16px] tracking-tight truncate">{info.nickName || name}</span>
                      <span className={`text-[10px] font-black border border-current px-1.5 rounded-md shrink-0 ${levelColor}`}>{level}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-1.5">
                      <div className="flex gap-0.5 shrink-0">
                          {[...Array(5)].map((_, i) => (
                            <Heart key={i} size={11} fill={i < Math.floor(score / 20) ? '#f43f5e' : 'transparent'} className={i < Math.floor(score / 20) ? 'text-rose-500' : 'text-slate-200'} />
                          ))}
                      </div>
                      <div className="h-1 flex-1 bg-slate-100 rounded-full max-w-[60px] overflow-hidden">
                        <div className="h-full bg-rose-400" style={{ width: `${score}%` }} />
                      </div>
                      <span className="text-[10px] font-black text-slate-400 tabular-nums">VAL:{score}</span>
                    </div>
                  </div>
                  <ChevronRight size={18} className="text-slate-300 group-hover:translate-x-1 transition-transform" />
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderProfileDetail = (p: any) => (
    <div className="flex-1 flex flex-col bg-slate-50 animate-in slide-in-from-bottom-5 duration-500 z-[1200]">
      <div className="bg-white px-4 py-1 flex items-center shrink-0 border-b border-gray-100 pt-10">
        <button onClick={() => setActiveProfile(null)} className="p-2 text-slate-600 hover:text-emerald-600">
           <ChevronRight size={24} className="rotate-180" />
        </button>
        <div className="flex-1 text-center font-bold text-slate-800">详细资料</div>
        <div className="w-10" />
      </div>

      <div className="flex-1 py-8 space-y-4 overflow-y-auto custom-scrollbar">
        {/* Profile Card */}
        <div className="bg-white px-8 py-10 flex flex-col items-center">
          <div className="w-24 h-24 rounded-3xl bg-slate-100 shadow-xl overflow-hidden mb-6 border-4 border-white ring-1 ring-slate-100">
            {p.info.avatar ? <img src={p.info.avatar} className="w-full h-full object-cover" /> : <User size={48} className="text-slate-400" />}
          </div>
          <h4 className="text-2xl font-black text-slate-800 mb-1">{p.info.nickName || p.name}</h4>
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">@{p.name}</p>
          <div className="text-xs text-slate-500 font-medium text-center px-4 mb-6">“ {p.info.bio} ”</div>
          
          <div className="grid grid-cols-2 gap-4 w-full">
            <div className="bg-slate-50 p-4 rounded-3xl text-center">
               <Heart className="text-rose-500 mx-auto mb-1" size={20} fill="#f43f5e33" />
               <span className="text-[10px] font-black text-slate-400 uppercase block">Affinity</span>
               <span className="text-lg font-black text-slate-800">{p.score}</span>
            </div>
            <div className="bg-slate-50 p-4 rounded-3xl text-center">
               <Trophy className="text-amber-500 mx-auto mb-1" size={20} />
               <span className="text-[10px] font-black text-slate-400 uppercase block">Level</span>
               <span className="text-lg font-black text-slate-800">{p.level}</span>
            </div>
          </div>
        </div>

        <div className="bg-white divide-y divide-gray-50">
           <div className="px-8 py-5 flex justify-between items-center group cursor-pointer active:bg-slate-50">
              <span className="text-sm font-bold text-slate-700">更多信息</span>
              <ChevronRight size={18} className="text-slate-300" />
           </div>
           <div className="px-8 py-5 flex justify-between items-center group cursor-pointer active:bg-slate-50">
              <span className="text-sm font-bold text-slate-700">朋友圈</span>
              <div className="flex gap-2">
                 <div className="w-8 h-8 bg-slate-100 rounded-md" />
                 <ChevronRight size={18} className="text-slate-300 self-center" />
              </div>
           </div>
        </div>

        <div className="px-8 pt-4 space-y-3">
           <button 
              onClick={() => {
                const info = getFriendInfo(p.name);
                const chat = realConversations[p.name] || { id: p.name, name: p.name, nickName: info.nickName, avatar: info.avatar, messages: [], isGroup: false };
                setActiveChat(chat);
                setActiveProfile(null);
                setActiveTab('chats');
              }}
              className="w-full py-4 bg-emerald-500 text-white rounded-2xl font-bold text-md shadow-lg shadow-emerald-500/10 flex items-center justify-center gap-2"
            >
              <MessageSquare size={18} fill="white" /> 发送消息
            </button>
            <div className="grid grid-cols-2 gap-3">
               <button className="py-4 bg-white text-slate-700 border border-slate-100 rounded-2xl font-bold text-md flex items-center justify-center gap-2"><Phone size={18} /> 音频通话</button>
               <button className="py-4 bg-white text-slate-700 border border-slate-100 rounded-2xl font-bold text-md flex items-center justify-center gap-2"><Video size={18} /> 视频通话</button>
            </div>
        </div>
      </div>
    </div>
  );

  const renderActiveChat = (chat: any) => (
    <div className="flex-1 flex flex-col bg-[#ededed] animate-in slide-in-from-right duration-300">
      <div className="bg-[#ededed] px-4 py-1 flex items-center shrink-0 border-b border-gray-200/50 pt-10">
        <button onClick={() => setActiveChat(null)} className="p-2 text-slate-600 hover:text-emerald-600">
          <ChevronRight size={24} className="rotate-180" />
        </button>
        <div className="flex-1 text-center font-bold text-slate-800 text-[16px] truncate">
          {chat.nickName || chat.name} {chat.isGroup && `(${chat.messages.length})`}
        </div>
        <button className="p-2 text-slate-600" onClick={() => {
          if(!chat.isGroup) setActiveProfile({ name: chat.id, score: affinity[chat.id] || 0, level: 'C', info: getFriendInfo(chat.id) });
        }}><ShieldEllipsis size={24}/></button>
      </div>
      
      <div className="flex-1 p-4 overflow-y-auto custom-scrollbar flex flex-col space-y-6 pb-24">
        <div className="py-2 text-center"><span className="bg-slate-200/50 text-[9px] text-slate-400 font-black px-3 py-1 rounded-md uppercase tracking-[0.2em]">{chat.isGroup ? 'ROOM CHAT' : 'ENCRYPTED DIALOGUE'}</span></div>
        {chat.messages.length === 0 ? <div className="p-12 text-center text-slate-300 italic text-xs">协议已启用，等待数据同步...</div> :
          chat.messages.map((msg: any, idx: number) => {
            const isMe = msg.sender === '陆陈安然';
            return (
              <div key={idx} className={`flex items-start gap-3 w-full animate-in fade-in slide-in-from-bottom-2 duration-300 ${isMe ? 'flex-row-reverse' : ''}`} style={{ animationDelay: `${idx * 50}ms` }}>
                <div className={`w-9 h-9 rounded-lg shadow-sm flex items-center justify-center overflow-hidden shrink-0 ${isMe ? 'bg-cyan-500' : (chat.isGroup ? 'bg-slate-400' : 'bg-white')}`}>
                  {isMe ? <User size={20} className="text-white" /> : (chat.avatar ? <img src={chat.avatar} className="w-full h-full object-cover" /> : <User size={20} className="text-slate-400" />)}
                </div>
                <div className={`flex flex-col max-w-[70%] ${isMe ? 'items-end' : ''}`}>
                  {chat.isGroup && !isMe && <span className="text-[10px] text-slate-400 font-bold mb-1 ml-1">{msg.sender}</span>}
                  <div className={`px-4 py-2.5 rounded-2xl shadow-sm text-[14px] leading-relaxed relative ${isMe ? 'bg-emerald-500 text-white rounded-tr-none' : 'bg-white text-slate-800 rounded-tl-none border border-white/50'}`}>
                    {msg.message}
                  </div>
                </div>
              </div>
            );
          })
        }
        <div ref={messagesEndRef} />
      </div>
      <div className="bg-[#f7f7f7] border-t border-gray-200 p-4 pb-16 shrink-0">
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-white rounded-[6px] h-10 border border-gray-200" />
          <button className="min-w-[50px] h-10 rounded-[6px] bg-emerald-500 text-white font-black text-xs opacity-50 cursor-not-allowed">发送</button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col relative overflow-hidden bg-white">
      {activeProfile ? renderProfileDetail(activeProfile) : (
        activeChat ? renderActiveChat(activeChat) : (
          activeTab === 'chats' ? renderChatList() : renderContactsList()
        )
      )}
      {!activeChat && !activeProfile && (
        <div className="absolute bottom-0 inset-x-0 h-24 bg-[#f7f7f7]/95 backdrop-blur-md border-t border-gray-200 flex items-start justify-around z-[1100] pt-4 px-10">
          <button onClick={() => setActiveTab('chats')} className={`flex flex-col items-center gap-1 transition-colors ${activeTab === 'chats' ? 'text-emerald-500' : 'text-slate-400'}`}>
            <MessageSquare size={20} fill={activeTab === 'chats' ? 'currentColor' : 'transparent'} />
            <span className="text-[9px] font-black uppercase tracking-widest">微信</span>
          </button>
          <button onClick={() => setActiveTab('contacts')} className={`flex flex-col items-center gap-1 transition-colors ${activeTab === 'contacts' ? 'text-emerald-500' : 'text-slate-400'}`}>
            <Contact2 size={20} />
            <span className="text-[9px] font-black uppercase tracking-widest">通讯录</span>
          </button>
        </div>
      )}
    </div>
  );
};
