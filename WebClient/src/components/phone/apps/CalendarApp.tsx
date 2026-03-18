import { Calendar, Clock } from 'lucide-react';

interface CalendarAppProps {
  chapter: number;
  turn: number;
  history: any[];
}

export const CalendarApp = ({ chapter, turn, history }: CalendarAppProps) => {
  return (
    <div className="flex-1 flex flex-col bg-slate-50 animate-in slide-in-from-right duration-500">
      <div className="bg-white px-8 py-7 border-b border-slate-100 flex items-center shrink-0">
        <h3 className="font-black text-slate-800 flex items-center tracking-tight text-lg">
          <Calendar size={22} className="mr-3 text-orange-500" /> 日历行程
        </h3>
      </div>
      
      <div className="flex-1 p-8 overflow-y-auto custom-scrollbar space-y-10 pb-24">
        {/* Current Status Card */}
        <div className="bg-gradient-to-br from-orange-400 to-pink-500 text-white p-8 rounded-[3rem] shadow-[0_20px_40px_rgba(249,115,22,0.2)] mb-12 relative overflow-hidden group hover:scale-[1.02] transition-transform duration-500">
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-10 -mt-10 blur-2xl group-hover:scale-150 transition-transform duration-1000" />
          <div className="relative z-10">
            <div className="text-5xl font-black mb-2 tracking-tighter">CH.{chapter}</div>
            <div className="text-[10px] font-black tracking-[0.4em] opacity-80 uppercase italic">Chapter Sequence</div>
            <div className="mt-8 flex items-center text-sm font-black bg-white/20 backdrop-blur-md px-5 py-2.5 rounded-full w-fit border border-white/20">
              <Clock size={16} className="mr-3 animate-pulse" /> 当前进度: 第 {turn} 回合
            </div>
          </div>
        </div>

        <div>
          <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.5em] mb-8 ml-2">Timeline Archive</h4>
          <div className="space-y-6">
            {history.slice(-15).reverse().map((h, i) => (
              <div key={i} className="flex space-x-6 group animate-in fade-in slide-in-from-bottom-4 duration-500" style={{ animationDelay: `${i * 100}ms` }}>
                <div className="flex flex-col items-center shrink-0 pt-1">
                  <div className="w-10 h-10 rounded-[1.2rem] bg-white text-orange-500 flex items-center justify-center text-[10px] font-black border border-slate-100 shadow-sm group-hover:bg-orange-50 group-hover:border-orange-200 transition-colors">
                    T{h.turn}
                  </div>
                  <div className="flex-1 w-[2px] bg-slate-200 group-last:hidden py-4 my-2 rounded-full" />
                </div>
                <div className="flex-1 bg-white p-5 rounded-[2.2rem] border border-slate-100 text-[11px] font-bold text-slate-600 leading-relaxed shadow-sm group-hover:shadow-md transition-shadow">
                  {h.text.split('\n')[0]}
                  <div className="mt-2 text-[9px] text-slate-300 uppercase tracking-widest font-black">Archive Complete</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
