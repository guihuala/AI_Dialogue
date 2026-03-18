import { useState, useEffect, useCallback, useMemo } from 'react';
import { Layers, Cloud, BookOpen, Trash2, Download, Play, Plus, RefreshCw, X, Check, Lock, Search, Edit3 } from 'lucide-react';
import { gameApi } from '../api/gameApi';

type TabType = 'library' | 'workshop';

interface ModManagerProps {
    onTabChange: (tab: any) => void;
}

export const ModManager = ({ onTabChange }: ModManagerProps) => {
    const [activeTab, setActiveTab] = useState<TabType>('library');
    const [libraryMods, setLibraryMods] = useState<any[]>([]);
    const [workshopMods, setWorkshopMods] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [toast, setToast] = useState('');
    
    // Save dialog state
    const [showSaveDialog, setShowSaveDialog] = useState(false);
    const [saveName, setSaveName] = useState('');
    const [saveDesc, setSaveDesc] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    // Action state
    const [actionTarget, setActionTarget] = useState<string | null>(null);

    const showToast = (msg: string) => {
        setToast(msg);
        setTimeout(() => setToast(''), 3000);
    };

    const loadLibrary = useCallback(async () => {
        setLoading(true);
        try {
            const res = await gameApi.getLibraryList();
            setLibraryMods(res.data || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, []);

    const loadWorkshop = useCallback(async () => {
        setLoading(true);
        try {
            const res = await gameApi.getWorkshopList();
            setWorkshopMods(res.data || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (activeTab === 'library') loadLibrary();
        else loadWorkshop();
    }, [activeTab, loadLibrary, loadWorkshop]);

    const handleSaveCurrent = async () => {
        if (!saveName.trim()) return;
        setIsSaving(true);
        try {
            await gameApi.saveToLibrary(saveName.trim(), saveDesc.trim());
            showToast(`✅ [${saveName}] 已保存到模组库`);
            setShowSaveDialog(false);
            setSaveName(''); setSaveDesc('');
            loadLibrary();
        } catch (e) {
            showToast('❌ 保存失败');
        } finally {
            setIsSaving(false);
        }
    };

    const handleApply = async (id: string, name: string) => {
        if (!window.confirm(`将应用模组 [${name}] 到当前活动环境。\n注意：新对局开启后，存档将与该模组绑定。\n\n确认继续？`)) return;
        setActionTarget(id);
        try {
            await gameApi.applyFromLibrary(id);
            showToast(`✅ [${name}] 已应用并完成热重载`);
        } catch (e) {
            showToast('❌ 应用失败');
        } finally {
            setActionTarget(null);
        }
    };

    const handleDelete = async (id: string, name: string) => {
        if (!window.confirm(`确定要删除模组 [${name}] 吗？`)) return;
        setActionTarget(`del-${id}`);
        try {
            await gameApi.deleteFromLibrary(id);
            showToast(`🗑 已删除 [${name}]`);
            loadLibrary();
        } catch (e) {
            showToast('❌ 删除失败');
        } finally {
            setActionTarget(null);
        }
    };

    const handleDownload = async (id: string, name: string) => {
        setActionTarget(`dl-${id}`);
        try {
            await gameApi.downloadWorkshopItem(id);
            showToast(`✅ [${name}] 已添加到库`);
            // Optional: switch to library or just show success
        } catch (e) {
            showToast('❌ 下载失败');
        } finally {
            setActionTarget(null);
        }
    };

    const filteredLibrary = useMemo(() => {
        const q = searchQuery.toLowerCase();
        return libraryMods.filter(m => m.name?.toLowerCase().includes(q) || m.description?.toLowerCase().includes(q));
    }, [libraryMods, searchQuery]);

    const filteredWorkshop = useMemo(() => {
        const q = searchQuery.toLowerCase();
        return workshopMods.filter(m => m.name?.toLowerCase().includes(q) || m.description?.toLowerCase().includes(q) || m.author?.toLowerCase().includes(q));
    }, [workshopMods, searchQuery]);

    return (
        <div className="flex-1 flex flex-col h-full bg-white/80 backdrop-blur-md rounded-2xl border-2 border-[var(--color-cyan-main)]/20 shadow-xl overflow-hidden p-8 relative animate-fade-in-up">
            {/* Toast Notification */}
            {toast && (
                <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50 px-6 py-3 bg-white border-2 border-[var(--color-cyan-main)]/20 rounded-full shadow-xl text-sm font-black text-[var(--color-cyan-dark)] animate-fade-in-up">
                    {toast}
                </div>
            )}

            {/* Header Area */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8">
                <div>
                    <h2 className="text-3xl font-black text-[var(--color-cyan-dark)] flex items-center tracking-tight">
                        <Layers className="mr-3 text-[var(--color-cyan-main)]" size={32} />
                        模组中心
                    </h2>
                    <p className="text-sm text-gray-400 font-bold mt-2 tracking-wide flex items-center gap-2">
                        <Lock size={14} className="text-amber-400" />
                        新游戏开始后，存档使用的模组将被锁定，无法在对局中途更改
                    </p>
                </div>

                <div className="flex items-center gap-4 w-full md:w-auto">
                    {/* Tab Switcher */}
                    <div className="flex bg-[var(--color-cyan-light)]/30 p-1 rounded-2xl border border-[var(--color-cyan-main)]/10">
                        <button
                            onClick={() => setActiveTab('library')}
                            className={`px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all flex items-center gap-2 ${activeTab === 'library' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-main)] hover:bg-white'}`}
                        >
                            <BookOpen size={14} /> 我的库
                        </button>
                        <button
                            onClick={() => setActiveTab('workshop')}
                            className={`px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all flex items-center gap-2 ${activeTab === 'workshop' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-main)] hover:bg-white'}`}
                        >
                            <Cloud size={14} /> 创意工坊
                        </button>
                    </div>

                    {/* Search */}
                    <div className="relative flex-1 md:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-cyan-main)]/50" size={18} />
                        <input
                            type="text"
                            placeholder="搜索模组..."
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2.5 bg-white border-2 border-[var(--color-cyan-main)]/10 rounded-2xl text-sm font-bold focus:border-[var(--color-cyan-main)] outline-none transition-all shadow-sm"
                        />
                    </div>

                    <button 
                        onClick={() => activeTab === 'library' ? loadLibrary() : loadWorkshop()}
                        className="p-3 bg-white border-2 border-[var(--color-cyan-main)]/10 text-[var(--color-cyan-main)] rounded-2xl hover:bg-[var(--color-cyan-main)] hover:text-white transition-all shadow-sm"
                    >
                        <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            {/* Action Bar */}
            {activeTab === 'library' && (
                <div className="mb-6 flex gap-4">
                    <button
                        onClick={() => setShowSaveDialog(true)}
                        className="flex items-center gap-2 px-6 py-3 bg-[var(--color-cyan-dark)] text-white rounded-2xl text-xs font-black uppercase tracking-widest hover:opacity-90 transition-all active:scale-95 shadow-lg"
                    >
                        <Plus size={16} /> 另存当前配置为新模组
                    </button>
                    <button
                        onClick={() => onTabChange('editor')}
                        className="flex items-center gap-2 px-6 py-3 bg-white border-2 border-[var(--color-cyan-main)]/20 text-[var(--color-cyan-main)] rounded-2xl text-xs font-black uppercase tracking-widest hover:bg-[var(--color-cyan-main)]/10 transition-all active:scale-95 shadow-sm"
                    >
                        <Edit3 size={16} /> 前往编辑器进行创作
                    </button>
                </div>
            )}

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto pr-4 custom-scrollbar">
                {loading && (activeTab === 'library' ? libraryMods.length === 0 : workshopMods.length === 0) ? (
                    <div className="flex flex-col items-center justify-center h-64 text-[var(--color-cyan-main)] animate-pulse">
                        <RefreshCw size={48} className="animate-spin mb-4 opacity-20" />
                        <span className="font-black uppercase tracking-widest text-xs">正在连接终端...</span>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 pb-8">
                        {activeTab === 'library' ? (
                            filteredLibrary.length === 0 ? (
                                <div className="col-span-full py-20 text-center text-gray-400 font-bold uppercase tracking-widest text-sm">
                                    暂无本地模组。你可以从工坊下载或手动保存。
                                </div>
                            ) : (
                                filteredLibrary.map(mod => (
                                    <div key={mod.id} className="group bg-white border-2 border-[var(--color-cyan-main)]/10 p-6 rounded-3xl shadow-sm hover:shadow-xl hover:border-[var(--color-cyan-main)]/30 transition-all flex flex-col relative overflow-hidden">
                                        <div className="flex justify-between items-start mb-3">
                                            <h3 className="font-black text-xl text-[var(--color-cyan-dark)] truncate">{mod.name}</h3>
                                            <span className="text-[10px] bg-gray-100 text-gray-400 px-2 py-1 rounded-lg font-black tracking-widest">{mod.timestamp?.split(' ')[0]}</span>
                                        </div>
                                        <p className="text-sm text-gray-500 font-semibold mb-6 line-clamp-2 min-h-[2.5rem] flex-1">
                                            {mod.description || '无描述'}
                                        </p>
                                        <div className="flex gap-3">
                                            <button
                                                onClick={() => handleApply(mod.id, mod.name)}
                                                disabled={actionTarget === mod.id}
                                                className="flex-1 py-3 bg-[var(--color-cyan-main)] text-white rounded-2xl flex items-center justify-center gap-2 font-black hover:bg-[var(--color-cyan-dark)] transition shadow-md uppercase tracking-widest text-xs disabled:opacity-50"
                                            >
                                                {actionTarget === mod.id ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
                                                应用此设置
                                            </button>
                                            <button
                                                onClick={() => handleDelete(mod.id, mod.name)}
                                                disabled={actionTarget === `del-${mod.id}`}
                                                className="p-3 bg-red-50 text-red-400 rounded-2xl hover:bg-red-500 hover:text-white transition shadow-sm disabled:opacity-50"
                                            >
                                                {actionTarget === `del-${mod.id}` ? <RefreshCw size={14} className="animate-spin" /> : <Trash2 size={16} />}
                                            </button>
                                        </div>
                                    </div>
                                ))
                            )
                        ) : (
                            filteredWorkshop.length === 0 ? (
                                <div className="col-span-full py-20 text-center text-gray-400 font-bold uppercase tracking-widest text-sm">
                                    工坊空空如也，快去发布第一个模组吧！
                                </div>
                            ) : (
                                filteredWorkshop.map(mod => (
                                    <div key={mod.id} className="group bg-white border-2 border-[var(--color-cyan-main)]/10 p-6 rounded-3xl shadow-sm hover:shadow-xl hover:border-[var(--color-cyan-main)]/30 transition-all flex flex-col">
                                        <div className="flex justify-between items-start mb-2 pr-6">
                                            <h3 className="font-black text-xl text-[var(--color-cyan-dark)] truncate">{mod.name}</h3>
                                        </div>
                                        <div className="mb-4">
                                            <span className="text-[10px] bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] px-3 py-1 rounded-full font-black tracking-widest uppercase">
                                                {mod.type === 'prompt_pack' ? '剧情包' : '独立角色'}
                                            </span>
                                        </div>
                                        <p className="text-sm text-gray-500 font-semibold mb-6 line-clamp-2 min-h-[2.5rem] flex-1">{mod.description}</p>
                                        <div className="flex justify-between items-center text-[10px] text-gray-400 font-black mb-4 uppercase tracking-widest">
                                            <span>作者: {mod.author}</span>
                                            <span className="flex items-center gap-1"><Download size={10} /> {mod.downloads} 下载</span>
                                        </div>
                                        <button
                                            onClick={() => handleDownload(mod.id, mod.name)}
                                            disabled={actionTarget === `dl-${mod.id}`}
                                            className="w-full py-4 bg-[var(--color-cyan-main)] text-white rounded-2xl flex items-center justify-center gap-2 font-black hover:bg-[var(--color-cyan-dark)] transition shadow-md uppercase tracking-widest text-xs disabled:opacity-50"
                                        >
                                            {actionTarget === `dl-${mod.id}` ? <RefreshCw size={14} className="animate-spin" /> : <Download size={16} />}
                                            下载到我的库
                                        </button>
                                    </div>
                                ))
                            )
                        )}
                    </div>
                )}
            </div>

            {/* Save Modal */}
            {showSaveDialog && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={() => setShowSaveDialog(false)}>
                    <div
                        className="bg-white rounded-[2rem] shadow-2xl p-8 w-full max-w-sm border-2 border-[var(--color-cyan-main)]/20 animate-scale-in"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-xl font-black text-gray-800">另存为模组</h3>
                            <button onClick={() => setShowSaveDialog(false)} className="text-gray-400 hover:text-black transition-colors">
                                <X size={24} />
                            </button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] block mb-2 ml-1">模组名称 *</label>
                                <input
                                    type="text"
                                    value={saveName}
                                    onChange={e => setSaveName(e.target.value)}
                                    placeholder="起个好听的名字..."
                                    className="w-full border-2 border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/10 rounded-2xl px-4 py-3 text-sm font-bold outline-none focus:border-[var(--color-cyan-main)] transition-all"
                                />
                            </div>
                            <div>
                                <label className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] block mb-2 ml-1">简介（选填）</label>
                                <textarea
                                    value={saveDesc}
                                    onChange={e => setSaveDesc(e.target.value)}
                                    placeholder="介绍一下这个配置..."
                                    rows={3}
                                    className="w-full border-2 border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/10 rounded-2xl px-4 py-3 text-sm font-bold outline-none focus:border-[var(--color-cyan-main)] transition-all resize-none"
                                />
                            </div>
                            <button
                                onClick={handleSaveCurrent}
                                disabled={!saveName.trim() || isSaving}
                                className="w-full py-4 bg-[var(--color-cyan-dark)] disabled:opacity-50 text-white rounded-2xl text-sm font-black uppercase tracking-widest flex items-center justify-center gap-2 shadow-lg hover:translate-y-[-2px] transition-all"
                            >
                                {isSaving ? <RefreshCw size={16} className="animate-spin" /> : <Check size={16} />}
                                {isSaving ? '正在打包...' : '确认保存'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
