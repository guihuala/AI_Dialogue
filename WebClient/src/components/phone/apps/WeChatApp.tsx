import { ChevronLeft, MessageCircle, User } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

type WechatSession = {
  chat_name: string;
  messages: Array<{ sender: string; message: string }>;
};

interface WeChatAppProps {
  sessions: WechatSession[];
  notifications: any[];
  clearNotifications: () => void;
}

export const WeChatApp = ({ sessions, notifications, clearNotifications }: WeChatAppProps) => {
  const orderedSessions = useMemo(() => {
    return [...(sessions || [])]
      .filter((session) => String(session?.chat_name || '').trim())
      .sort((a, b) => (b.messages?.length || 0) - (a.messages?.length || 0));
  }, [sessions]);

  const [activeChat, setActiveChat] = useState<string>('');
  const hasAutoOpenedRef = useRef(false);

  useEffect(() => {
    if (notifications.length > 0) {
      clearNotifications();
    }
  }, [notifications.length, clearNotifications]);

  useEffect(() => {
    if (!orderedSessions.length) {
      setActiveChat('');
      return;
    }
    if (!hasAutoOpenedRef.current && !activeChat) {
      hasAutoOpenedRef.current = true;
      setActiveChat(orderedSessions[0].chat_name);
      return;
    }
    if (activeChat && !orderedSessions.some((session) => session.chat_name === activeChat)) {
      setActiveChat('');
    }
  }, [orderedSessions, activeChat]);

  const selectedSession = orderedSessions.find((session) => session.chat_name === activeChat) || null;

  if (!orderedSessions.length) {
    return (
      <div className="flex-1 flex flex-col bg-slate-50">
        <div className="px-6 pt-12 pb-4 bg-white/90 backdrop-blur-sm shrink-0 border-b border-slate-100">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-black text-slate-800 tracking-tight">微信</h3>
            <MessageCircle size={22} className="text-[#07C160]" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex bg-slate-50 overflow-hidden">
      {!selectedSession && (
        <div className="w-full flex flex-col bg-white/88 backdrop-blur-sm">
        <div className="px-5 pt-12 pb-4 border-b border-slate-100 shrink-0">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-black text-slate-800 tracking-tight">微信</h3>
            <MessageCircle size={22} className="text-[#07C160]" />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {orderedSessions.map((session) => {
            const lastMessage = session.messages?.[session.messages.length - 1];
            const isActive = session.chat_name === activeChat;
            return (
              <button
                key={session.chat_name}
                onClick={() => setActiveChat(session.chat_name)}
                className={`w-full flex items-center gap-3 px-5 py-4 text-left transition-colors border-b border-slate-100/80 ${
                  isActive ? 'bg-cyan-50/80' : 'hover:bg-slate-50'
                }`}
              >
                <div className="w-12 h-12 rounded-2xl bg-[#07C160]/12 text-[#07C160] flex items-center justify-center shrink-0">
                  <User size={22} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-black text-[15px] text-slate-800 truncate">{session.chat_name}</div>
                  <div className="mt-1 text-[12px] font-bold text-slate-500 truncate">
                    {lastMessage ? `${lastMessage.sender}：${lastMessage.message}` : '暂无消息'}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
        </div>
      )}

      {selectedSession && (
        <div className="flex-1 flex-col flex bg-[linear-gradient(180deg,#f8fffb_0%,#f4fbff_100%)]">
          <div className="px-4 pt-10 pb-3 border-b border-slate-200/70 bg-white/78 backdrop-blur-sm flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setActiveChat('')}
              className="w-9 h-9 rounded-full flex items-center justify-center text-slate-500 hover:bg-slate-100"
            >
              <ChevronLeft size={20} />
            </button>
            <div className="min-w-0">
              <div className="font-black text-[16px] text-slate-800 truncate">{selectedSession.chat_name}</div>
              <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">Chat</div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar px-4 py-5 space-y-3">
            {selectedSession.messages.map((msg, index) => {
              const isSelf = msg.sender === '你' || msg.sender === '我';
              return (
                <div
                  key={`${selectedSession.chat_name}-${index}`}
                  className={`flex ${isSelf ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[82%] rounded-[1.4rem] px-4 py-3 shadow-sm ${
                      isSelf
                        ? 'bg-[#95EC69] text-slate-800 rounded-br-md'
                        : 'bg-white text-slate-800 rounded-bl-md border border-slate-200/70'
                    }`}
                  >
                    {!isSelf && (
                      <div className="mb-1 text-[10px] font-black uppercase tracking-[0.14em] text-slate-400">
                        {msg.sender}
                      </div>
                    )}
                    <div className="text-[13px] font-bold leading-relaxed whitespace-pre-wrap break-words">
                      {msg.message}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
