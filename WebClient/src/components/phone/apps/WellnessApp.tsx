import { Brain, Activity, ShieldCheck, RefreshCw, ChevronRight } from 'lucide-react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';

interface WellnessAppProps {
  san: number;
}

export const WellnessApp = ({ san }: WellnessAppProps) => {
  const radarData = [
    { subject: '理智', A: san, fullMark: 100 },
    { subject: '意志', A: Math.max(san - 10, 0), fullMark: 100 },
    { subject: '专注', A: Math.min(san + 20, 100), fullMark: 100 },
    { subject: '情绪', A: Math.max(san - 5, 0), fullMark: 100 },
    { subject: '耐受', A: san, fullMark: 100 },
  ];

  return (
    <div className="flex-1 flex flex-col bg-slate-50 animate-in slide-in-from-right duration-500 overflow-hidden">
      <div className="bg-white px-8 py-10 border-b border-slate-100 shrink-0">
        <div className="flex items-center justify-between mb-8">
           <div className="w-10 h-10 bg-indigo-50 rounded-xl flex items-center justify-center text-indigo-500"><Brain size={24}/></div>
           <Activity size={20} className="text-indigo-200 animate-pulse" />
        </div>
        
        <div className="flex flex-col items-center">
            <div className="relative mb-6">
                <svg className="w-44 h-44 -rotate-90">
                    <circle cx="88" cy="88" r="80" className="stroke-slate-100 fill-none" strokeWidth="8" />
                    <circle 
                        cx="88" cy="88" r="80" 
                        className="stroke-indigo-500 fill-none transition-all duration-1000 ease-out" 
                        strokeWidth="8" 
                        strokeDasharray={2 * Math.PI * 80} 
                        strokeDashoffset={2 * Math.PI * 80 * (1 - san / 100)} 
                        strokeLinecap="round" 
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center rotate-90">
                    <span className="text-5xl font-black tracking-tighter tabular-nums text-slate-800">{san}</span>
                    <span className="text-[10px] font-black tracking-[0.2em] text-slate-400 uppercase mt-[-4px]">SANITY</span>
                </div>
            </div>
            <div className="text-[10px] font-black text-slate-400 border border-slate-200 px-4 py-1.5 rounded-full uppercase tracking-widest flex items-center gap-2 bg-white">
                <ShieldCheck size={14} className="text-indigo-500" /> Mental Status OK
            </div>
        </div>
      </div>
      
      <div className="flex-1 p-6 overflow-y-auto custom-scrollbar pb-32">
        <div className="bg-white p-6 rounded-[2.5rem] border border-slate-100 shadow-sm mb-6 overflow-hidden relative">
          <h5 className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 mb-8 flex justify-center">Cognitive Analysis</h5>
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                <PolarGrid stroke="#f1f5f9" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 700 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar 
                    name="Status" 
                    dataKey="A" 
                    stroke="#6366f1" 
                    fill="#818cf8" 
                    fillOpacity={0.3} 
                    animationDuration={1500} 
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white p-6 rounded-3xl border border-slate-100 flex items-center justify-between group cursor-pointer active:scale-95 transition-all shadow-sm">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-500"><RefreshCw size={24}/></div>
            <div>
              <div className="text-sm font-bold text-slate-800">心理调节</div>
              <div className="text-[10px] font-medium text-slate-400 uppercase tracking-widest mt-0.5">Therapy Session</div>
            </div>
          </div>
          <ChevronRight size={20} className="text-slate-300" />
        </div>
      </div>
    </div>
  );
};
