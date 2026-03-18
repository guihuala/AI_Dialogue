import { Calendar as CalendarIcon, Clock, ChevronRight, MapPin, Star } from 'lucide-react';
import { useState } from 'react';

interface CalendarAppProps {
  chapter: number;
  turn: number;
  history: any[];
}

export const CalendarApp = ({ chapter, turn, history }: CalendarAppProps) => {
  const years = ["大一", "大二", "大三", "大四"];
  const currentYearIndex = Math.min(Math.floor((chapter - 1) / 2), 3); // Simple mapping
  const [activeYearTab, setActiveYearTab] = useState(currentYearIndex);

  // Derive "Events" from history by filtering for specific formatting or length
  const events = history.filter(h => h.text.length > 50 || h.text.includes('【'));

  return (
    <div className="flex-1 flex flex-col bg-white animate-in slide-in-from-right duration-500 overflow-hidden">
      {/* Header */}
      <div className="bg-[#FF9500] px-8 py-8 text-white shrink-0">
        <div className="flex justify-between items-start mb-6">
          <CalendarIcon size={32} />
          <div className="flex flex-col items-end">
             <div className="text-[10px] font-black bg-white/20 px-3 py-1 rounded-full border border-white/20 uppercase tracking-widest mb-1">Timeline v2.1</div>
             <div className="text-xl font-black">2026/03/18 周三</div>
          </div>
        </div>
        <h3 className="text-2xl font-black tracking-tight mb-1">学年成长日历</h3>
        <p className="text-white/60 text-xs font-bold flex items-center gap-1">
          <Clock size={12} /> 当前累计推进: {turn} 个阶段
        </p>
      </div>

      {/* Academic Year Tabs - Shrunk to fit */}
      <div className="bg-slate-50 border-b border-slate-100 flex p-3 shrink-0 gap-2 justify-center">
        {years.map((name, i) => (
          <button 
            key={i} 
            onClick={() => setActiveYearTab(i)}
            className={`flex-1 max-w-[80px] py-2 rounded-xl text-[10px] font-black tracking-tighter transition-all border ${i === activeYearTab ? 'bg-[#FF9500] text-white border-[#FF9500] shadow-md shadow-orange-500/10' : 'bg-white text-slate-400 border-slate-200'}`}
          >
            {name}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-6 pb-32">
        {/* Semester Overview Summary */}
        <div className="bg-white rounded-[2.5rem] p-6 border border-slate-100 shadow-sm mb-10 flex items-center justify-between">
            <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-orange-50 text-[#FF9500] rounded-[1.2rem] flex flex-col items-center justify-center border border-orange-100">
                    <span className="text-[10px] font-black uppercase">YEAR</span>
                    <span className="text-xl font-black">{activeYearTab + 1}</span>
                </div>
                <div>
                   <div className="text-sm font-black text-slate-800">{years[activeYearTab]}</div>
                   <div className="text-[10px] font-bold text-slate-400 mt-0.5">滨海大学 2024 级</div>
                </div>
            </div>
            {activeYearTab === currentYearIndex && (
               <div className="text-orange-500 font-black text-[10px] bg-orange-50 px-3 py-1 rounded-full animate-pulse border border-orange-100">
                  当前学年
               </div>
            )}
        </div>

        {/* Milestone Timeline */}
        <div className="relative pl-12 space-y-12 pb-10">
          <div className="absolute left-[23px] top-2 bottom-0 w-1.5 bg-slate-100 rounded-full" />
          
          {/* Milestone Items */}
          {events.length === 0 ? (
            <div className="p-12 text-center opacity-20 italic text-slate-400">
               本学期暂无重要事件记录
            </div>
          ) : (
            events.slice(-20).reverse().map((ev, idx) => (
              <div key={idx} className="relative group animate-in slide-in-from-left-4 duration-500" style={{ animationDelay: `${idx * 100}ms` }}>
                {/* Pointer Dot */}
                <div className={`absolute -left-[14px] top-2 w-6 h-6 rounded-full border-4 border-white shadow-md flex items-center justify-center transition-all group-hover:scale-125 ${idx === 0 ? 'bg-orange-500' : 'bg-slate-300'}`}>
                   {idx === 0 && <Star size={10} className="text-white fill-white" />}
                </div>
                
                {/* Info Card */}
                <div className="bg-white p-5 rounded-[2.2rem] border border-slate-100 shadow-sm transition-all group-hover:shadow-md group-hover:ring-1 group-hover:ring-orange-200">
                   <div className="flex justify-between items-center mb-3">
                      <div className="text-[10px] font-black text-[#FF9500] uppercase tracking-widest bg-orange-50 px-2.5 py-1 rounded-md">阶段 {ev.turn}</div>
                      <MapPin size={14} className="text-slate-300" />
                   </div>
                   <p className="text-xs font-bold text-slate-700 leading-relaxed mb-4">
                     {ev.text.split('】: ')[1] || ev.text}
                   </p>
                   <div className="h-px bg-slate-50 w-full mb-4" />
                   <div className="flex items-center justify-end gap-2 text-[9px] font-black text-slate-400 uppercase tracking-[0.2em]">
                      Status: Logged <ChevronRight size={10} />
                   </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
