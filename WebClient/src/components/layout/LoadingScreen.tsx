import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingScreen = ({ onFinished }: { onFinished: () => void }) => {
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState('初始化中...');
    const [isLeaving, setIsLeaving] = useState(false);

    const stages = [
        { threshold: 30, text: '载入角色与世界设定...' },
        { threshold: 70, text: '初始化剧情系统...' },
        { threshold: 95, text: '整理本局状态...' },
        { threshold: 100, text: '准备就绪！' }
    ];

    useEffect(() => {
        const interval = setInterval(() => {
            setProgress(prev => {
                const next = prev + (Math.random() * 18 + 12);
                if (next >= 100) {
                    clearInterval(interval);
                    setTimeout(() => {
                        setIsLeaving(true);
                        setTimeout(onFinished, 220);
                    }, 80);
                    return 100;
                }

                const currentStage = stages.find(s => next < s.threshold);
                if (currentStage) setStatus(currentStage.text);

                return next;
            });
        }, 170);

        return () => clearInterval(interval);
    }, []);

    return (
        <div className={`fixed inset-0 z-[9999] flex items-center justify-center bg-[var(--color-cyan-light)] transition-all duration-300 ${isLeaving ? 'opacity-0' : 'opacity-100'}`}>
            <div className="w-[320px] max-w-[86vw] rounded-2xl border border-[var(--color-cyan-main)]/15 bg-white/92 backdrop-blur-sm px-5 py-5 shadow-lg">
                <div className="text-base font-black tracking-tight text-[var(--color-cyan-dark)] mb-3">载入中</div>
                <div className="h-2 w-full rounded-full bg-[var(--color-cyan-light)] overflow-hidden">
                    <div
                        className="h-full bg-[var(--color-cyan-main)] transition-all duration-200"
                        style={{ width: `${progress}%` }}
                    />
                </div>
                <div className="mt-3 flex items-center justify-between text-[11px] font-bold text-[var(--color-cyan-dark)]/70">
                    <div className="inline-flex items-center gap-2">
                        <Loader2 size={12} className="animate-spin text-[var(--color-cyan-main)]" />
                        <span>{status}</span>
                    </div>
                    <span>{Math.round(progress)}%</span>
                </div>
            </div>
        </div>
    );
};
