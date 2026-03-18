import { Settings, Cloud, BookOpen, Coffee, Sun, Heart, Newspaper, Home } from 'lucide-react';
import { useState, useEffect } from 'react';

interface TitleMenuProps {
    onStart: () => void;
    onWorkshop: () => void;
    onEditor: () => void;
    onSettings: () => void;
}

export const TitleMenu = ({ onStart, onWorkshop, onEditor, onSettings }: TitleMenuProps) => {
    const [currentTime, setCurrentTime] = useState(new Date());
    const [newsIndex, setNewsIndex] = useState(0);

    const newsItems = [
        "今天的宿舍阿姨心情不错，也许会有额外的热水供应？",
        "楼下的野猫又在向路过的同学讨食了，记得带点猫粮。",
        "图书馆的座位还是那么难抢，记得早起出征。",
        "创意工坊的同学们分享了许多有趣的新故事，去看看吧。",
        "南区食堂的红烧肉今天限量供应，先到先得！"
    ];

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        const newsTimer = setInterval(() => setNewsIndex(prev => (prev + 1) % newsItems.length), 6000);
        return () => {
            clearInterval(timer);
            clearInterval(newsTimer);
        };
    }, []);

    const weekDays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
    const currentDay = weekDays[currentTime.getDay()];

    return (
        <div className="flex-1 flex flex-col items-center justify-center relative min-h-[500px] h-full w-full animate-fade-in group overflow-hidden rounded-[2.5rem] bg-[var(--color-cyan-light)]/30 border-2 border-[var(--color-cyan-main)]/20 shadow-[0_20px_50px_rgba(0,188,212,0.1)]">
            
            {/* 1. Warm/Light Background Layer */}
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
                {/* Left: Academic/Weather Info */}
                <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-4 px-5 py-3 glass-panel rounded-2xl pointer-events-auto border-white/60 shadow-sm">
                        <Sun size={18} className="text-[var(--color-cyan-main)] animate-spin-slow" />
                        <div className="flex flex-col">
                            <span className="text-[11px] font-black text-[var(--color-cyan-dark)] uppercase tracking-widest">
                                今日天气：晴朗
                            </span>
                            <span className="text-[9px] font-bold text-[var(--color-cyan-main)]/60 mt-0.5">
                                适合在阳台晾晒被褥
                            </span>
                        </div>
                    </div>
                </div>

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

            {/* 3. Students' Notice Board (Left Side - Cyan style) */}
            <div className="absolute left-10 bottom-12 z-20 hidden xl:flex flex-col gap-5 w-72 pointer-events-none animate-slide-up-fade">
                <div className="flex items-center gap-3 text-[var(--color-cyan-dark)]/60 mb-1 ml-2">
                    <Newspaper size={20} className="text-[var(--color-cyan-main)]" />
                    <span className="text-[11px] font-black uppercase tracking-[0.4em]">校园杂谈</span>
                </div>
                <div className="relative h-24">
                    {newsItems.map((news, idx) => (
                        <div 
                            key={idx}
                            className={`absolute inset-0 text-sm p-5 rounded-[2rem] glass-panel transition-all duration-1000 border-white/60 ${idx === newsIndex ? 'opacity-100 translate-y-0 scale-100 shadow-xl' : 'opacity-0 translate-y-4 scale-95 pointer-events-none'}`}
                        >
                            <p className="font-bold text-[var(--color-cyan-dark)] leading-relaxed italic">
                                “ {news} ”
                            </p>
                        </div>
                    ))}
                </div>
            </div>

            {/* 4. Center Logo & Actions (Cyan + Yellow) */}
            <div className="relative z-10 flex flex-col items-center max-w-2xl w-full">
                <div className="text-center mb-16 space-y-8">
                    <div className="flex flex-col items-center">
                        <div className="w-16 h-[2px] bg-[var(--color-cyan-main)] mb-6" />
                        <h1 className="flex flex-col items-center gap-2">
                            <span className="text-7xl md:text-8xl font-black text-[var(--color-cyan-dark)] tracking-tighter drop-shadow-sm">
                                ROOMMATE
                            </span>
                            <span className="text-6xl md:text-7xl font-black text-[var(--color-yellow-main)] tracking-tight mt-[-0.5rem] flex items-center gap-4">
                                <Heart className="fill-[var(--color-yellow-main)] animate-pulse shadow-sm" size={40} />
                                SURVIVAL
                                <Heart className="fill-[var(--color-yellow-main)] animate-pulse shadow-sm" size={40} />
                            </span>
                        </h1>
                        <p className="mt-8 text-sm font-black text-[var(--color-cyan-main)]/60 tracking-[1em] uppercase">
                            日常 // 生活 // 陪伴
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
                            <span className="text-[10px] font-black tracking-widest uppercase">灵感空间</span>
                        </button>
                        <button
                            onClick={onEditor}
                            className="flex flex-col items-center justify-center py-7 glass-panel hover:bg-white text-[var(--color-cyan-dark)] rounded-[2rem] transition-all group hover:-translate-y-1 shadow-sm border-white/60"
                        >
                            <BookOpen className="mb-2 text-[var(--color-cyan-main)] group-hover:scale-110 transition-transform" size={24} />
                            <span className="text-[10px] font-black tracking-widest uppercase">剧本工坊</span>
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

            {/* 5. Cozy Status Overlays (Right Side) */}
            <div className="absolute right-10 bottom-12 z-20 flex flex-col items-end gap-4 pointer-events-none hidden md:flex">
                <div className="px-6 py-4 glass-panel rounded-3xl border-white/60 shadow-lg animate-float flex items-center gap-4">
                    <Coffee className="text-[var(--color-cyan-main)]" size={24} />
                    <div className="flex flex-col">
                        <span className="text-[11px] font-black text-[var(--color-cyan-dark)]">想喝杯咖啡吗？</span>
                        <span className="text-[9px] font-bold text-[var(--color-cyan-main)]/60 uppercase tracking-widest mt-0.5">Take a break</span>
                    </div>
                </div>
                
                <div className="flex items-center gap-4 px-6 py-3 glass-panel rounded-full border-white/60 shadow-sm">
                    <Home size={18} className="text-[var(--color-cyan-main)]" />
                    <span className="text-[10px] font-black text-[var(--color-cyan-dark)]/60 uppercase tracking-[0.3em]">南区 404 宿舍</span>
                </div>
            </div>

            <div className="absolute bottom-8 font-black text-[10px] text-[var(--color-cyan-main)]/20 tracking-[1em] uppercase select-none z-20">
                Memories // 2026 Archive
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
