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
            <div className="flex-1 flex flex-col items-center justify-center p-12 bg-white/80 backdrop-blur-md rounded-3xl border-2 border-[var(--color-cyan-main)]/20 shadow-xl min-h-[500px]">
                <RefreshCcw className="animate-spin text-[var(--color-cyan-main)] mb-4" size={48} />
                <p className="text-sm font-black text-[var(--color-cyan-main)] tracking-widest uppercase animate-pulse">正在扫描存档...</p>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col h-full bg-white/80 backdrop-blur-md rounded-3xl border-2 border-[var(--color-cyan-main)]/10 shadow-2xl overflow-hidden animate-fade-in-up p-8">
            <div className="flex items-center justify-between mb-12 border-b-2 border-dashed border-[var(--color-cyan-main)]/10 pb-6">
                <div className="flex items-center">
                    <button
                        onClick={onBack}
                        className="mr-6 p-3 bg-white hover:bg-[var(--color-cyan-main)] hover:text-white rounded-xl transition-all shadow-sm border border-[var(--color-cyan-main)]/20 group"
                    >
                        <ArrowLeft size={20} className="group-hover:-translate-x-1 transition-transform" />
                    </button>
                    <div>
                        <h2 className="text-3xl font-black text-[var(--color-cyan-dark)] tracking-tight">选择存档</h2>
                        <p className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.3em]">选择存档或开启全新游戏</p>
                    </div>
                </div>
            </div>

            <div className="flex-1 flex flex-col items-center justify-center">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-8 w-full max-w-6xl">
                    {/* New Game Option */}
                    <div
                        onClick={onNewGame}
                        className="group relative p-8 rounded-[2.5rem] border-4 border-dashed border-[var(--color-cyan-main)]/30 hover:border-[var(--color-cyan-main)] bg-white/40 hover:bg-white hover:shadow-2xl hover:shadow-cyan-500/10 transition-all cursor-pointer flex flex-col items-center justify-center text-center space-y-6 h-96"
                    >
                        <div className="w-24 h-24 rounded-3xl bg-[var(--color-cyan-dark)] text-white flex items-center justify-center shadow-lg group-hover:scale-110 group-hover:rotate-6 transition-all">
                            <Rocket size={40} />
                        </div>
                        <div>
                            <h3 className="text-2xl font-black text-[var(--color-cyan-dark)] uppercase">开启新游戏</h3>
                            <p className="text-xs font-bold text-[var(--color-cyan-dark)]/40 mt-2 uppercase tracking-tighter">START A FRESH GAME</p>
                        </div>
                        <div className="text-[10px] font-black text-[var(--color-cyan-main)] bg-[var(--color-cyan-light)] px-4 py-2 rounded-full uppercase tracking-widest group-hover:bg-[var(--color-yellow-main)] group-hover:text-[var(--color-cyan-dark)] transition-all">
                            选择舍友并进入宿舍
                        </div>
                    </div>

                    {/* Filter for non-empty saves */}
                    {saves.map((slot) => (
                        <div
                            key={slot.slot_id}
                            onClick={() => !slot.is_empty && onLoadGame(slot.slot_id)}
                            className={`group relative p-8 rounded-[2.5rem] border-2 transition-all duration-500 h-96 flex flex-col ${slot.is_empty ? 'border-dashed border-gray-200 bg-gray-50/50 grayscale opacity-40 cursor-not-allowed' : 'border-[var(--color-cyan-main)]/10 bg-white hover:border-[var(--color-yellow-main)]/50 hover:shadow-2xl hover:shadow-yellow-500/10 hover:-translate-y-2 cursor-pointer'}`}
                        >
                            <div className="absolute top-8 left-8 text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.4em]">
                                SLOT 0{slot.slot_id}
                            </div>

                            <div className="flex-1 flex flex-col items-center justify-center text-center space-y-4">
                                <div className={`w-20 h-20 rounded-2xl flex items-center justify-center transition-all ${slot.is_empty ? 'bg-gray-200 text-gray-400' : 'bg-[var(--color-yellow-main)]/20 text-[var(--color-yellow-dark)] group-hover:scale-110 group-hover:-rotate-3'}`}>
                                    {slot.is_empty ? <Milestone size={32} /> : <FolderOpen size={32} />}
                                </div>

                                <div>
                                    <h4 className="text-xl font-black text-[var(--color-cyan-dark)] line-clamp-2 min-h-[3.5rem]">
                                        {slot.is_empty ? '空存档' : slot.chapter_info}
                                    </h4>
                                    {!slot.is_empty && (
                                        <p className="text-[10px] font-bold text-[var(--color-cyan-dark)]/40 mt-2 uppercase tracking-tighter flex items-center justify-center">
                                            最后更新: {slot.timestamp}
                                        </p>
                                    )}
                                </div>
                            </div>

                            {!slot.is_empty && (
                                <div className="mt-auto w-full py-4 bg-[var(--color-cyan-light)] group-hover:bg-[var(--color-yellow-main)] text-[var(--color-cyan-dark)] font-black rounded-2xl tracking-[0.2em] transition-all flex items-center justify-center">
                                    加载存档
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            <div className="mt-8 text-center text-[9px] font-black text-[var(--color-cyan-main)]/20 uppercase tracking-[1em]">
                Deep Reality Archive Engine // Sector 404
            </div>
        </div>
    );
};
