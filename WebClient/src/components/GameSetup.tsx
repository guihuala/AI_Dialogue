import { useState, useEffect } from 'react';
import { gameApi } from '../api/gameApi';
import { useGameStore } from '../store/gameStore';
import { RefreshCw, Dices } from 'lucide-react';
import { SetupHeader } from './game/setup/SetupHeader';
import { ModPackSelector } from './game/setup/ModPackSelector';
import { RoommateSelector } from './game/setup/RoommateSelector';
import { StartGameButton } from './game/setup/StartGameButton';

interface GameSetupProps {
    onBack: () => void;
    onStartGame: (roommates: string[], modId?: string, maxTurns?: number) => void;
    onTabChange: (tab: any) => void;
}

export const GameSetup = ({ onBack, onStartGame, onTabChange }: GameSetupProps) => {
    const [candidates, setCandidates] = useState<any[]>([]);
    const [selectedRoommates, setSelectedRoommates] = useState<string[]>([]);
    const [selectedMod, setSelectedMod] = useState<string>('default');
    const [maxTurns, setMaxTurns] = useState<number>(20);
    const [isLoading, setIsLoading] = useState(true);
    const isGameLoading = useGameStore(state => state.isLoading);

    useEffect(() => {
        let alive = true;
        const loadSetupData = async () => {
            setIsLoading(true);
            try {
                const candRes = await gameApi.getCandidates(selectedMod || 'default');
                const safeCandidates = (candRes.data || []).filter((c: any) => !c?.is_player);
                if (!alive) return;
                setCandidates(safeCandidates);
                const validIds = new Set(safeCandidates.map((c: any) => c.id));
                setSelectedRoommates((prev) => prev.filter((id) => validIds.has(id)).slice(0, 3));
            } catch (e) {
                console.error(e);
            } finally {
                if (alive) setIsLoading(false);
            }
        };
        loadSetupData();
        return () => {
            alive = false;
        };
    }, [selectedMod]);

    const toggleRoommate = (id: string) => {
        setSelectedRoommates(prev => {
            if (prev.includes(id)) return prev.filter(i => i !== id);
            const next = [...prev, id];
            return next.length > 3 ? next.slice(1) : next;
        });
    };

    const randomizeRoommates = () => {
        if (candidates.length < 3) return;
        const shuffled = [...candidates].sort(() => 0.5 - Math.random());
        setSelectedRoommates(shuffled.slice(0, 3).map(c => c.id));
    };

    if (isLoading) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-12 bg-white/82 backdrop-blur-md rounded-[2rem] border border-[var(--color-cyan-main)]/15 shadow-xl min-h-[500px]">
                <RefreshCw className="animate-spin text-[var(--color-cyan-main)] mb-4" size={48} />
                <p className="text-base font-black text-[var(--color-cyan-main)] animate-pulse">加载中...</p>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col h-full bg-white/82 backdrop-blur-md rounded-[2rem] border border-[var(--color-cyan-main)]/12 shadow-2xl overflow-hidden animate-fade-in-up">
            <SetupHeader onBack={onBack} isReady={selectedRoommates.length === 3} />

            <div className="flex-1 flex flex-col md:flex-row overflow-hidden bg-[var(--color-cyan-light)]/10">
                <ModPackSelector 
                    selectedMod={selectedMod} 
                    setSelectedMod={setSelectedMod} 
                    onTabChange={onTabChange} 
                />

                <div className="flex-1 flex flex-col overflow-hidden">
                    <RoommateSelector 
                        candidates={candidates} 
                        selectedRoommates={selectedRoommates} 
                        onToggleRoommate={toggleRoommate}
                    />

                    <div className="p-8 bg-white/45 backdrop-blur-sm border-t border-[var(--color-cyan-main)]/10 flex flex-col gap-5">
                        <div className="flex items-center justify-between gap-4">
                            <div>
                                <p className="text-lg font-black text-[var(--color-cyan-dark)] tracking-tight">最大回合数</p>
                                <p className="mt-1 text-sm text-[var(--color-cyan-dark)]/55">推荐 18-24。</p>
                            </div>
                            <div className="px-4 py-2 rounded-2xl bg-[var(--color-cyan-dark)] text-[var(--color-yellow-main)] text-2xl font-black leading-none shadow-md tabular-nums min-w-[74px] text-center">
                                {maxTurns}
                            </div>
                        </div>
                        <input
                            type="range"
                            min={15}
                            max={30}
                            step={1}
                            value={maxTurns}
                            onChange={(e) => setMaxTurns(Math.max(15, Math.min(30, Number(e.target.value) || 20)))}
                            className="setup-range"
                            style={{ ['--progress' as any]: `${((maxTurns - 15) / 15) * 100}%` }}
                        />

                        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                            <button
                                onClick={randomizeRoommates}
                                className="w-full md:w-auto flex items-center justify-center gap-3 px-8 py-4 bg-white hover:bg-[var(--color-cyan-main)]/5 text-[var(--color-cyan-main)] text-sm font-black rounded-2xl border border-[var(--color-cyan-main)]/20 transition-all active:scale-95 group shadow-lg"
                            >
                                <Dices size={20} className="group-hover:rotate-180 transition-transform duration-700" />
                                随机
                            </button>

                            <StartGameButton
                                disabled={selectedRoommates.length !== 3}
                                isLoading={isGameLoading}
                                onClick={() => onStartGame(selectedRoommates, selectedMod, maxTurns)}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
