import { Settings, Cloud, BookOpen } from 'lucide-react';
import { useState, useEffect } from 'react';

interface TitleMenuProps {
    onStart: () => void;
    onWorkshop: () => void;
    onEditor: () => void;
    onSettings: () => void;
}

export const TitleMenu = ({ onStart, onWorkshop, onEditor, onSettings }: TitleMenuProps) => {
    const [currentTime, setCurrentTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => {
            clearInterval(timer);
        };
    }, []);

    const weekDays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
    const currentDay = weekDays[currentTime.getDay()];

    return (
        <div className="flex-1 flex flex-col items-center justify-center relative min-h-[500px] h-full w-full animate-fade-in group overflow-hidden rounded-[2.5rem] bg-[var(--color-cyan-light)]/30 border-2 border-[var(--color-cyan-main)]/20 shadow-[0_20px_50px_rgba(0,188,212,0.1)]">

            {/* Warm/Light Background Layer */}
            <div className="absolute inset-0 z-0">
                <div
                    className="absolute inset-0 bg-cover bg-center scale-105"
                    style={{
                        backgroundImage: "url('/assets/title_bg.png')",
                        animation: 'soft-float 20s ease-in-out infinite'
                    }}
                />
                {/* Light overlays */}
                <div className="absolute inset-0 bg-gradient-to-t from-[var(--color-cyan-light)]/80 via-transparent to-white/40" />
                <div className="absolute inset-0 backdrop-blur-[0.5px] bg-white/10 mix-blend-soft-light" />
            </div>

            {/* 2. Top Info Bar (Lifestyle focus - Cyan Palette) */}
            <div className="absolute top-10 left-10 right-10 z-20 flex justify-between items-start pointer-events-none">
                {/* Right: Date & Clock */}
                <div className="flex flex-col items-end gap-3 pointer-events-auto">
                    <div className="flex flex-col items-end px-5 py-3 glass-panel rounded-2xl border-white/60 shadow-sm">
                        <div className="flex items-baseline gap-2">
                            <span className="text-2xl font-black text-[var(--color-cyan-dark)] font-mono tracking-tighter">
                                {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            <span className="text-xs font-black text-[var(--color-cyan-main)]/80">{currentDay}</span>
                        </div>
                        <span className="text-[9px] font-black text-[var(--color-cyan-main)]/60 uppercase tracking-[0.2em] mt-1">
                            {currentTime.getFullYear()}年{currentTime.getMonth() + 1}月{currentTime.getDate()}日
                        </span>
                    </div>
                </div>
            </div>

            {/* Center Logo & Actions (Cyan + Yellow) */}
            <div className="relative z-10 flex flex-col items-center max-w-2xl w-full">
                <div className="text-center mb-16 space-y-8">
                    <div className="flex flex-col items-center">
                        <h1 className="flex flex-col items-center gap-2">
                            <span className="text-7xl md:text-8xl font-black text-[var(--color-cyan-dark)] tracking-tighter drop-shadow-sm">
                                UNIVERSITY
                            </span>
                            <span className="text-6xl md:text-7xl font-black text-[var(--color-yellow-main)] tracking-tight mt-[-0.5rem] flex items-center gap-4">
                                ARCHIVES
                            </span>
                        </h1>
                        <p className="mt-8 text-sm font-black text-[var(--color-cyan-main)]/60 tracking-[1em] uppercase">
                            大 学 档 案
                        </p>
                    </div>
                </div>

                <div className="flex flex-col space-y-10 w-80 animate-slide-up-fade" style={{ animationDelay: '0.2s' }}>
                    <button
                        onClick={onStart}
                        className="group relative px-6 py-10 bg-[var(--color-cyan-dark)] text-white rounded-[2.5rem] font-black tracking-[0.6em] uppercase transition-all shadow-2xl hover:-translate-y-2 active:translate-y-0 flex items-center justify-center text-2xl overflow-hidden hover:bg-[var(--color-cyan-main)]"
                    >
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-shimmer" />
                        开始宿舍生活
                    </button>

                    <div className="grid grid-cols-2 gap-5">
                        <button
                            onClick={onWorkshop}
                            className="flex flex-col items-center justify-center py-7 glass-panel hover:bg-white text-[var(--color-cyan-dark)] rounded-[2rem] transition-all group hover:-translate-y-1 shadow-sm border-white/60"
                        >
                            <Cloud className="mb-2 text-[var(--color-cyan-main)] group-hover:scale-110 transition-transform" size={24} />
                            <span className="text-[10px] font-black tracking-widest uppercase">编写模组</span>
                        </button>
                        <button
                            onClick={onEditor}
                            className="flex flex-col items-center justify-center py-7 glass-panel hover:bg-white text-[var(--color-cyan-dark)] rounded-[2rem] transition-all group hover:-translate-y-1 shadow-sm border-white/60"
                        >
                            <BookOpen className="mb-2 text-[var(--color-cyan-main)] group-hover:scale-110 transition-transform" size={24} />
                            <span className="text-[10px] font-black tracking-widest uppercase">创意工坊</span>
                        </button>
                    </div>

                    <button
                        onClick={onSettings}
                        className="self-center px-8 py-2.5 glass-panel text-[var(--color-cyan-main)]/60 hover:text-[var(--color-cyan-dark)] font-black text-[10px] tracking-[0.5em] uppercase transition-all flex items-center rounded-full hover:bg-white border-white/40 shadow-sm"
                    >
                        <Settings size={14} className="mr-3 group-hover:rotate-45 transition-transform" />
                        设置中心
                    </button>
                </div>
            </div>

            <div className="absolute bottom-2 font-black text-[10px] text-[var(--color-cyan-main)]/20 tracking-[1em] uppercase select-none z-20">
                Mokukeki 2026
            </div>
        </div>
    );
};

/* Internal Animation Helpers */
if (typeof document !== 'undefined' && !document.getElementById('title-menu-styles')) {
    const style = document.createElement('style');
    style.id = 'title-menu-styles';
    style.textContent = `
        @keyframes soft-float {
            0%, 100% { transform: scale(1.05) translate(0, 0); }
            50% { transform: scale(1.1) translate(-1%, -1%); }
        }
        .animate-spin-slow {
            animation: spin 12s linear infinite;
        }
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        @keyframes shimmer {
            from { transform: translateX(-100%); }
            to { transform: translateX(100%); }
        }
    `;
    document.head.appendChild(style);
}
