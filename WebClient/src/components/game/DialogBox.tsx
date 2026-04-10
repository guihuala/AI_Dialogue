import { RefreshCcw } from 'lucide-react';
import { ReactNode, RefObject, useEffect, useState } from 'react';

interface DialogBoxProps {
    typedText: string;
    isTyping: boolean;
    isLoading: boolean;
    isDialogFinished: boolean;
    onTextClick: () => void;
    scrollRef: RefObject<HTMLDivElement>;
    parseMarktext: (text: string) => ReactNode;
    speakerName?: string;
    pendingChoice?: string | null;
    avgResponseMs?: number;
    autoPlayDialogue?: boolean;
}

export const DialogBox = ({
    typedText,
    isTyping,
    isLoading,
    isDialogFinished,
    onTextClick,
    scrollRef,
    parseMarktext,
    speakerName,
    pendingChoice,
    avgResponseMs = 8000,
    autoPlayDialogue = false
}: DialogBoxProps) => {
    const [loadingElapsedMs, setLoadingElapsedMs] = useState(0);

    useEffect(() => {
        if (!isLoading) {
            setLoadingElapsedMs(0);
            return;
        }
        const startedAt = Date.now();
        const timer = setInterval(() => {
            setLoadingElapsedMs(Date.now() - startedAt);
        }, 120);
        return () => clearInterval(timer);
    }, [isLoading]);

    const renderText = typedText || "";
    const expectedMs = Math.max(2500, Number(avgResponseMs || 8000));
    const ratio = Math.max(0, Math.min(1.2, loadingElapsedMs / expectedMs));
    const progressPercent = Math.min(96, Math.round((1 - Math.exp(-2.4 * ratio)) * 100));

    return (
        <div className="w-[95%] mx-auto mb-6 relative group/dialog">
            {speakerName && (
                <div className="absolute top-0 left-10 -translate-y-1/2 px-8 py-2 bg-[var(--color-cyan-main)] text-white font-black text-sm rounded-full shadow-lg z-30 border-2 border-white animate-fade-in-up">
                    {speakerName}
                </div>
            )}
            <div className="h-[22vh] bg-white/95 backdrop-blur-xl rounded-[2.5rem] border-2 border-[var(--color-cyan-main)]/30 shadow-[0_15px_40px_-10px_rgba(0,188,212,0.2)] pointer-events-auto overflow-hidden flex flex-col transition-all duration-500 hover:shadow-[0_20px_40px_-10px_rgba(0,188,212,0.3)] hover:border-[var(--color-cyan-main)]/50">
            <div
                ref={scrollRef}
                onClick={onTextClick}
                className="flex-1 overflow-y-auto p-6 md:px-10 md:py-6 text-xl leading-[1.8] text-[var(--color-cyan-dark)] whitespace-pre-wrap font-bold custom-scrollbar cursor-pointer relative"
                title={isTyping ? "点击跳过打字动画" : "点击继续"}
            >
                <div className="relative z-10">
                    {parseMarktext(renderText)}
                    {isTyping && <span className="typing-cursor ml-1"></span>}
                </div>

                {/* Loading hint (non-blocking) */}
                {!isTyping && isLoading && (
                    <div className="absolute right-5 bottom-4 z-20">
                        <div className="w-[260px] bg-white/90 backdrop-blur-md px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 shadow-sm">
                            <div className="flex items-center justify-between text-[var(--color-cyan-dark)] font-black text-[10px] tracking-[0.15em] uppercase">
                                <div className="flex items-center">
                                    <RefreshCcw className="mr-2 text-[var(--color-cyan-main)] animate-spin" size={12} />
                                    {pendingChoice ? '生成中' : '对话生成中'}
                                </div>
                                <span className="tabular-nums text-[9px] text-[var(--color-cyan-main)]">
                                    {progressPercent}%
                                </span>
                            </div>
                            <div className="mt-1.5 h-1.5 rounded-full bg-[var(--color-cyan-light)]/60 overflow-hidden">
                                <div
                                    className="h-full rounded-full bg-gradient-to-r from-[var(--color-cyan-main)] to-[var(--color-yellow-main)] transition-[width] duration-150"
                                    style={{ width: `${progressPercent}%` }}
                                />
                            </div>
                            <div className="mt-1 text-[9px] text-slate-500">
                                预计约 {Math.max(1, Math.round(expectedMs / 1000))}s
                            </div>
                            <span className="sr-only">
                                当前进度 {progressPercent}%
                            </span>
                        </div>
                    </div>
                )}

                {/* Prompt to click text */}
                {!isDialogFinished && !isLoading && !isTyping && (
                    <div className="sticky bottom-0 right-0 float-right pt-4 px-2 py-1 bg-gradient-to-l from-white/0 via-white/80 to-white text-[10px] text-[var(--color-cyan-main)]/70 font-black tracking-[0.5em] uppercase hover:text-[var(--color-cyan-dark)] transition-colors animate-pulse">
                        {autoPlayDialogue ? '自动播放中' : '点击继续阅读'}
                    </div>
                )}
            </div>
            </div>
        </div>
    );
};
