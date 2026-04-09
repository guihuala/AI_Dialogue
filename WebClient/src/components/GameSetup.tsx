import { useState, useEffect } from 'react';
import { gameApi } from '../api/gameApi';
import { settingsApi } from '../api/settingsApi';
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
    const [configChecked, setConfigChecked] = useState(false);
    const [hasValidApiConfig, setHasValidApiConfig] = useState(false);
    const [configErrorMessage, setConfigErrorMessage] = useState('');
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

    useEffect(() => {
        let alive = true;
        const checkSettings = async () => {
            try {
                await settingsApi.validateSettings();
                if (alive) {
                    setHasValidApiConfig(true);
                    setConfigErrorMessage('');
                }
            } catch (error: any) {
                if (alive) {
                    setHasValidApiConfig(false);
                    const status = Number(error?.response?.status || 0);
                    const detail = String(error?.response?.data?.detail || '').trim();
                    const lowered = detail.toLowerCase();

                    if (status === 404 || lowered === 'not found' || lowered.includes('not found')) {
                        setConfigErrorMessage('后端好像并没有检验API key的接口...');
                    } else if (detail.includes('尚未完整配置') || detail.includes('API Key') || detail.includes('模型配置无效')) {
                        setConfigErrorMessage('还没有配置API key。请先检查你的设置～');
                    } else {
                        setConfigErrorMessage(detail || '模型配置无效，请配置正确的API哦！');
                    }
                }
            } finally {
                if (alive) {
                    setConfigChecked(true);
                }
            }
        };
        checkSettings();
        return () => {
            alive = false;
        };
    }, []);

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

    const canStartGame = selectedRoommates.length === 3 && hasValidApiConfig && configChecked;

    if (isLoading) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-8 md:p-12 bg-white/82 backdrop-blur-md rounded-[1.5rem] md:rounded-[2rem] border border-[var(--color-cyan-main)]/15 shadow-xl min-h-[360px] md:min-h-[500px]">
                <RefreshCw className="animate-spin text-[var(--color-cyan-main)] mb-4" size={48} />
                <p className="text-base font-black text-[var(--color-cyan-main)] animate-pulse">加载中...</p>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col h-full bg-white/82 backdrop-blur-md rounded-[1.5rem] md:rounded-[2rem] border border-[var(--color-cyan-main)]/12 shadow-2xl overflow-hidden animate-fade-in-up">
            <SetupHeader onBack={onBack} />

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

                    <div className="p-4 md:p-5 bg-white/72 backdrop-blur-sm border-t border-[var(--color-cyan-main)]/10">
                        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,440px)_1fr] gap-4 md:gap-6 items-center">
                            <div>
                                <div className="flex items-center justify-between gap-4 mb-2">
                                    <div>
                                        <p className="text-base md:text-lg font-black text-[var(--color-cyan-dark)] tracking-tight">最大回合数</p>
                                    </div>
                                    <div className="px-4 py-2 rounded-2xl bg-[var(--color-cyan-dark)] text-[var(--color-yellow-main)] text-xl md:text-2xl font-black leading-none shadow-md tabular-nums min-w-[68px] md:min-w-[74px] text-center">
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
                                {!hasValidApiConfig && configChecked && (
                                    <p className="mt-3 text-xs md:text-sm font-black text-amber-700">
                                        {configErrorMessage || '还没有配置API哦，请先前往设置填写网关、模型和API Key。'}
                                    </p>
                                )}
                            </div>

                            <div className="flex flex-row items-stretch justify-end gap-3">
                                <button
                                    onClick={randomizeRoommates}
                                    className="w-full max-w-[60px] flex items-center justify-center gap-3 px-5 py-3.5 bg-white hover:bg-[var(--color-cyan-main)]/5 text-[var(--color-cyan-main)] text-sm font-black rounded-2xl border border-[var(--color-cyan-main)]/20 transition-all active:scale-95 group shadow-sm"
                                >
                                    <Dices size={18} className="transition-transform duration-500 group-hover:rotate-180" />
                                </button>

                                <StartGameButton
                                    disabled={!canStartGame}
                                    isLoading={isGameLoading}
                                    onClick={() => onStartGame(selectedRoommates, selectedMod, maxTurns)}
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
