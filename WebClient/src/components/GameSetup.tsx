import { useState, useEffect } from 'react';
import { gameApi } from '../api/gameApi';
import { useGameStore } from '../store/gameStore';
import { RefreshCw } from 'lucide-react';
import { SetupHeader } from './game/setup/SetupHeader';
import { ModPackSelector } from './game/setup/ModPackSelector';
import { RoommateSelector } from './game/setup/RoommateSelector';
import { StartGameButton } from './game/setup/StartGameButton';

interface GameSetupProps {
    onBack: () => void;
    onStartGame: (roommates: string[], modId?: string) => void;
    onTabChange: (tab: any) => void;
}

export const GameSetup = ({ onBack, onStartGame, onTabChange }: GameSetupProps) => {
    const [candidates, setCandidates] = useState<any[]>([]);
    const [workshopPacks, setWorkshopPacks] = useState<any[]>([]);
    const [selectedRoommates, setSelectedRoommates] = useState<string[]>([]);
    const [selectedMod, setSelectedMod] = useState<string>('default');
    const [isLoading, setIsLoading] = useState(true);
    const isGameLoading = useGameStore(state => state.isLoading);

    useEffect(() => {
        const loadSetupData = async () => {
            try {
                const [candRes, workRes] = await Promise.all([
                    gameApi.getCandidates(),
                    gameApi.getWorkshopList()
                ]);
                setCandidates(candRes.data || []);
                setWorkshopPacks(workRes.data || []);
            } catch (e) {
                console.error(e);
            } finally {
                setIsLoading(false);
            }
        };
        loadSetupData();
    }, []);

    const toggleRoommate = (id: string) => {
        setSelectedRoommates(prev => {
            if (prev.includes(id)) return prev.filter(i => i !== id);
            const next = [...prev, id];
            return next.length > 3 ? next.slice(1) : next;
        });
    };

    if (isLoading) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-12 bg-white/80 backdrop-blur-md rounded-3xl border-2 border-[var(--color-cyan-main)]/20 shadow-xl min-h-[500px]">
                <RefreshCw className="animate-spin text-[var(--color-cyan-main)] mb-4" size={48} />
                <p className="text-sm font-black text-[var(--color-cyan-main)] tracking-widest uppercase animate-pulse">正在调取档案库...</p>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col h-full bg-white/80 backdrop-blur-md rounded-3xl border-2 border-[var(--color-cyan-main)]/10 shadow-2xl overflow-hidden animate-fade-in-up">
            <SetupHeader onBack={onBack} isReady={selectedRoommates.length === 3} />

            <div className="flex-1 flex flex-col md:flex-row overflow-hidden bg-[var(--color-cyan-light)]/10">
                <ModPackSelector 
                    workshopPacks={workshopPacks} 
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

                    <StartGameButton 
                        disabled={selectedRoommates.length !== 3} 
                        isLoading={isGameLoading} 
                        onClick={() => onStartGame(selectedRoommates, selectedMod === 'default' ? undefined : selectedMod)} 
                    />
                </div>
            </div>
        </div>
    );
};
