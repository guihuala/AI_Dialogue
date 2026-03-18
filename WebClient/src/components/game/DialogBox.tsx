import { RefreshCcw } from 'lucide-react';
import { ReactNode, RefObject } from 'react';

interface DialogBoxProps {
    typedText: string;
    isTyping: boolean;
    isLoading: boolean;
    isDialogFinished: boolean;
    onTextClick: () => void;
    scrollRef: RefObject<HTMLDivElement>;
    parseMarktext: (text: string) => ReactNode;
}

export const DialogBox = ({
    typedText,
    isTyping,
    isLoading,
    isDialogFinished,
    onTextClick,
    scrollRef,
    parseMarktext
}: DialogBoxProps) => {
    return (
        <div className="h-[22vh] w-[95%] mx-auto mb-6 bg-white/95 backdrop-blur-xl rounded-[2.5rem] border-2 border-[var(--color-cyan-main)]/30 shadow-[0_15px_40px_-10px_rgba(0,188,212,0.2)] pointer-events-auto overflow-hidden relative flex flex-col group/dialog transition-all duration-500 hover:shadow-[0_20px_40px_-10px_rgba(0,188,212,0.3)] hover:border-[var(--color-cyan-main)]/50">
            <div
                ref={scrollRef}
                onClick={onTextClick}
                className="flex-1 overflow-y-auto p-6 md:px-10 md:py-6 text-xl leading-[1.8] text-[var(--color-cyan-dark)] whitespace-pre-wrap font-bold custom-scrollbar cursor-pointer relative"
                title={isTyping ? "点击跳过打字动画" : "点击继续"}
            >
                <div className="relative z-10">
                    {parseMarktext(typedText || "等待故事载入...")}
                    {isTyping && <span className="typing-cursor ml-1"></span>}
                </div>

                {/* Loading State Overlay over text area */}
                {!isTyping && isLoading && (
                    <div className="absolute inset-0 bg-white/80 backdrop-blur-md flex flex-col items-center justify-center animate-fade-in z-20">
                        <div className="relative scale-75">
                            <div className="w-24 h-24 rounded-full border-4 border-[var(--color-cyan-light)] border-t-[var(--color-cyan-main)] animate-spin"></div>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <RefreshCcw className="text-[var(--color-cyan-main)] animate-pulse" size={32} />
                            </div>
                            <div className="absolute -inset-4 border border-[var(--color-cyan-main)]/20 rounded-full animate-[ping_2s_infinite]"></div>
                            <div className="absolute -inset-8 border border-[var(--color-cyan-main)]/10 rounded-full animate-[ping_3s_infinite]"></div>
                        </div>
                        <div className="mt-6 flex flex-col items-center">
                            <span className="text-[8px] font-black text-[var(--color-cyan-main)]/60 uppercase tracking-[0.6em] mb-2">Neural Process</span>
                            <div className="flex items-center text-[var(--color-cyan-dark)] font-black text-[10px] tracking-[0.2em] uppercase bg-[var(--color-cyan-light)] px-6 py-2 rounded-full border border-[var(--color-cyan-main)]/20 shadow-sm">
                                对话生成中
                                <span className="ml-3 flex space-x-1.5 min-w-[20px]">
                                    <span className="w-1.5 h-1.5 bg-[var(--color-cyan-dark)] rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                    <span className="w-1.5 h-1.5 bg-[var(--color-cyan-dark)] rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                    <span className="w-1.5 h-1.5 bg-[var(--color-cyan-dark)] rounded-full animate-bounce"></span>
                                </span>
                            </div>
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
    );
};
