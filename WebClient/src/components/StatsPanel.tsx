import { useGameStore } from '../store/gameStore';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';

export const StatsPanel = () => {
  const { san, money, hygiene, reputation, gpa, chapter, turn, current_evt_id } = useGameStore();

  // Normalize data for the radar chart (0-100 scale)
  const data = [
    { subject: '理智', value: san, actual: san, fullMark: 100 },
    { subject: '整洁', value: hygiene, actual: hygiene, fullMark: 100 },
    { subject: '声望', value: reputation, actual: reputation, fullMark: 100 },
    { subject: '学分', value: Math.min(gpa * 25, 100), actual: gpa.toFixed(1), fullMark: 100 }, // Assuming max GPA is 4.0
    { subject: '资金', value: Math.min(money / 10, 100), actual: money, fullMark: 100 }, // Assuming 1000 is a "full" chart
  ];

  /* eslint-disable @typescript-eslint/no-explicit-any */
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-black/80 border border-[var(--color-cyan-main)]/50 p-2 rounded-lg backdrop-blur-sm z-50">
          <p className="text-[var(--color-cyan-main)] font-black text-xs uppercase tracking-widest">{payload[0].payload.subject}</p>
          <p className="text-white font-bold text-sm">{payload[0].payload.actual}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="absolute left-4 bottom-4 md:left-8 md:bottom-8 z-20 flex flex-col space-y-3 w-64 md:w-72 shrink-0 animate-fade-in-up">
      <div className="glass-panel p-4 md:p-6 rounded-2xl border-2 border-[var(--color-cyan-main)]/20 shadow-lg bg-white/80 backdrop-blur-md relative z-10">
        <h3 className="text-sm font-black text-[var(--color-cyan-main)] mb-2 tracking-widest uppercase">状态雷达</h3>
        
        <div className="h-48 w-full -ml-2">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius="65%" data={data}>
              <PolarGrid stroke="var(--color-cyan-main)" strokeOpacity={0.3} />
              <PolarAngleAxis 
                dataKey="subject" 
                tick={{ fill: 'var(--color-cyan-dark)', fontSize: 11, fontWeight: 900 }} 
              />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Radar
                name="状态"
                dataKey="value"
                stroke="var(--color-cyan-main)"
                strokeWidth={2}
                fill="var(--color-cyan-main)"
                fillOpacity={0.4}
                activeDot={{ r: 4, fill: 'var(--color-yellow-main)', stroke: 'white' }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
        
        {/* 紧凑版数值显示 */}
        <div className="grid grid-cols-2 gap-2 mt-2">
            <div className="bg-white/90 px-2 py-1.5 rounded-lg border border-[var(--color-cyan-light)] shadow-sm flex flex-col items-center">
                <span className="text-[10px] text-[var(--color-cyan-dark)]/70 font-black tracking-widest uppercase">SAN</span>
                <span className={`text-sm font-black ${san < 50 ? 'text-red-500' : 'text-[var(--color-cyan-main)]'}`}>{san}</span>
            </div>
            <div className="bg-white/90 px-2 py-1.5 rounded-lg border border-[var(--color-cyan-light)] shadow-sm flex flex-col items-center">
                <span className="text-[10px] text-[var(--color-cyan-dark)]/70 font-black tracking-widest uppercase">¥</span>
                <span className="text-sm font-black text-cyan-500">{money}</span>
            </div>
            <div className="bg-white/90 px-2 py-1.5 rounded-lg border border-[var(--color-cyan-light)] shadow-sm flex flex-col items-center">
                <span className="text-[10px] text-[var(--color-cyan-dark)]/70 font-black tracking-widest uppercase">GPA</span>
                <span className="text-sm font-black text-[var(--color-yellow-main)] drop-shadow-sm">{gpa.toFixed(1)}</span>
            </div>
            <div className="bg-white/90 px-2 py-1.5 rounded-lg border border-[var(--color-cyan-light)] shadow-sm flex flex-col items-center">
                <span className="text-[10px] text-[var(--color-cyan-dark)]/70 font-black tracking-widest uppercase">声望</span>
                <span className="text-sm font-black text-orange-500">{reputation}</span>
            </div>
        </div>
      </div>

      <div className="glass-panel p-4 rounded-xl border-2 border-[var(--color-cyan-main)]/20 shadow-lg bg-white/80 backdrop-blur-md flex flex-col">
        <h3 className="text-xs font-black text-[var(--color-cyan-main)] mb-2 tracking-widest uppercase">当前进度</h3>
        <div className="space-y-1 mt-1 text-xs text-[var(--color-cyan-dark)]/90 tracking-wide">
          <div className="flex justify-between items-center">
            <span className="font-black">章节回合:</span>
            <span className="font-mono font-bold bg-[var(--color-cyan-light)] px-2 py-0.5 rounded-md">Ch.{chapter} | T.{turn}</span>
          </div>
          <div className="flex justify-between items-center mt-1">
            <span className="font-black">事件ID:</span>
            <span className="bg-[var(--color-yellow-light)] text-[var(--color-cyan-dark)] px-2 py-0.5 rounded-md border border-[var(--color-yellow-main)]/30 font-mono text-[10px] font-bold w-full text-right ml-2 truncate">{current_evt_id || '等待中...'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
