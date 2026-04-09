import { Settings, Cloud, BookOpen, Bell } from 'lucide-react';

interface TitleMenuProps {
    onStart: () => void;
    onWorkshop: () => void;
    onEditor: () => void;
    onSettings: () => void;
    onAnnouncement: () => void;
}

export const TitleMenu = ({ onStart, onWorkshop, onEditor, onSettings, onAnnouncement }: TitleMenuProps) => {
    return (
        <div className="flex-1 flex flex-col items-center justify-center relative min-h-[420px] md:min-h-[500px] h-full w-full animate-fade-in group overflow-hidden bg-[var(--color-cyan-light)]/35">

            {/* Warm/Light Background Layer */}
            <div className="absolute inset-0 z-0">
                {/* Scrolling texture (below protagonist cover) */}
                <div className="absolute inset-0 opacity-[0.5] pointer-events-none">
                    <div
                        className="absolute inset-0 animate-texture-scroll"
                        style={{
                            backgroundImage: "repeating-linear-gradient(135deg, rgba(0,188,212,0.22) 0 8px, rgba(0,188,212,0) 8px 30px)",
                            backgroundSize: "43px 43px",
                        }}
                    />
                </div>
                <div className="absolute inset-0 md:inset-10">
                    <img
                        src="/assets/cover/cover_01.webp"
                        alt=""
                        className="absolute inset-0 w-full h-full object-contain opacity-55 md:opacity-100"
                        style={{ objectPosition: "92% bottom" }}
                    />
                    <img
                        src="/assets/cover/cover_02.webp"
                        alt=""
                        className="absolute inset-0 w-full h-full object-contain opacity-55 md:opacity-100"
                        style={{ objectPosition: "92% bottom" }}
                    />
                </div>
                {/* Light overlays */}
                <div className="absolute inset-0 bg-gradient-to-t from-[var(--color-cyan-light)]/80 via-transparent to-white/40" />
                <div className="absolute inset-0 backdrop-blur-[0.5px] bg-white/10 mix-blend-soft-light" />

                {/* Floating roommate placeholders (6 cards) */}

            </div>

            {/* Center Logo & Actions (Cyan + Yellow) */}
            <div className="relative z-10 flex flex-col items-center md:items-start max-w-2xl w-full px-5 md:px-0 mr-auto ml-0 md:ml-[8%] py-8 md:py-10">
                <div className="text-center md:text-left mb-8 md:mb-14 space-y-6 md:space-y-8">
                    <div className="flex flex-col items-start">
                        <h1 className="flex flex-col items-center md:items-start gap-2">
                            <span className="text-5xl sm:text-6xl md:text-8xl font-black text-[var(--color-cyan-dark)] tracking-tighter drop-shadow-sm leading-none">
                                UNIVERSITY
                            </span>
                            <span className="text-4xl sm:text-5xl md:text-7xl font-black text-[var(--color-yellow-main)] tracking-tight mt-[-0.15rem] md:mt-[-0.5rem] flex items-center gap-4 leading-none">
                                ARCHIVES
                            </span>
                        </h1>
                    </div>
                </div>

                <div className="flex flex-col items-center md:items-stretch space-y-5 md:space-y-8 w-full max-w-[20rem] animate-slide-up-fade" style={{ animationDelay: '0.2s' }}>
                    <button
                        onClick={onStart}
                        className="group relative w-full px-6 py-5 md:py-8 bg-[var(--color-cyan-dark)] text-white rounded-[1.6rem] md:rounded-[2rem] font-black transition-all duration-300 shadow-2xl hover:bg-[var(--color-cyan-main)] hover:shadow-[0_22px_40px_rgba(0,129,201,0.22)] active:scale-[0.99] flex items-center justify-center text-xl md:text-2xl overflow-hidden"
                    >
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-shimmer" />
                        开始游戏
                    </button>

                    <div className="grid w-full grid-cols-2 gap-3 md:gap-4">
                        <button
                            onClick={onWorkshop}
                            className="flex flex-col items-center justify-center gap-2 py-4 md:py-6 bg-white/78 hover:bg-white text-[var(--color-cyan-dark)] rounded-[1.25rem] md:rounded-[1.6rem] transition-all duration-300 group border border-white/70 hover:shadow-[0_16px_34px_rgba(255,255,255,0.32)] active:scale-[0.99]"
                        >
                            <Cloud className="text-[var(--color-cyan-main)] group-hover:scale-110 transition-transform" size={24} />
                            <span className="text-xs md:text-sm font-black">创意工坊</span>
                        </button>
                        <button
                            onClick={onEditor}
                            className="flex flex-col items-center justify-center gap-2 py-4 md:py-6 bg-white/78 hover:bg-white text-[var(--color-cyan-dark)] rounded-[1.25rem] md:rounded-[1.6rem] transition-all duration-300 group border border-white/70 hover:shadow-[0_16px_34px_rgba(255,255,255,0.32)] active:scale-[0.99]"
                        >
                            <BookOpen className="text-[var(--color-cyan-main)] group-hover:scale-110 transition-transform" size={24} />
                            <span className="text-xs md:text-sm font-black">模组编辑</span>
                        </button>
                    </div>

                    <div className="self-center md:self-start flex flex-wrap items-center justify-center md:justify-start gap-3">
                        <button
                            onClick={onAnnouncement}
                            className="px-4 md:px-5 py-3 bg-[var(--color-yellow-main)]/92 text-white hover:bg-[var(--color-yellow-dark)] rounded-full transition-all duration-300 flex items-center text-xs md:text-sm font-black shadow-sm hover:shadow-[0_14px_28px_rgba(255,209,102,0.28)] active:scale-[0.99]"
                        >
                            <Bell size={14} className="mr-3" />
                            查看公告
                        </button>

                        <button
                            onClick={onSettings}
                            className="px-4 md:px-5 py-3 bg-white/75 text-[var(--color-cyan-dark)] hover:bg-white font-black text-xs md:text-sm transition-all duration-300 flex items-center rounded-full border border-white/70 hover:shadow-[0_14px_28px_rgba(255,255,255,0.28)] active:scale-[0.99]"
                        >
                            <Settings size={14} className="mr-3 group-hover:rotate-45 transition-transform" />
                            设置
                        </button>
                    </div>
                </div>
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
        @keyframes float-card {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        @keyframes float-card-delayed {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-14px); }
        }
        @keyframes float-card-slow {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-8px); }
        }
        @keyframes texture-scroll {
            0% { transform: translate3d(0, 0, 0); }
            100% { transform: translate3d(-40px, -40px, 0); }
        }
        .animate-float-card {
            animation: float-card 6s ease-in-out infinite;
        }
        .animate-float-card-delayed {
            animation: float-card-delayed 7.5s ease-in-out infinite;
        }
        .animate-float-card-slow {
            animation: float-card-slow 9s ease-in-out infinite;
        }
        .animate-texture-scroll {
            animation: texture-scroll 8s linear infinite;
            will-change: transform;
        }
    `;
    document.head.appendChild(style);
}
