import { GraduationCap, TrendingDown, TrendingUp } from 'lucide-react';

interface HistoryEntry {
  turn: number;
  text: string;
  gpa?: number;
  gpaDelta?: number;
  eventName?: string;
}

interface JMUAppProps {
  gpa: number;
  history: HistoryEntry[];
}

export const JMUApp = ({ gpa, history }: JMUAppProps) => {
  const gpaLogs = history
    .filter((item) => Math.abs(Number(item.gpaDelta || 0)) > 0.001)
    .slice()
    .reverse();

  return (
    <div className="flex-1 flex flex-col bg-slate-50 animate-in slide-in-from-right duration-500 overflow-hidden">
      <div className="bg-gradient-to-r from-cyan-600 to-blue-700 px-7 py-8 text-white shrink-0">
        <div className="flex items-start justify-between mb-6">
          <GraduationCap size={34} className="text-white/90" />
          <div className="text-[10px] font-black bg-white/20 px-3 py-1 rounded-full border border-white/20 uppercase tracking-widest">
            GPA Records
          </div>
        </div>
        <h3 className="text-2xl font-black tracking-tight">学工系统</h3>
      </div>

      <div className="p-4 bg-white/90 border-b border-slate-100 shrink-0">
        <div className="rounded-[1.5rem] bg-white border border-cyan-100 px-5 py-5 shadow-sm">
          <div className="text-[10px] font-black uppercase tracking-[0.22em] text-cyan-600">Current GPA</div>
          <div className="mt-2 text-5xl font-black tracking-tighter text-slate-800">{Number(gpa || 0).toFixed(2)}</div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 pb-28 space-y-3">
        {gpaLogs.length === 0 ? (
          <div className="rounded-[1.8rem] bg-white border border-slate-200 px-5 py-10 text-center text-slate-400 text-sm font-bold">
            目前还没有 GPA 变化记录。
          </div>
        ) : (
          gpaLogs.map((item, index) => {
            const delta = Number(item.gpaDelta || 0);
            const positive = delta > 0;
            return (
              <div key={`${item.turn}-${index}`} className="rounded-[1.6rem] bg-white border border-cyan-100/80 px-5 py-5 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">
                    Turn {item.turn}
                  </div>
                  <div className={`flex items-center gap-1 text-sm font-black ${positive ? 'text-emerald-500' : 'text-rose-500'}`}>
                    {positive ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                    {positive ? '+' : ''}{delta.toFixed(2)}
                  </div>
                </div>
                <div className="mt-3 text-base font-black text-slate-800">
                  {item.eventName || '学业变动'}
                </div>
                <div className="mt-2 text-[12px] font-bold text-slate-600 leading-relaxed line-clamp-3">
                  {String(item.text || '').replace(/^【你的选择】:\s*/,'').trim()}
                </div>
                <div className="mt-3 text-[11px] font-black text-slate-400">
                  当前绩点：{Number(item.gpa || 0).toFixed(2)}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
