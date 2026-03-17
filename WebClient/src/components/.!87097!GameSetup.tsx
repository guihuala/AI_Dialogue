import { useState, useEffect } from 'react';
import { gameApi } from '../api/gameApi';
import { UserCheck, Rocket, ArrowLeft, RefreshCw, Layers } from 'lucide-react';

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
        console.log(`Toggling roommate: ${id}`);
        setSelectedRoommates(prev => {
            if (prev.includes(id)) {
                return prev.filter(i => i !== id);
            }
            if (prev.length < 3) {
                return [...prev, id];
            }
            return prev;
        });
    };

    if (isLoading) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-12 bg-white rounded-3xl border-2 border-[var(--color-cyan-main)]/20 shadow-xl min-h-[500px]">
                 <RefreshCw className="animate-spin text-[var(--color-cyan-main)] mb-4" size={48} />
                 <p className="text-sm font-black text-[var(--color-cyan-main)] tracking-widest uppercase animate-pulse">正在调取档案库 (Loading System Assets)...</p>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col h-full bg-white rounded-3xl border-2 border-[var(--color-cyan-main)]/10 shadow-2xl overflow-hidden animate-fade-in-up">
            <div className="p-8 border-b-2 border-dashed border-[var(--color-cyan-main)]/10 flex items-center justify-between shrink-0 bg-white/50">
                <div className="flex items-center">
                    <button 
                        onClick={onBack}
                        className="mr-6 p-3 bg-white hover:bg-[var(--color-cyan-main)] hover:text-white rounded-xl transition-all shadow-sm border border-[var(--color-cyan-main)]/20 group"
                    >
                        <ArrowLeft size={20} className="group-hover:-translate-x-1 transition-transform" />
                    </button>
                    <div>
                        <h2 className="text-3xl font-black text-[var(--color-cyan-dark)] tracking-tight">对局前置初始化</h2>
                        <p className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.3em]">Game Session Initialization // Room 404</p>
                    </div>
                </div>
                {selectedRoommates.length === 3 && (
                    <div className="hidden md:flex items-center bg-[var(--color-yellow-main)]/20 px-4 py-2 rounded-full border border-[var(--color-yellow-main)]/30 animate-in zoom-in duration-300">
                        <span className="text-[10px] font-black text-[var(--color-yellow-dark)] uppercase tracking-widest">配置就绪 (Setup Ready)</span>
                    </div>
                )}
            </div>

            <div className="flex-1 flex flex-col md:flex-row overflow-hidden bg-[var(--color-cyan-light)]/10">
                {/* Mod Packs Section */}
                <div className="w-full md:w-80 bg-white border-r border-dashed border-[var(--color-cyan-main)]/20 p-6 flex flex-col shrink-0 overflow-y-auto custom-scrollbar">
                    <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] mb-6 flex items-center tracking-[0.2em] uppercase">
                        <Layers size={14} className="mr-2" /> 剧本与设定模组 (MOD SET)
                    </h3>
                    <div className="space-y-3 flex-1">
                        <div 
                            onClick={() => setSelectedMod('default')}
                            className={`p-4 rounded-xl cursor-pointer border-2 transition-all relative overflow-hidden group ${selectedMod === 'default' ? 'bg-[var(--color-cyan-dark)] border-[var(--color-cyan-dark)] text-white shadow-lg' : 'bg-white border-[var(--color-cyan-main)]/10 text-gray-600 hover:border-[var(--color-cyan-main)]'}`}
                        >
                            {selectedMod === 'default' && <div className="absolute top-0 right-0 w-8 h-8 bg-[var(--color-yellow-main)] flex items-center justify-center -rotate-45 translate-x-4 -translate-y-4 shadow-md text-black">✓</div>}
                            <h4 className="font-black text-sm">官方/默认设定</h4>
                            <p className="text-[9px] mt-1 opacity-60 font-bold uppercase tracking-tighter">Current Physical Files</p>
                        </div>
                        
                        {workshopPacks.map(pkg => (
                            <div 
                                key={pkg.id}
                                onClick={() => setSelectedMod(pkg.id)}
                                className={`p-4 rounded-xl cursor-pointer border-2 transition-all relative overflow-hidden group ${selectedMod === pkg.id ? 'bg-[var(--color-cyan-dark)] border-[var(--color-cyan-dark)] text-white shadow-lg' : 'bg-white border-[var(--color-cyan-main)]/10 text-gray-600 hover:border-[var(--color-cyan-main)]'}`}
                            >
                                {selectedMod === pkg.id && <div className="absolute top-0 right-0 w-8 h-8 bg-[var(--color-yellow-main)] flex items-center justify-center -rotate-45 translate-x-4 -translate-y-4 shadow-md text-black">✓</div>}
                                <h4 className="font-black text-sm truncate">{pkg.name}</h4>
                                <p className="text-[9px] mt-1 opacity-60 font-bold uppercase tracking-tighter">Author: {pkg.author}</p>
                            </div>
                        ))}
                    </div>

                    <button 
                        onClick={() => onTabChange('workshop')}
                        className="mt-6 flex items-center justify-center p-4 bg-[var(--color-cyan-light)] border-2 border-dashed border-[var(--color-cyan-main)]/30 text-[var(--color-cyan-main)] rounded-xl hover:bg-[var(--color-cyan-main)] hover:text-white transition-all text-[9px] font-black uppercase tracking-widest"
                    >
                        <RefreshCw size={12} className="mr-2" /> 发现更多模组 (BROWSE WORKSHOP)
                    </button>
                </div>

                {/* Roommate Selection Section */}
                <div className="flex-1 p-8 overflow-y-auto custom-scrollbar flex flex-col">
                    <div className="flex justify-between items-end mb-8">
                        <div>
                            <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] flex items-center tracking-[0.2em] uppercase mb-1">
                                <UserCheck size={14} className="mr-2" /> 选定舍友 (SELECT ROOMMATES)
                            </h3>
                            <p className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-tight">
                                404寝室需要 3 位性格迥异的生命体
                            </p>
                        </div>
                        <div className="text-right">
                            <div className="text-3xl font-black text-[var(--color-cyan-dark)]">{selectedRoommates.length}<span className="text-[var(--color-cyan-main)]/30">/3</span></div>
                            <div className="text-[8px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.1em]">已选员额 (Personnel)</div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
                        {candidates.map(char => {
                            const isSelected = selectedRoommates.includes(char.id);
                            return (
                                <div 
                                    key={char.id}
                                    onClick={() => toggleRoommate(char.id)}
                                    className={`group p-6 rounded-3xl border-2 cursor-pointer transition-all duration-300 relative overflow-hidden flex flex-col h-48 ${isSelected ? 'border-[var(--color-cyan-dark)] bg-white shadow-2xl shadow-[var(--color-cyan-main)]/10 -translate-y-1' : 'border-[var(--color-cyan-main)]/10 bg-white/60 hover:border-[var(--color-cyan-main)] hover:bg-white'}`}
                                >
                                    {isSelected && (
                                        <>
                                            <div className="absolute top-0 left-0 w-1.5 h-full bg-[var(--color-cyan-dark)]" />
                                            <div className="absolute top-4 right-4 w-6 h-6 bg-[var(--color-cyan-dark)] text-white rounded-full flex items-center justify-center text-[10px] font-black shadow-lg shadow-cyan-900/40 animate-in zoom-in-50 duration-200">
                                                ✓
                                            </div>
                                        </>
                                    )}
                                    <h4 className={`text-xl font-black mb-1 transition-colors ${isSelected ? 'text-[var(--color-cyan-dark)]' : 'text-gray-400 group-hover:text-[var(--color-cyan-dark)]'}`}>{char.name}</h4>
                                    <div className="flex flex-wrap gap-1 mb-4">
                                        {char.tags.map((t: string) => (
                                            <span key={t} className="text-[8px] bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)]/50 px-1.5 py-0.5 rounded font-black uppercase">{t}</span>
                                        ))}
                                    </div>
                                    <p className={`text-xs font-black leading-relaxed line-clamp-3 mt-auto ${isSelected ? 'text-[var(--color-cyan-dark)]/60' : 'text-gray-300 group-hover:text-gray-400'}`}>
                                        {char.description}
                                    </p>
                                </div>
                            );
                        })}
                    </div>

                    <div className="mt-auto flex justify-center pb-8 border-t border-dashed border-[var(--color-cyan-main)]/20 pt-12">
                        <button 
                            disabled={selectedRoommates.length !== 3}
                            onClick={() => onStartGame(selectedRoommates, selectedMod === 'default' ? undefined : selectedMod)}
                            className="group relative px-20 py-6 bg-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] text-white rounded-2xl font-black tracking-[0.4em] uppercase transition-all shadow-2xl shadow-cyan-900/40 hover:-translate-y-1 active:translate-y-0 disabled:opacity-10 disabled:grayscale disabled:hover:translate-y-0 disabled:cursor-not-allowed flex items-center overflow-hidden"
                        >
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:animate-shimmer" />
                            <Rocket className="mr-4 group-hover:animate-bounce" size={20} />
                            构建并注入对局 (INITIALIZE)
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
