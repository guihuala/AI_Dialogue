import { useEffect, useRef, useState } from 'react';
import { useGameStore } from '../store/gameStore';
import { RefreshCcw, ScrollText, X, Smartphone } from 'lucide-react';
import { TitleMenu } from './TitleMenu';
import { GameSetup } from './GameSetup';

export const GameView = ({ onTabChange }: { onTabChange: (tab: any) => void }) => {
    const { 
        displayText, 
        nextOptions, 
        isEnd, 
        isLoading, 
        performTurn, 
        startGame, 
        isPlaying,
        history,
        togglePhone
    } = useGameStore();

    const scrollRef = useRef<HTMLDivElement>(null);
    const historyScrollRef = useRef<HTMLDivElement>(null);
    
    const [typedText, setTypedText] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [showHistory, setShowHistory] = useState(false);
    
    // Dialog pacing state
    const [dialogSegments, setDialogSegments] = useState<string[]>([]);
    const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0);

    // Auto-scroll story text
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [typedText]);

    // Auto-scroll history overlay
    useEffect(() => {
        if (showHistory && historyScrollRef.current) {
            historyScrollRef.current.scrollTop = historyScrollRef.current.scrollHeight;
        }
    }, [showHistory, history]);
    
    // Split text into segments whenever displayText changes
    useEffect(() => {
        if (!displayText) {
            setDialogSegments([]);
            setCurrentSegmentIndex(0);
            setTypedText('');
            return;
        }
        
        // Split by double quotes or newlines to separate character dialog and narration
        const segments = displayText
            .split(/(?<=\n|”)/g)
            .map(s => s.trim())
            .filter(s => s.length > 0);
            
        setDialogSegments(segments.length > 0 ? segments : [displayText]);
        setCurrentSegmentIndex(0);
    }, [displayText]);

    // Typewriter effect for current segment
    useEffect(() => {
        if (dialogSegments.length === 0 || currentSegmentIndex >= dialogSegments.length) {
            setTypedText('');
            setIsTyping(false);
            return;
        }
        
        const currentText = dialogSegments[currentSegmentIndex];
        setIsTyping(true);
        let i = 0;
        
        const interval = setInterval(() => {
            setTypedText(currentText.slice(0, i + 1));
            i++;
            if (i >= currentText.length) {
                clearInterval(interval);
                setIsTyping(false);
            }
        }, 30); // Speed of typing

        return () => clearInterval(interval);
    }, [currentSegmentIndex, dialogSegments]);

    const handleTextClick = () => {
        if (dialogSegments.length === 0) return;
        
        if (isTyping) {
            // Speed up / Skip typing
            setTypedText(dialogSegments[currentSegmentIndex]);
            setIsTyping(false);
        } else {
            // Advance to next segment
            if (currentSegmentIndex < dialogSegments.length - 1) {
                setCurrentSegmentIndex(prev => prev + 1);
            }
        }
    };

    const isDialogFinished = dialogSegments.length > 0 && currentSegmentIndex === dialogSegments.length - 1 && !isTyping;

    const [phase, setPhase] = useState<'title' | 'setup' | 'playing'>(isPlaying ? 'playing' : 'title');

    // Sync phase with isPlaying
    useEffect(() => {
        if (isPlaying) setPhase('playing');
    }, [isPlaying]);

    if (phase === 'title') {
        return (
            <TitleMenu 
                onStart={() => setPhase('setup')}
                onWorkshop={() => onTabChange('workshop')}
                onEditor={() => onTabChange('editor')}
                onSettings={() => onTabChange('settings')}
            />
        );
    }

    if (phase === 'setup') {
        return (
            <GameSetup 
                onBack={() => setPhase('title')}
                onStartGame={(roommates, modId) => {
                    startGame(roommates, modId);
                }}
                onTabChange={onTabChange}
            />
        );
    }

    const determinePortrait = () => {
        if (!displayText) return null;
        
        // Scan backwards from the end, prioritizing exact names over single characters
        const lines = displayText.split('\n').filter(l => l.trim().length > 0);
        if (lines.length === 0) return null;
        
        // Search in the last few significant lines for dialogue markers
        const recentContext = lines.slice(-3).join('\n');
        
        // Map from character keys/names to portrait files
        // We know we have 唐, 李, 赵, 林, 陈, 苏, 陆陈
        // Full names from roster: 唐梦琪, 李一诺, 赵鑫, 林飒, 陈雨婷, 苏浅
        const portraitMapping = [
            { id: '唐', names: ['唐梦琪', '梦琪', '唐'] },
            { id: '李', names: ['李一诺', '一诺', '李'] },
            { id: '赵', names: ['赵鑫', '鑫鑫', '赵'] },
            { id: '林', names: ['林飒', '飒飒', '林'] },
            { id: '陈', names: ['陈雨婷', '雨婷', '陈'] },
            { id: '苏', names: ['苏浅', '浅浅', '苏'] },
        ];
        
        let bestMatch: { id: string, index: number, priority: number } | null = null;
        
        // Strategy: First look for "[Name]:" or "[Name]说" specifically
        for (const c of portraitMapping) {
            for (const name of c.names) {
                // Priority 1: Dialog tags like "唐梦琪：" or "唐："
                const dialogIdx = Math.max(
                    recentContext.lastIndexOf(`${name}：`), 
                    recentContext.lastIndexOf(`${name}:`)
                );
                
                if (dialogIdx > -1) {
                    if (!bestMatch || dialogIdx > bestMatch.index || (dialogIdx === bestMatch.index && bestMatch.priority < 2)) {
                        bestMatch = { id: c.id, index: dialogIdx, priority: 2 };
                    }
                    continue; // found best type for this name
                }
                
                // Priority 0: Just mention of the name
                const idx = recentContext.lastIndexOf(name);
                if (idx > -1 && (!bestMatch || (idx > bestMatch.index && bestMatch.priority === 0))) {
                    bestMatch = { id: c.id, index: idx, priority: 0 };
                }
            }
        }
        
        if (bestMatch) return `/assets/portraits/${bestMatch.id}.png`;
        return null;
    };
    
    const portraitUrl = determinePortrait();

    return (
        <div className="flex-1 flex flex-col h-full rounded-2xl border-2 border-[var(--color-cyan-main)]/20 shadow-xl overflow-hidden relative bg-black">
            {/* Background Image Layer */}
            <div 
                className="absolute inset-0 bg-cover bg-center opacity-70" 
                style={{ backgroundImage: "url('/assets/backgrounds/食堂.jpg')" }}
            />
            
            {/* Character Portrait Layer */}
            {portraitUrl && (
                <div className="absolute inset-0 flex items-end justify-center pointer-events-none z-10 overflow-hidden pb-[22vh]">
                    <img 
                        src={portraitUrl} 
                        alt="Portrait" 
                        className="max-h-[115%] max-w-[115%] drop-shadow-2xl translate-y-8 animate-in slide-in-from-bottom-8 duration-500 scale-105 origin-bottom"
                    />
                </div>
            )}

            {/* History Overlay Panel */}
            {showHistory && (
                <div className="absolute inset-0 z-40 bg-black/80 backdrop-blur-lg flex flex-col p-6 overflow-hidden">
                    <div className="flex justify-between items-center mb-6 shrink-0">
                        <h3 className="text-2xl font-black text-[var(--color-cyan-main)] tracking-widest uppercase flex items-center">
                            <ScrollText className="mr-3" /> 对局记录
                        </h3>
                        <button 
                            onClick={() => setShowHistory(false)}
                            className="p-2 bg-white/10 hover:bg-red-500/80 text-white rounded-full transition-colors"
                        >
                            <X size={24} />
                        </button>
                    </div>
                    <div 
                        ref={historyScrollRef}
                        className="flex-1 overflow-y-auto pr-4 space-y-6 custom-scrollbar"
                    >
                        {history.length === 0 && <div className="text-white/50 text-center mt-10 font-bold">暂无记录</div>}
                        {history.map((h, i) => (
                            <div key={i} className="bg-white/5 border border-white/10 p-4 rounded-xl">
                                <span className="text-[var(--color-yellow-main)] text-xs font-black tracking-widest uppercase mb-2 block">
                                    回合 {h.turn}
                                </span>
                                <div className="text-white/90 whitespace-pre-wrap font-bold leading-relaxed">{h.text}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Top Right Controls Layer */}
            <div className="absolute top-6 right-6 z-30 flex space-x-3 pointer-events-auto">
                <button 
                    onClick={() => togglePhone()}
                    className="flex items-center px-4 py-2 bg-white/90 hover:bg-white text-[var(--color-cyan-dark)] backdrop-blur-md rounded-full border border-[var(--color-cyan-main)]/30 shadow-lg transition-all font-black text-sm tracking-widest uppercase"
                >
                    <Smartphone size={16} className="mr-2 text-[var(--color-cyan-main)]" /> 呼出手机
                </button>
                <button 
                    onClick={() => setShowHistory(true)}
                    className="flex items-center px-4 py-2 bg-white/90 hover:bg-white text-[var(--color-cyan-dark)] backdrop-blur-md rounded-full border border-[var(--color-cyan-main)]/30 shadow-lg transition-all font-black text-sm tracking-widest uppercase"
                >
                    <ScrollText size={16} className="mr-2 text-[var(--color-yellow-main)] drop-shadow-sm" /> 回顾记录
                </button>
            </div>

            {/* UI Layer: Dialog (Bottom 22%) + Options (Right) */}
            <div className="absolute inset-0 pointer-events-none flex flex-col justify-end z-20">
                {/* Options Area (Positioned above dialog, on the right) */}
                {(!isTyping && !isLoading && !isEnd && isDialogFinished) && (
                    <div className="absolute right-10 bottom-[28vh] w-96 flex flex-col space-y-4 pointer-events-auto z-30">
                        {nextOptions.map((opt, idx) => (
                            <button
                                key={idx}
                                disabled={isLoading || isTyping}
                                onClick={() => performTurn(opt)}
                                className="p-4 bg-white/95 backdrop-blur-xl border-2 border-[var(--color-cyan-main)]/30 rounded-2xl shadow-2xl hover:border-[var(--color-yellow-main)] hover:bg-white hover:-translate-x-2 transition-all duration-300 disabled:opacity-50 font-black text-[var(--color-cyan-dark)] flex items-center group relative overflow-hidden text-left active:scale-95"
                            >
                                <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-cyan-light)]/0 via-[var(--color-cyan-light)]/50 to-[var(--color-cyan-light)]/0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
                                <div className="w-10 h-10 rounded-xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] flex items-center justify-center text-sm font-black mr-4 group-hover:bg-[var(--color-yellow-main)] transition-all shrink-0 border border-[var(--color-cyan-main)]/20 shadow-sm">
                                    {String.fromCharCode(65 + idx)}
                                </div>
                                <span className="leading-snug text-sm relative z-10">{opt}</span>
                            </button>
                        ))}
                    </div>
                )}
                
                {/* End Screen Content Container within GameView bounds */}
                {isEnd && (
                   <div className="absolute inset-0 flex items-center justify-center bg-white/50 backdrop-blur-sm z-30 pointer-events-auto rounded-2xl">
                       <div className="text-center w-full animate-in zoom-in duration-700">
                           <h3 className="text-4xl font-black text-[var(--color-cyan-dark)] mb-8 drop-shadow-sm tracking-[0.5em] ml-[0.5em] uppercase">故事已落幕</h3>
                           <button 
                               onClick={() => startGame()}
                               className="px-12 py-5 bg-gradient-to-br from-[var(--color-cyan-main)] to-[var(--color-cyan-dark)] text-white rounded-full font-black shadow-[0_10px_30px_rgba(0,188,212,0.4)] hover:scale-105 transition-all uppercase tracking-[0.3em] text-sm border-2 border-white/20 active:scale-95 mx-auto"
                           >
                               开启新的轮回
                           </button>
                       </div>
                   </div>
                )}

                {/* Dialog Box (Fixed 22% height at bottom) */}
                <div className="h-[22vh] w-[95%] mx-auto mb-6 bg-white/95 backdrop-blur-xl rounded-[2.5rem] border-2 border-[var(--color-cyan-main)]/30 shadow-[0_15px_40px_-10px_rgba(0,188,212,0.2)] pointer-events-auto overflow-hidden relative flex flex-col group/dialog transition-all duration-500 hover:shadow-[0_20px_40px_-10px_rgba(0,188,212,0.3)] hover:border-[var(--color-cyan-main)]/50">
                    <div 
                        ref={scrollRef}
                        onClick={handleTextClick}
                        className="flex-1 overflow-y-auto p-6 md:px-10 md:py-6 text-xl leading-[1.8] text-[var(--color-cyan-dark)] whitespace-pre-wrap font-bold custom-scrollbar cursor-pointer relative"
                        title={isTyping ? "点击跳过打字动画" : "点击继续"}
                    >
                        <div className="relative z-10">
                            {typedText || "等待故事载入..."}
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
                                        命运的齿轮正在转动
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
            </div>
        </div>
    );
};
