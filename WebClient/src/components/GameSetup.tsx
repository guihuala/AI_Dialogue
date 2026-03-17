import { useState, useEffect } from 'react';
import { gameApi } from '../api/gameApi';
import { UserCheck, Rocket, ArrowLeft, RefreshCw, Layers, Cloud } from 'lucide-react';

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
        setSelectedRoommates(prev => {
            if (prev.includes(id)) {
                return prev.filter(i => i !== id);
            }
            const next = [...prev, id];
            if (next.length > 3) {
                return next.slice(1); // Replace oldest selection
            }
            return next;
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
                        <p className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.3em]">Room 404</p>
                    </div>
                </div>
                {selectedRoommates.length === 3 && (
                    <div className="hidden md:flex items-center bg-[var(--color-yellow-main)]/20 px-4 py-2 rounded-full border border-[var(--color-yellow-main)]/30 animate-in zoom-in duration-300">
                        <span className="text-[10px] font-black text-[var(--color-yellow-dark)] uppercase tracking-widest">配置就绪</span>
                    </div>
                )}
            </div>

            <div className="flex-1 flex flex-col md:flex-row overflow-hidden bg-[var(--color-cyan-light)]/10">
                {/* Mod Packs Section */}
                <div className="w-full md:w-80 bg-white/60 border-r border-dashed border-[var(--color-cyan-main)]/20 p-6 flex flex-col shrink-0 overflow-y-auto custom-scrollbar">
                    <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] mb-6 flex items-center tracking-[0.2em] uppercase">
                        <Layers size={14} className="mr-2" /> 剧本与设定模组
                    </h3>
                    <div className="space-y-3 flex-1">
                        <div 
                            onClick={() => setSelectedMod('default')}
                            className={`p-4 rounded-xl cursor-pointer border-2 transition-all relative overflow-hidden group ${selectedMod === 'default' ? 'bg-[var(--color-cyan-dark)] border-[var(--color-cyan-dark)] text-white shadow-lg' : 'bg-white/80 border-[var(--color-cyan-main)]/10 text-gray-600 hover:border-[var(--color-cyan-main)]'}`}
                        >
                            {selectedMod === 'default' && <div className="absolute top-0 right-0 w-8 h-8 bg-[var(--color-yellow-main)] flex items-center justify-center -rotate-45 translate-x-4 -translate-y-4 shadow-md text-black font-bold">✓</div>}
                            <h4 className="font-black text-sm">官方/默认设定</h4>
                            <p className="text-[9px] mt-1 opacity-60 font-bold uppercase tracking-tighter">Current Physical Files</p>
                        </div>
                        
                        {workshopPacks.map(pkg => (
                            <div 
                                key={pkg.id}
                                onClick={() => setSelectedMod(pkg.id)}
                                className={`p-4 rounded-xl cursor-pointer border-2 transition-all relative overflow-hidden group ${selectedMod === pkg.id ? 'bg-[var(--color-cyan-dark)] border-[var(--color-cyan-dark)] text-white shadow-lg' : 'bg-white/80 border-[var(--color-cyan-main)]/10 text-gray-600 hover:border-[var(--color-cyan-main)]'}`}
                            >
                                {selectedMod === pkg.id && <div className="absolute top-0 right-0 w-8 h-8 bg-[var(--color-yellow-main)] flex items-center justify-center -rotate-45 translate-x-4 -translate-y-4 shadow-md text-black font-bold">✓</div>}
                                <h4 className="font-black text-sm truncate">{pkg.name}</h4>
                                <p className="text-[9px] mt-1 opacity-60 font-bold uppercase tracking-tighter">Author: {pkg.author}</p>
                            </div>
                        ))}
                    </div>

                    <button 
                        onClick={() => onTabChange('workshop')}
                        className="mt-6 flex items-center justify-center p-4 bg-white/60 border-2 border-dashed border-[var(--color-cyan-main)]/30 text-[var(--color-cyan-main)] rounded-xl hover:bg-[var(--color-cyan-main)] hover:text-white transition-all text-[9px] font-black uppercase tracking-widest"
                    >
                        <Cloud size={14} className="mr-2" /> 发现更多模组
                    </button>
                </div>

                {/* Roommate Selection Section */}
                <div className="flex-1 p-8 overflow-y-auto custom-scrollbar flex flex-col">
                    <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
                        <div>
                            <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] flex items-center tracking-[0.2em] uppercase mb-1">
                                <UserCheck size={14} className="mr-2" /> 选定舍友
                            </h3>
                            <p className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-tight">
                                404寝室需要 <span className="text-[var(--color-cyan-main)] px-2 bg-white rounded shadow-sm">3</span> 位性格迥异的生命体
                            </p>
                        </div>
                        <div className="flex items-center gap-6">
                            <div className="text-right">
                                <div className="text-3xl font-black text-[var(--color-cyan-dark)]">{selectedRoommates.length}<span className="text-[var(--color-cyan-main)]/30">/3</span></div>
                                <div className="text-[8px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.1em]">已选员额</div>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
                        {candidates.map(char => {
                            const isSelected = selectedRoommates.includes(char.id);
                            return (
                                <div 
                                    key={char.id}
                                    onClick={() => toggleRoommate(char.id)}
                                    className={`group p-1 rounded-[2rem] border-2 cursor-pointer transition-all duration-500 relative overflow-hidden flex flex-col h-64 ${isSelected ? 'border-[var(--color-cyan-main)] bg-white shadow-[0_0_30px_rgba(0,188,212,0.15)] -translate-y-2' : 'border-[var(--color-cyan-main)]/10 bg-white/40 hover:border-[var(--color-cyan-main)]/30 hover:bg-white/60'}`}
                                >
                                    <div className="relative flex-1 rounded-[1.8rem] overflow-hidden bg-slate-100/50">
                                        {/* Avatar Background */}
                                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent z-10 opacity-60 group-hover:opacity-80 transition-opacity" />
                                        
                                        {/* Avatar Image */}
                                        {char.avatar ? (
                                            <img 
                                                src={char.avatar} 
                                                alt={char.name}
                                                className={`w-full h-full object-cover transition-transform duration-700 ${isSelected ? 'scale-110' : 'group-hover:scale-105'}`}
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)]">
                                                <UserCheck size={48} opacity={0.2} />
                                            </div>
                                        )}

                                        {/* Name and Tags Overlay */}
                                        <div className="absolute bottom-0 left-0 right-0 p-5 z-20">
                                            <div className="flex flex-wrap gap-1 mb-2">
                                                {char.tags.map((t: string) => (
                                                    <span key={t} className="text-[7px] bg-white/20 backdrop-blur-md text-white px-2 py-0.5 rounded-full font-black uppercase tracking-widest border border-white/10">{t}</span>
                                                ))}
                                            </div>
                                            <h4 className="text-xl font-black text-white tracking-tight drop-shadow-md">{char.name}</h4>
                                        </div>

                                        {/* Selection Indicators */}
                                        {isSelected && (
                                            <div className="absolute top-4 right-4 w-8 h-8 bg-[var(--color-cyan-main)] text-white rounded-full flex items-center justify-center shadow-lg border-2 border-white z-30 animate-in zoom-in-50 duration-300">
                                                <UserCheck size={16} />
                                            </div>
                                        )}
                                    </div>

                                    <div className="p-4 px-6 shrink-0">
                                        <p className={`text-[10px] font-bold leading-relaxed line-clamp-2 transition-colors ${isSelected ? 'text-[var(--color-cyan-dark)]' : 'text-slate-400'}`}>
                                            {char.description}
                                        </p>
                                    </div>
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
                            构建并注入对局
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
