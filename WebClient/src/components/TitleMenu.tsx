import { Play, Settings, Cloud, BookOpen } from 'lucide-react';

interface TitleMenuProps {
    onStart: () => void;
    onWorkshop: () => void;
    onEditor: () => void;
    onSettings: () => void;
}

export const TitleMenu = ({ onStart, onWorkshop, onEditor, onSettings }: TitleMenuProps) => {
    return (
        <div className="flex-1 flex flex-col items-center justify-center relative min-h-[600px] w-full animate-fade-in group">
            {/* Decorative Background Elements */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] bg-[radial-gradient(circle_at_center,var(--color-cyan-main)_0%,transparent_70%)] opacity-[0.05] animate-pulse pointer-events-none" />
            
            {/* Title Area */}
            <div className="relative z-10 text-center mb-16 space-y-4">
                <div className="inline-flex items-center px-4 py-1 bg-white/60 border border-[var(--color-cyan-main)]/20 text-[var(--color-cyan-dark)] text-[10px] font-black tracking-[0.4em] uppercase mb-4 rounded-lg shadow-sm backdrop-blur-sm">
                    Experimental AI Simulation v2.0
                </div>
                
                <h1 className="text-8xl md:text-9xl font-black text-[var(--color-cyan-dark)] tracking-tighter leading-none relative group-hover:drop-shadow-[0_0_25px_rgba(0,188,212,0.3)] transition-all">
                    ROOMMATE<br/>
                    <span className="text-[var(--color-yellow-main)] drop-shadow-sm flex items-center justify-center gap-4">
                        SURVIVAL
                    </span>
                </h1>
                
                <div className="flex items-center justify-center space-x-6 pt-4">
                    <div className="h-[2px] w-16 bg-gradient-to-r from-transparent to-[var(--color-cyan-main)]/40" />
                    <p className="text-sm font-black text-[var(--color-cyan-dark)] tracking-[0.6em] uppercase">
                        南区宿舍 · 404号对局
                    </p>
                    <div className="h-[2px] w-16 bg-gradient-to-l from-transparent to-[var(--color-cyan-main)]/40" />
                </div>
            </div>

            {/* Main Menu Actions */}
            <div className="relative z-10 flex flex-col space-y-6 w-96">
                <button 
                    onClick={onStart}
                    className="group relative px-8 py-7 bg-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] text-white rounded-3xl font-black tracking-[0.5em] uppercase transition-all shadow-2xl shadow-cyan-900/20 hover:-translate-y-1 active:translate-y-0 flex items-center justify-center text-2xl overflow-hidden"
                >
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-shimmer" />
                    <Play className="mr-6 fill-white group-hover:scale-125 transition-transform" size={28} />
                    进入宿舍
                </button>

                <div className="grid grid-cols-2 gap-6">
                    <button 
                        onClick={onWorkshop}
                        className="flex flex-col items-center justify-center py-6 bg-white/60 backdrop-blur-md border-2 border-[var(--color-cyan-main)]/10 text-[var(--color-cyan-dark)] rounded-3xl hover:bg-white hover:border-[var(--color-cyan-main)] transition-all group shadow-sm hover:shadow-lg"
                    >
                        <Cloud className="mb-2 text-[var(--color-cyan-main)] group-hover:scale-110 group-hover:rotate-12 transition-transform" size={24} />
                        <span className="text-[10px] font-black tracking-widest uppercase text-center">创意工坊</span>
                    </button>
                    <button 
                        onClick={onEditor}
                        className="flex flex-col items-center justify-center py-6 bg-white/60 backdrop-blur-md border-2 border-[var(--color-cyan-main)]/10 text-[var(--color-cyan-dark)] rounded-3xl hover:bg-white hover:border-[var(--color-cyan-main)] transition-all group shadow-sm hover:shadow-lg"
                    >
                        <BookOpen className="mb-2 text-[var(--color-cyan-main)] group-hover:scale-110 group-hover:-rotate-12 transition-transform" size={24} />
                        <span className="text-[10px] font-black tracking-widest uppercase text-center">剧本编辑</span>
                    </button>
                </div>

                <div className="group">
                    <button 
                        onClick={onSettings}
                        className="w-full py-2 text-[var(--color-cyan-dark)]/30 hover:text-[var(--color-cyan-main)] font-black text-[10px] tracking-[0.4em] uppercase transition-all flex items-center justify-center group-hover:scale-105"
                    >
                        <Settings size={14} className="mr-2 group-hover:rotate-90 transition-transform" />
                        系统架构配置
                    </button>
                </div>
            </div>

            {/* Bottom Credit */}
            <div className="absolute bottom-4 font-black text-[9px] text-[var(--color-cyan-main)]/20 tracking-[1em] uppercase select-none">
                Antigravity Core // Deep Reality // 2026
            </div>
        </div>
    );
};
