import { CalendarDays, Clock3, Flag, Hourglass } from 'lucide-react';

interface HistoryEntry {
  turn: number;
  text: string;
  eventName?: string;
  currentScene?: string;
}

interface CalendarAppProps {
  chapter: number;
  turn: number;
  maxTurns: number;
  currentEventName?: string;
  currentScene?: string;
  history: HistoryEntry[];
}

export const CalendarApp = ({ chapter, turn, maxTurns, currentEventName, currentScene, history }: CalendarAppProps) => {
  const eventLogs = history.filter((item) => String(item.eventName || item.text || '').trim());
  const remainingTurns = Math.max(0, Number(maxTurns || 20) - Number(turn || 0));
  const currentStage = Math.max(1, Number(chapter || 1));

  return (
    <div className="flex-1 flex flex-col bg-slate-50 animate-in slide-in-from-right duration-500 overflow-hidden">
      <div className="bg-gradient-to-r from-amber-400 to-orange-500 px-7 py-8 text-white shrink-0">
        <div className="flex items-start justify-between mb-6">
          <CalendarDays size={30} />
        </div>
        <h3 className="text-2xl font-black tracking-tight">日历</h3>
      </div>

      <div className="grid grid-cols-2 gap-3 p-4 bg-white/88 border-b border-slate-100 shrink-0">
        <div className="rounded-[1.4rem] bg-orange-50 border border-orange-100 px-4 py-4">
          <div className="flex items-center gap-2 text-orange-500 text-[10px] font-black uppercase tracking-[0.22em]">
            <Flag size={14} /> 当前事件
          </div>
          <div className="mt-2 text-sm font-black text-slate-800 line-clamp-2">
            {currentEventName || '等待进入下一事件'}
          </div>
          <div className="mt-1 text-[11px] font-bold text-slate-500">{currentScene || '宿舍'}</div>
        </div>
        <div className="rounded-[1.4rem] bg-cyan-50 border border-cyan-100 px-4 py-4">
          <div className="flex items-center gap-2 text-cyan-600 text-[10px] font-black uppercase tracking-[0.22em]">
            <Hourglass size={14} /> 距离完成
          </div>
          <div className="mt-2 text-3xl font-black text-slate-800 tabular-nums">{remainingTurns}</div>
          <div className="mt-1 text-[11px] font-bold text-slate-500">还剩 {remainingTurns} 轮</div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 pb-28 space-y-3">
        {eventLogs.length === 0 ? (
          <div className="rounded-[1.8rem] bg-white border border-slate-200 px-5 py-10 text-center text-slate-400 text-sm font-bold">
            还没有可记录的事件。
          </div>
        ) : (
          eventLogs.slice().reverse().map((item, index) => (
            <div key={`${item.turn}-${index}`} className="rounded-[1.6rem] bg-white border border-cyan-100/80 px-5 py-5 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.24em] text-cyan-600">
                  <Clock3 size={13} /> Turn {item.turn}
                </div>
                <div className="text-[10px] font-black text-orange-500 bg-orange-50 border border-orange-100 px-2.5 py-1 rounded-full">
                  阶段 {currentStage}
                </div>
              </div>
              <div className="mt-3 text-base font-black text-slate-800">
                {item.eventName || '剧情推进'}
              </div>
              <div className="mt-1 text-[11px] font-bold text-slate-400">
                {item.currentScene || '宿舍'}
              </div>
              <div className="mt-3 text-[12px] font-bold text-slate-600 leading-relaxed line-clamp-3">
                {String(item.text || '').replace(/^【你的选择】:\s*/,'').trim()}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
