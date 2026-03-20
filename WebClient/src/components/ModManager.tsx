import { useState, useEffect, useCallback, useMemo } from 'react';
import { Layers, Cloud, BookOpen, Trash2, Download, Plus, RefreshCw, X, Check, Lock, Search, Edit3, RotateCcw, ShieldCheck } from 'lucide-react';
import { gameApi } from '../api/gameApi';
import { ConfirmDialog } from './common/ConfirmDialog';

type TabType = 'library' | 'workshop';

interface ModManagerProps {
    onTabChange: (tab: any) => void;
}

export const ModManager = ({ onTabChange }: ModManagerProps) => {
    const [libraryFilter, setLibraryFilter] = useState<'all' | 'original' | 'downloaded' | 'public'>('all');
    const [librarySort, setLibrarySort] = useState<'updated' | 'name'>('updated');
    const [workshopFilter, setWorkshopFilter] = useState<'all' | 'original' | 'forked' | 'mine'>('all');
    const [workshopSort, setWorkshopSort] = useState<'updated' | 'downloads' | 'name'>('updated');
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
    const [confirmDialog, setConfirmDialog] = useState<{
        open: boolean;
        title: string;
        message: string;
        confirmText?: string;
        danger?: boolean;
        onConfirm?: () => Promise<void> | void;
    }>({ open: false, title: '', message: '' });

    // Action state
    const [actionTarget, setActionTarget] = useState<string | null>(null);
    const [userState, setUserState] = useState<any>(null);
    const [snapshots, setSnapshots] = useState<any[]>([]);
    const [selectedWorkshopMod, setSelectedWorkshopMod] = useState<any | null>(null);

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

    const loadSafetyData = useCallback(async () => {
        try {
            const [stateRes, snapsRes] = await Promise.all([
                gameApi.getUserState(),
                gameApi.getSnapshots()
            ]);
            setUserState(stateRes?.data || null);
            setSnapshots(snapsRes?.data || []);
        } catch (e) {
            console.warn('Failed to load safety data', e);
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

    useEffect(() => {
        loadSafetyData();
    }, [loadSafetyData]);

    const handleSaveCurrent = async () => {
        if (!saveName.trim()) return;
        setIsSaving(true);
        try {
            await gameApi.saveToLibrary(saveName.trim(), saveDesc.trim());
            showToast(`✅ [${saveName}] 已保存到模组库`);
            setShowSaveDialog(false);
            setSaveName(''); setSaveDesc('');
            loadLibrary();
            loadSafetyData();
        } catch (e) {
            showToast('❌ 保存失败');
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async (id: string, name: string) => {
        setConfirmDialog({
            open: true,
            title: '删除模组',
            message: `确定要删除模组 [${name}] 吗？`,
            confirmText: '确认删除',
            danger: true,
            onConfirm: async () => {
                setActionTarget(`del-${id}`);
                try {
                    await gameApi.deleteFromLibrary(id);
                    showToast(`🗑 已删除 [${name}]`);
                    loadLibrary();
                    loadSafetyData();
                } catch (e) {
                    showToast('❌ 删除失败');
                } finally {
                    setActionTarget(null);
                }
            }
        });
    };

    const handleDownload = async (id: string, name: string) => {
        setActionTarget(`dl-${id}`);
        try {
            await gameApi.downloadWorkshopItem(id);
            showToast(`✅ [${name}] 已添加到库`);
            loadLibrary();
            loadSafetyData();
            // Optional: switch to library or just show success
        } catch (e) {
            showToast('❌ 下载失败');
        } finally {
            setActionTarget(null);
        }
    };

    const handleEdit = async (id: string, name: string) => {
        setActionTarget(`edit-${id}`);
        try {
            await gameApi.selectLibraryItemForEdit(id);
            showToast(`✍️ 正在编辑 [${name}]`);
            onTabChange('editor');
        } catch (e) {
            const detail = (e as any)?.response?.data?.detail || '切换编辑目标失败';
            showToast(`❌ ${detail}`);
        } finally {
            setActionTarget(null);
        }
    };

    const handleViewDefault = async () => {
        setActionTarget('edit-default');
        try {
            await gameApi.selectDefaultForEdit();
            showToast('📘 正在查看默认模组');
            onTabChange('editor');
        } catch (e) {
            const detail = (e as any)?.response?.data?.detail || '切换默认模组失败';
            showToast(`❌ ${detail}`);
        } finally {
            setActionTarget(null);
        }
    };

    const handleRollback = async (snapshotId: string) => {
        setConfirmDialog({
            open: true,
            title: '回滚配置',
            message: `将回滚到快照 ${snapshotId}，当前活动配置会被覆盖。确认继续？`,
            confirmText: '确认回滚',
            danger: true,
            onConfirm: async () => {
                setActionTarget(`rb-${snapshotId}`);
                try {
                    await gameApi.rollbackSnapshot(snapshotId);
                    showToast(`✅ 已回滚到 ${snapshotId}`);
                    loadSafetyData();
                } catch (e) {
                    const detail = (e as any)?.response?.data?.detail || '回滚失败';
                    showToast(`❌ ${detail}`);
                } finally {
                    setActionTarget(null);
                }
            }
        });
    };

    const filteredLibrary = useMemo(() => {
        const q = searchQuery.toLowerCase();
        const defaultMod = {
            id: 'default',
            name: '默认模组',
            description: '官方默认内容，只可查看，不能直接覆盖。若要微调，请另存为新的本地模组。',
            timestamp: '系统内置',
            visibility: 'readonly',
            isDefault: true,
            source_type: 'system',
            version: 1
        };
        const merged = [defaultMod, ...libraryMods];
        const filtered = merged.filter((m) => {
            const matchesSearch = m.name?.toLowerCase().includes(q) || m.description?.toLowerCase().includes(q);
            if (!matchesSearch) return false;
            if (libraryFilter === 'original') return !!m.isDefault || (m.source_type !== 'downloaded' && m.source_type !== 'forked');
            if (libraryFilter === 'downloaded') return m.source_type === 'downloaded';
            if (libraryFilter === 'public') return m.visibility === 'public';
            return true;
        });
        return filtered.sort((a, b) => {
            if (a.isDefault) return -1;
            if (b.isDefault) return 1;
            if (librarySort === 'name') return String(a.name || '').localeCompare(String(b.name || ''));
            return String(b.updated_at || b.timestamp || '').localeCompare(String(a.updated_at || a.timestamp || ''));
        });
    }, [libraryMods, searchQuery, libraryFilter, librarySort]);

    const filteredWorkshop = useMemo(() => {
        const q = searchQuery.toLowerCase();
        const filtered = workshopMods.filter((m) => {
            const matchesSearch = m.name?.toLowerCase().includes(q) || m.description?.toLowerCase().includes(q) || m.author?.toLowerCase().includes(q);
            if (!matchesSearch) return false;
            if (workshopFilter === 'original') return m.source_type !== 'forked';
            if (workshopFilter === 'forked') return m.source_type === 'forked';
            if (workshopFilter === 'mine') return !!m.is_owned_by_current_user;
            return true;
        });
        return filtered.sort((a, b) => {
            if (workshopSort === 'name') return String(a.name || '').localeCompare(String(b.name || ''));
            if (workshopSort === 'downloads') return Number(b.downloads || 0) - Number(a.downloads || 0);
            return String(b.updated_at || b.timestamp || '').localeCompare(String(a.updated_at || a.timestamp || ''));
        });
    }, [workshopMods, searchQuery, workshopFilter, workshopSort]);

    const getWorkshopFocusTags = (mod: any) => {
        const summary = mod?.summary || {};
        const tags: string[] = [];
        const characterCount = Number(summary.character_count || 0);
        const skillCount = Number(summary.skill_count || 0);
        const csvCount = Number(summary.csv_files || 0);
        const worldCount = Number(summary.world_count || 0);

        if (characterCount >= 4) tags.push('偏角色向');
        if (csvCount >= 3) tags.push('偏剧情向');
        if (skillCount >= 2 || worldCount >= 3) tags.push('偏系统向');
        if (tags.length === 0) {
            if (characterCount >= Math.max(skillCount, csvCount)) tags.push('轻角色向');
            else if (csvCount >= Math.max(characterCount, skillCount)) tags.push('轻剧情向');
            else tags.push('轻系统向');
        }
        return tags.slice(0, 3);
    };

    const getSourceLabel = (sourceType?: string) => {
        if (sourceType === 'downloaded') return '下载副本';
        if (sourceType === 'forked') return '派生作品';
        return '原创';
    };

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

            <div className="mb-6 flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
                <div className="flex flex-wrap gap-2">
                    {activeTab === 'library' ? (
                        <>
                            <button onClick={() => setLibraryFilter('all')} className={`px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-widest border ${libraryFilter === 'all' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>全部</button>
                            <button onClick={() => setLibraryFilter('original')} className={`px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-widest border ${libraryFilter === 'original' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>原创</button>
                            <button onClick={() => setLibraryFilter('downloaded')} className={`px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-widest border ${libraryFilter === 'downloaded' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>下载副本</button>
                            <button onClick={() => setLibraryFilter('public')} className={`px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-widest border ${libraryFilter === 'public' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>已公开</button>
                        </>
                    ) : (
                        <>
                            <button onClick={() => setWorkshopFilter('all')} className={`px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-widest border ${workshopFilter === 'all' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>全部</button>
                            <button onClick={() => setWorkshopFilter('original')} className={`px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-widest border ${workshopFilter === 'original' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>原创</button>
                            <button onClick={() => setWorkshopFilter('forked')} className={`px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-widest border ${workshopFilter === 'forked' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>派生</button>
                            <button onClick={() => setWorkshopFilter('mine')} className={`px-4 py-2 rounded-full text-[10px] font-black uppercase tracking-widest border ${workshopFilter === 'mine' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>我的作品</button>
                        </>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] font-black uppercase tracking-widest text-gray-400">排序</span>
                    {activeTab === 'library' ? (
                        <select value={librarySort} onChange={(e) => setLibrarySort(e.target.value as 'updated' | 'name')} className="px-3 py-2 rounded-xl border-2 border-[var(--color-cyan-main)]/10 bg-white text-[11px] font-black text-[var(--color-cyan-dark)] outline-none">
                            <option value="updated">最近更新</option>
                            <option value="name">名称</option>
                        </select>
                    ) : (
                        <select value={workshopSort} onChange={(e) => setWorkshopSort(e.target.value as 'updated' | 'downloads' | 'name')} className="px-3 py-2 rounded-xl border-2 border-[var(--color-cyan-main)]/10 bg-white text-[11px] font-black text-[var(--color-cyan-dark)] outline-none">
                            <option value="updated">最近更新</option>
                            <option value="downloads">下载量</option>
                            <option value="name">名称</option>
                        </select>
                    )}
                </div>
            </div>

            {activeTab === 'library' && (
                <div className="mb-6 grid grid-cols-1 xl:grid-cols-2 gap-4">
                    <div className="bg-white border-2 border-[var(--color-cyan-main)]/10 rounded-2xl p-4">
                        <div className="text-[11px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] flex items-center gap-2">
                            <ShieldCheck size={14} />
                            当前编辑目标
                        </div>
                        <div className="mt-3 text-sm font-bold text-[var(--color-cyan-dark)]">
                            来源：{userState?.editor_source || 'default'} · 模组：{userState?.editor_mod_id || 'default'}
                        </div>
                        <div className="text-[11px] mt-1 text-gray-400 font-black">
                            这里只表示编辑器当前正在改哪份内容；真正用于游戏的模组会在新游戏开始时读取
                        </div>
                        <div className="text-[11px] mt-1 text-gray-400 font-black">
                            最近更新时间：{userState?.updated_at || '-'} · 最近安全快照：{userState?.last_good_snapshot_id || '-'}
                        </div>
                    </div>
                    <div className="bg-white border-2 border-[var(--color-cyan-main)]/10 rounded-2xl p-4">
                        <div className="text-[11px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] flex items-center gap-2">
                            <RotateCcw size={14} />
                            快照回滚
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                            {snapshots.slice(0, 4).map((s: any) => (
                                <button
                                    key={s.id}
                                    onClick={() => handleRollback(s.id)}
                                    disabled={actionTarget === `rb-${s.id}`}
                                    className="px-3 py-1.5 rounded-full text-[10px] font-black tracking-widest uppercase bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] border border-[var(--color-cyan-main)]/20 hover:bg-white transition-all disabled:opacity-50"
                                >
                                    {actionTarget === `rb-${s.id}` ? '回滚中...' : `回滚 ${s.id}`}
                                </button>
                            ))}
                            {snapshots.length === 0 && (
                                <span className="text-xs text-gray-400 font-bold">暂无快照</span>
                            )}
                        </div>
                    </div>
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
                                        <div className="mb-4 flex flex-wrap gap-2">
                                            <span className="px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] border border-[var(--color-cyan-main)]/20">
                                                {mod.isDefault ? '只读模板' : '开局可选'}
                                            </span>
                                            {mod.isDefault && (
                                                <span className="px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase bg-amber-50 text-amber-600 border border-amber-200">
                                                    修改请另存为
                                                </span>
                                            )}
                                            {mod.visibility === 'public' && !mod.isDefault && (
                                                <span className="px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase bg-emerald-50 text-emerald-600 border border-emerald-200">
                                                    已公开同步
                                                </span>
                                            )}
                                            {!mod.isDefault && (
                                                <span className="px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase bg-white border border-[var(--color-cyan-main)]/15 text-[var(--color-cyan-main)]">
                                                    {getSourceLabel(mod.source_type)} · v{mod.version || 1}
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex gap-3">
                                            <button
                                                onClick={() => mod.isDefault ? handleViewDefault() : handleEdit(mod.id, mod.name)}
                                                disabled={actionTarget === `edit-${mod.id}`}
                                                className="flex-1 py-3 bg-white border-2 border-[var(--color-cyan-main)]/20 text-[var(--color-cyan-main)] rounded-2xl flex items-center justify-center gap-2 font-black hover:bg-[var(--color-cyan-main)]/10 transition shadow-sm uppercase tracking-widest text-xs disabled:opacity-50"
                                            >
                                                {actionTarget === `edit-${mod.id}` ? <RefreshCw size={14} className="animate-spin" /> : <Edit3 size={14} />}
                                                {mod.isDefault ? '查看默认内容' : '编辑这个模组'}
                                            </button>
                                            {!mod.isDefault && (
                                                <button
                                                    onClick={() => handleDelete(mod.id, mod.name)}
                                                    disabled={actionTarget === `del-${mod.id}`}
                                                    className="p-3 bg-red-50 text-red-400 rounded-2xl hover:bg-red-500 hover:text-white transition shadow-sm disabled:opacity-50"
                                                >
                                                    {actionTarget === `del-${mod.id}` ? <RefreshCw size={14} className="animate-spin" /> : <Trash2 size={16} />}
                                                </button>
                                            )}
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
                                        <div className="mb-4 flex flex-wrap gap-2">
                                            {mod.is_owned_by_current_user ? (
                                                <span className="px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase bg-emerald-50 text-emerald-600 border border-emerald-200">
                                                    我的公开模组
                                                </span>
                                            ) : (
                                                <span className="px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] border border-[var(--color-cyan-main)]/20">
                                                    下载后可在开局选择
                                                </span>
                                            )}
                                            <span className="px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase bg-white border border-[var(--color-cyan-main)]/15 text-[var(--color-cyan-main)]">
                                                {getSourceLabel(mod.source_type)} · v{mod.version || 1}
                                            </span>
                                        </div>
                                        <button
                                            onClick={() => setSelectedWorkshopMod(mod)}
                                            className="mb-4 w-full py-3 bg-white border-2 border-[var(--color-cyan-main)]/10 text-[var(--color-cyan-main)] rounded-2xl font-black hover:bg-[var(--color-cyan-main)]/10 transition shadow-sm uppercase tracking-widest text-xs"
                                        >
                                            查看详情
                                        </button>
                                        <button
                                            onClick={() => handleDownload(mod.id, mod.name)}
                                            disabled={actionTarget === `dl-${mod.id}`}
                                            className="w-full py-4 bg-[var(--color-cyan-main)] text-white rounded-2xl flex items-center justify-center gap-2 font-black hover:bg-[var(--color-cyan-dark)] transition shadow-md uppercase tracking-widest text-xs disabled:opacity-50"
                                        >
                                            {actionTarget === `dl-${mod.id}` ? <RefreshCw size={14} className="animate-spin" /> : <Download size={16} />}
                                            {mod.is_owned_by_current_user ? '查看我的库副本' : '下载到我的库'}
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

            {selectedWorkshopMod && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={() => setSelectedWorkshopMod(null)}>
                    <div
                        className="bg-white rounded-[2rem] shadow-2xl p-8 w-full max-w-2xl border-2 border-[var(--color-cyan-main)]/20 animate-scale-in"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="flex items-start justify-between gap-6 mb-6">
                            <div className="min-w-0">
                                <div className="flex flex-wrap gap-2 mb-3">
                                    <span className="text-[10px] bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] px-3 py-1 rounded-full font-black tracking-widest uppercase">
                                        {selectedWorkshopMod.type === 'prompt_pack' ? '剧情包' : '独立角色'}
                                    </span>
                                    {getWorkshopFocusTags(selectedWorkshopMod).map((tag) => (
                                        <span key={tag} className="text-[10px] bg-amber-50 text-amber-700 px-3 py-1 rounded-full font-black tracking-widest uppercase border border-amber-200">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                                <h3 className="text-3xl font-black text-[var(--color-cyan-dark)] tracking-tight break-words">
                                    {selectedWorkshopMod.name}
                                </h3>
                                <div className="mt-2 text-sm font-bold text-gray-500">
                                    作者：{selectedWorkshopMod.author} · 下载：{selectedWorkshopMod.downloads} · 版本：v{selectedWorkshopMod.version || 1}
                                </div>
                            </div>
                            <button onClick={() => setSelectedWorkshopMod(null)} className="text-gray-400 hover:text-black transition-colors shrink-0">
                                <X size={24} />
                            </button>
                        </div>

                        <div className="mb-6 rounded-2xl border border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/20 p-5">
                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] mb-3">
                                基本信息
                            </div>
                            <div className="mb-4 flex flex-wrap gap-2">
                                <span className="text-[10px] bg-white text-[var(--color-cyan-main)] px-3 py-1 rounded-full font-black tracking-widest uppercase border border-[var(--color-cyan-main)]/15">
                                    {getSourceLabel(selectedWorkshopMod.source_type)}
                                </span>
                                {selectedWorkshopMod.published_at && (
                                    <span className="text-[10px] bg-white text-gray-500 px-3 py-1 rounded-full font-black tracking-widest uppercase border border-gray-200">
                                        首次公开：{String(selectedWorkshopMod.published_at).split(' ')[0]}
                                    </span>
                                )}
                                {selectedWorkshopMod.updated_at && (
                                    <span className="text-[10px] bg-white text-gray-500 px-3 py-1 rounded-full font-black tracking-widest uppercase border border-gray-200">
                                        最近更新：{String(selectedWorkshopMod.updated_at).split(' ')[0]}
                                    </span>
                                )}
                            </div>
                            <p className="text-sm text-gray-600 font-semibold leading-7">
                                {selectedWorkshopMod.description || '作者还没有填写模组简介。'}
                            </p>
                        </div>

                        <div className="mb-8 rounded-2xl border border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/25 p-5">
                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] mb-3">
                                模组概要
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[11px] font-bold text-[var(--color-cyan-dark)]">
                                <div className="rounded-xl bg-white/85 px-3 py-3">
                                    角色：{selectedWorkshopMod.summary?.character_count ?? 0}
                                </div>
                                <div className="rounded-xl bg-white/85 px-3 py-3">
                                    技能：{selectedWorkshopMod.summary?.skill_count ?? 0}
                                </div>
                                <div className="rounded-xl bg-white/85 px-3 py-3">
                                    世界文件：{selectedWorkshopMod.summary?.world_count ?? 0}
                                </div>
                                <div className="rounded-xl bg-white/85 px-3 py-3">
                                    事件文件：{selectedWorkshopMod.summary?.csv_files ?? 0}
                                </div>
                            </div>
                            <div className="mt-3 text-[10px] text-gray-400 font-black">
                                共包含 {(selectedWorkshopMod.summary?.md_files ?? 0) + (selectedWorkshopMod.summary?.csv_files ?? 0)} 个内容文件
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <button
                                onClick={() => setSelectedWorkshopMod(null)}
                                className="flex-1 py-4 bg-white border-2 border-[var(--color-cyan-main)]/15 text-[var(--color-cyan-main)] rounded-2xl font-black uppercase tracking-widest hover:bg-[var(--color-cyan-main)]/10 transition-all"
                            >
                                关闭
                            </button>
                            <button
                                onClick={async () => {
                                    await handleDownload(selectedWorkshopMod.id, selectedWorkshopMod.name);
                                    setSelectedWorkshopMod(null);
                                }}
                                disabled={actionTarget === `dl-${selectedWorkshopMod.id}`}
                                className="flex-[1.3] py-4 bg-[var(--color-cyan-main)] text-white rounded-2xl flex items-center justify-center gap-2 font-black hover:bg-[var(--color-cyan-dark)] transition shadow-md uppercase tracking-widest text-xs disabled:opacity-50"
                            >
                                {actionTarget === `dl-${selectedWorkshopMod.id}` ? <RefreshCw size={14} className="animate-spin" /> : <Download size={16} />}
                                {selectedWorkshopMod.is_owned_by_current_user ? '查看我的库副本' : '下载到我的库'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <ConfirmDialog
                open={confirmDialog.open}
                title={confirmDialog.title}
                message={confirmDialog.message}
                confirmText={confirmDialog.confirmText || '确认'}
                danger={!!confirmDialog.danger}
                onCancel={() => setConfirmDialog({ open: false, title: '', message: '' })}
                onConfirm={async () => {
                    const handler = confirmDialog.onConfirm;
                    setConfirmDialog({ open: false, title: '', message: '' });
                    if (handler) await handler();
                }}
            />
        </div>
    );
};
