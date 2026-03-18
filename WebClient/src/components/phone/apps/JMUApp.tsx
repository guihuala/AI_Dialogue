import { GraduationCap, Trophy, BookOpen, LineChart } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface JMUAppProps {
  gpa: number;
  history: any[];
}

export const JMUApp = ({ gpa, history }: JMUAppProps) => {
  // Mock trend data or derived from history if possible
  const gpaTrend = history.map((h, i) => ({
    name: `T${h.turn}`,
    val: parseFloat((gpa - (Math.random() * 0.2)).toFixed(2)) // Simulating some variance for the chart
  })).slice(-10);

  return (
    <div className="flex-1 flex flex-col bg-white animate-in slide-in-from-right duration-500 overflow-hidden">
      <div className="bg-[#004b97] px-8 py-8 text-white shrink-0">
        <div className="flex justify-between items-start mb-6">
          <GraduationCap size={40} className="text-white/80" />
          <div className="text-[10px] font-black bg-white/20 px-3 py-1 rounded-full border border-white/20 uppercase tracking-widest">Student Portal</div>
        </div>
        <h3 className="text-2xl font-black tracking-tight mb-2">滨海大学 (JMU)</h3>
        <p className="text-white/60 text-xs font-bold">教务管理系统 - 学业看板</p>
      </div>
      
      <div className="flex-1 p-6 overflow-y-auto custom-scrollbar pb-32 bg-slate-50/50">
        <div className="bg-white rounded-[2.5rem] p-8 shadow-sm border border-slate-100 mb-6">
          <div className="flex justify-between items-center mb-8">
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Current Cumulative GPA</span>
            <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600"><Trophy size={20} /></div>
          </div>
          <div className="text-6xl font-black text-slate-800 tracking-tighter mb-4">{gpa.toFixed(2)}</div>
          <div className="text-xs font-bold text-emerald-500 flex items-center gap-1">
            <LineChart size={14} /> 绩点状态：优秀 (Rank A+)
          </div>
        </div>

        <div className="bg-white rounded-[2.5rem] p-6 shadow-sm border border-slate-100 mb-6 font-bold overflow-hidden">
          <h5 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-6 ml-2">成绩走势 / GPA Trend</h5>
          <div className="h-40 w-full pr-4">
             <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={gpaTrend}>
                  <defs>
                    <linearGradient id="colorGpa" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#004b97" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#004b97" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#94a3b8' }} />
                  <YAxis hide domain={[0, 4.0]} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '1rem', border: 'none', shadow: 'none', backgroundColor: '#0f172a', color: '#fff', fontSize: '10px' }}
                  />
                  <Area type="monotone" dataKey="val" stroke="#004b97" strokeWidth={3} fillOpacity={1} fill="url(#colorGpa)" />
                </AreaChart>
             </ResponsiveContainer>
          </div>
        </div>

        <div className="space-y-4">
          <h5 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 ml-2">学业变动记录 / Records</h5>
          {history.slice(-5).reverse().map((h, i) => (
             <div key={i} className="bg-white p-5 rounded-3xl border border-slate-100 flex items-center gap-4 transition-all hover:scale-[1.02]">
                <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center text-slate-400 shrink-0"><BookOpen size={24}/></div>
                <div className="flex-1">
                   <div className="text-xs font-black text-slate-800 line-clamp-1">{h.text.split('】: ')[1] || h.text}</div>
                   <div className="text-[10px] text-slate-400 mt-1 uppercase font-black">Turn {h.turn} • Academic Log</div>
                </div>
             </div>
          ))}
        </div>
      </div>
    </div>
  );
};
