import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingScreen = ({ onFinished }: { onFinished: () => void }) => {
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState('初始化...');
    const [isLeaving, setIsLeaving] = useState(false);

    const tips = [
        "今天的膨胀券只膨胀了一块钱...",
        "为什么舍友都在外放抖音？",
        "每天都有早八，周六早还有课，命好苦。",
        "一堆作业，舍友还在打游戏，好烦啊！！",
        "宿舍好像有蟑螂？...随便吧，蟑螂有时候比舍友可爱。",
        "在微博上蛐蛐舍友记得开好友圈...",
        "小红书上刷到的大red竟然是我舍友？！"
    ];

    const [currentTip] = useState(() => tips[Math.floor(Math.random() * tips.length)]);

    const stages = [
        { threshold: 10, text: '正在浏览猫猫视频...' },
        { threshold: 30, text: '正在水课上赶DDL...' },
        { threshold: 50, text: '正在赶DDL...' },
        { threshold: 75, text: '正在wb小号蛐蛐舍友...' },
        { threshold: 90, text: '正在准备起床上早八...' },
        { threshold: 100, text: '准备就绪！' }
    ];

    useEffect(() => {
        const interval = setInterval(() => {
            setProgress(prev => {
                const next = prev + (Math.random() * 5 + 1);
                if (next >= 100) {
                    clearInterval(interval);
                    setTimeout(() => {
                        setIsLeaving(true);
                        setTimeout(onFinished, 1000);
                    }, 500);
                    return 100;
                }

                const currentStage = stages.find(s => next < s.threshold);
                if (currentStage) setStatus(currentStage.text);

                return next;
            });
        }, 150);

        return () => clearInterval(interval);
    }, []);

    return (
        <div className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-gradient-to-br from-[var(--color-cyan-light)] via-white to-[var(--color-yellow-light)] transition-all duration-1000 ${isLeaving ? 'opacity-0 scale-110' : 'opacity-100'}`}>
            {/* Background Decorative Elements */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-20">
                <div className="absolute top-1/4 -left-20 w-80 h-80 bg-[var(--color-cyan-main)] rounded-full blur-[100px] animate-pulse"></div>
                <div className="absolute bottom-1/4 -right-20 w-80 h-80 bg-[var(--color-yellow-main)] rounded-full blur-[100px] animate-pulse" style={{ animationDelay: '1s' }}></div>
            </div>

            <div className="relative flex flex-col items-center max-w-md w-full px-8 text-center">
                {/* Logo Animation */}
                <div className="mb-12 relative group">
                    <div className="w-24 h-24 rounded-3xl flex items-center justify-center relative z-10">
                        <img src="/avatar.webp" alt="Logo"></img>
                    </div>
                    {/* Ring Decorations */}
                    <div className="absolute -inset-4 border-2 border-[var(--color-cyan-main)]/10 rounded-[2.5rem] animate-[spin_8s_linear_infinite]"></div>
                    <div className="absolute -inset-8 border border-[var(--color-yellow-main)]/10 rounded-[3rem] animate-[spin_12s_linear_infinite_reverse]"></div>

                    {/* Floating Icons */}
                    <div className="absolute -top-4 -right-4 w-10 h-10 rounded-xl flex items-center justify-center text-[var(--color-yellow-main)] animate-bounce" style={{ animationDelay: '0.2s' }}>
                        <img src="/avatar.webp" alt="Logo"></img>
                    </div>
                    <div className="absolute -bottom-2 -left-6 w-12 h-12 rounded-xl flex items-center justify-center text-[var(--color-cyan-main)] animate-bounce" style={{ animationDelay: '0.5s' }}>
                        <img src="assets/branding/guihua_ni_avatar.webp" alt="Logo"></img>
                    </div>
                </div>

                <h1 className="text-4xl font-black text-[var(--color-cyan-dark)] tracking-tighter mb-2 uppercase">
                    代号：大学档案
                </h1>
                <p className="text-sm font-bold text-[var(--color-cyan-dark)]/40 uppercase tracking-[0.3em] mb-12">
                    我真的还没想好这个游戏应该叫什么名字
                </p>

                {/* Progress Bar Container */}
                <div className="w-full h-12 bg-white/50 backdrop-blur-sm rounded-2xl border-2 border-[var(--color-cyan-main)]/10 p-1.5 mb-6 shadow-inner relative overflow-hidden">
                    <div
                        className="h-full bg-gradient-to-r from-[var(--color-cyan-main)] via-[var(--color-cyan-main)] to-[var(--color-yellow-main)] rounded-xl transition-all duration-300 ease-out shadow-lg"
                        style={{ width: `${progress}%` }}
                    >
                        {/* Glow effect */}
                        <div className="absolute inset-y-0 right-0 w-20 bg-white/30 blur-md translate-x-10 skew-x-12"></div>
                    </div>

                    {/* Percentage Display */}
                    <div className="absolute inset-0 flex items-center justify-center mix-blend-difference">
                        <span className="text-xs font-black text-white tracking-widest">{Math.round(progress)}%</span>
                    </div>
                </div>

                {/* Status Text with Spinner */}
                <div className="flex items-center justify-center space-x-3 text-[var(--color-cyan-dark)]/60">
                    <Loader2 size={16} className="animate-spin text-[var(--color-cyan-main)]" />
                    <p className="text-xs font-bold uppercase tracking-widest">
                        {status}
                    </p>
                </div>

                {/* Footer Insight */}
                <div className="mt-24 p-4 rounded-xl bg-white/30 border border-white/50">
                    <div className="flex items-center space-x-2 mb-2 text-[var(--color-cyan-main)]">
                        <span className="text-[10px] font-black uppercase tracking-widest">现在的心情</span>
                    </div>
                    <p className="text-[10px] font-bold text-[var(--color-cyan-dark)]/60 leading-relaxed italic">
                        "{currentTip}"
                    </p>
                </div>
            </div>
        </div>
    );
};
