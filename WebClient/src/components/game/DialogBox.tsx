import { RefreshCcw } from 'lucide-react';
import { ReactNode, RefObject, useEffect, useMemo, useState } from 'react';

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
    pendingChoice
}: DialogBoxProps) => {
    const [loadingPhase, setLoadingPhase] = useState(0);

    useEffect(() => {
        if (!(isLoading && pendingChoice)) {
            setLoadingPhase(0);
            return;
        }
        const timer = setInterval(() => {
            setLoadingPhase((v) => (v + 1) % 4);
        }, 900);
        return () => {
            clearInterval(timer);
        };
    }, [isLoading, pendingChoice]);

    const stageHints = useMemo(
        () => [
            "（室友正在理解你的选择...）",
            "（她们交换了一个眼神，气氛有些微妙。）",
            "（新的回应正在形成，请稍等。）",
            "（剧情即将接续到下一段。）"
        ],
        []
    );

    const optimisticText = pendingChoice
        ? `你选择了：${pendingChoice}\n\n${stageHints[loadingPhase]}`
        : "";
    const renderText = isLoading && optimisticText ? optimisticText : (typedText || "等待故事载入...");

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
                        <div className="flex items-center text-[var(--color-cyan-dark)] font-black text-[10px] tracking-[0.15em] uppercase bg-white/90 backdrop-blur-md px-4 py-2 rounded-full border border-[var(--color-cyan-main)]/20 shadow-sm">
                            <RefreshCcw className="mr-2 text-[var(--color-cyan-main)] animate-spin" size={12} />
                            {pendingChoice ? '生成中' : '对话生成中'}
                            <span className="ml-2 flex space-x-1 min-w-[14px]">
                                <span className="w-1 h-1 bg-[var(--color-cyan-dark)] rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                <span className="w-1 h-1 bg-[var(--color-cyan-dark)] rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                <span className="w-1 h-1 bg-[var(--color-cyan-dark)] rounded-full animate-bounce"></span>
                            </span>
                        </div>
                    </div>
                )}

                {/* Prompt to click text */}
                {!isDialogFinished && !isLoading && !isTyping && (
                    <div className="sticky bottom-0 right-0 float-right pt-4 px-2 py-1 bg-gradient-to-l from-white/0 via-white/80 to-white text-[10px] text-[var(--color-cyan-main)]/70 font-black tracking-[0.5em] uppercase hover:text-[var(--color-cyan-dark)] transition-colors animate-pulse">
                        点击继续阅读
                    </div>
                )}
            </div>
            </div>
        </div>
    );
};
