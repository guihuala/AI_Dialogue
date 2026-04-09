import { useState, useEffect } from 'react';
import { gameApi } from '../api/gameApi';
import { RefreshCcw, Milestone, Rocket, FolderOpen, ArrowLeft } from 'lucide-react';

interface SaveSelectionProps {
    onNewGame: () => void;
    onLoadGame: (slotId: number) => void;
    onBack: () => void;
}

export const SaveSelection = ({ onNewGame, onLoadGame, onBack }: SaveSelectionProps) => {
    const [saves, setSaves] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        loadSaves();
    }, []);

    const loadSaves = async () => {
        setIsLoading(true);
        try {
            const data = await gameApi.getSavesInfo();
            setSaves(data.slots || []);
        } catch (error) {
            console.error('Failed to load saves:', error);
        } finally {
            setIsLoading(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-8 md:p-12 bg-white/82 backdrop-blur-md rounded-[1.5rem] md:rounded-[2rem] border border-[var(--color-cyan-main)]/15 shadow-xl min-h-[360px] md:min-h-[500px]">
                <RefreshCcw className="animate-spin text-[var(--color-cyan-main)] mb-4" size={48} />
                <p className="text-base font-black text-[var(--color-cyan-main)] animate-pulse">正在扫描存档...</p>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col h-full bg-white/82 backdrop-blur-md rounded-[1.5rem] md:rounded-[2rem] border border-[var(--color-cyan-main)]/12 shadow-2xl overflow-hidden animate-fade-in-up p-4 md:p-8">
            <div className="flex items-center justify-between mb-6 md:mb-10 border-b border-[var(--color-cyan-main)]/10 pb-4 md:pb-5">
                <div className="flex items-center min-w-0">
                    <button
                        onClick={onBack}
                        className="mr-3 md:mr-6 p-2.5 md:p-3 bg-white hover:bg-[var(--color-cyan-main)] hover:text-white rounded-xl transition-all shadow-sm border border-[var(--color-cyan-main)]/20 group shrink-0"
                    >
                        <ArrowLeft size={20} className="group-hover:-translate-x-1 transition-transform" />
                    </button>
                    <div className="min-w-0">
                        <h2 className="text-2xl md:text-3xl font-black text-[var(--color-cyan-dark)] tracking-tight">选择存档</h2>
                        <p className="mt-1 text-xs md:text-sm text-[var(--color-cyan-dark)]/60">继续上一次进度，或者直接开启新的一局。</p>
                    </div>
                </div>
            </div>

            <div className="flex-1 flex flex-col items-center justify-center">
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 md:gap-6 w-full max-w-6xl">
                    {/* New Game Option */}
                    <div
                        onClick={onNewGame}
                        className="group relative p-6 md:p-8 rounded-[1.5rem] md:rounded-[2rem] border-2 border-dashed border-[var(--color-cyan-main)]/30 hover:border-[var(--color-cyan-main)] bg-white/55 hover:bg-white transition-all cursor-pointer flex flex-col items-center justify-center text-center gap-4 md:gap-5 min-h-[280px] md:h-96"
                    >
                        <div className="w-24 h-24 rounded-[1.75rem] bg-[var(--color-cyan-dark)] text-white flex items-center justify-center shadow-lg group-hover:scale-105 transition-all">
                            <Rocket size={40} />
                        </div>
                        <div>
                            <h3 className="text-xl md:text-2xl font-black text-[var(--color-cyan-dark)]">开启新游戏</h3>
                        </div>
                        <div className="text-sm font-black text-[var(--color-cyan-dark)] bg-[var(--color-cyan-light)] px-4 py-2 rounded-full group-hover:bg-[var(--color-yellow-main)] transition-all">
                            选择舍友并进入宿舍
                        </div>
                    </div>

                    {/* Filter for non-empty saves */}
                    {saves.map((slot) => (
                        <div
                            key={slot.slot_id}
                            onClick={() => !slot.is_empty && onLoadGame(slot.slot_id)}
                        className={`group relative p-6 md:p-8 rounded-[1.5rem] md:rounded-[2rem] border transition-all duration-500 min-h-[280px] md:h-96 flex flex-col ${slot.is_empty ? 'border-dashed border-gray-200 bg-gray-50/50 grayscale opacity-40 cursor-not-allowed' : 'border-[var(--color-cyan-main)]/12 bg-white hover:border-[var(--color-yellow-main)]/50 hover:-translate-y-1 cursor-pointer'}`}
                        >
                            <div className="absolute top-8 left-8 text-sm font-black text-[var(--color-cyan-main)]">
                                存档 {slot.slot_id}
                            </div>

                            <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
                                <div className={`w-20 h-20 rounded-2xl flex items-center justify-center transition-all ${slot.is_empty ? 'bg-gray-200 text-gray-400' : 'bg-[var(--color-yellow-main)]/20 text-[var(--color-yellow-dark)] group-hover:scale-105'}`}>
                                    {slot.is_empty ? <Milestone size={32} /> : <FolderOpen size={32} />}
                                </div>

                                <div>
                                    <h4 className="text-lg md:text-xl font-black text-[var(--color-cyan-dark)] line-clamp-2 min-h-[3rem] md:min-h-[3.5rem]">
                                        {slot.is_empty ? '空存档' : slot.chapter_info}
                                    </h4>
                                    {!slot.is_empty && (
                                        <p className="mt-2 text-sm font-bold text-[var(--color-cyan-dark)]/45 flex items-center justify-center">
                                            最后更新: {slot.timestamp}
                                        </p>
                                    )}
                                </div>
                            </div>

                            {!slot.is_empty && (
                                <div className="mt-auto w-full py-4 bg-[var(--color-cyan-light)] group-hover:bg-[var(--color-yellow-main)] text-[var(--color-cyan-dark)] font-black rounded-2xl transition-all flex items-center justify-center">
                                    加载存档
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};
