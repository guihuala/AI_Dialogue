import { useState, useEffect, useCallback, useMemo } from 'react';
import { Cloud, BookOpen, Trash2, Download, Plus, RefreshCw, X, Check, Search, Edit3 } from 'lucide-react';
import { gameApi } from '../api/gameApi';
import { ConfirmDialog } from './common/ConfirmDialog';
import { WorkshopModDetailModal } from './mods/WorkshopModDetailModal';

type TabType = 'library' | 'workshop';

interface ModManagerProps {
    onTabChange: (tab: any) => void;
}

interface ListPagination {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
}

const EMPTY_PAGINATION: ListPagination = {
    page: 1,
    page_size: 12,
    total: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false
};

export const ModManager = ({ onTabChange }: ModManagerProps) => {
    const [libraryFilter, setLibraryFilter] = useState<'all' | 'original' | 'downloaded' | 'public'>('all');
    const [librarySort, setLibrarySort] = useState<'updated' | 'name'>('updated');
    const [workshopFilter, setWorkshopFilter] = useState<'all' | 'original' | 'forked' | 'mine'>('all');
    const [workshopSort, setWorkshopSort] = useState<'updated' | 'downloads' | 'name'>('updated');
    const [activeTab, setActiveTab] = useState<TabType>('library');
    const [libraryMods, setLibraryMods] = useState<any[]>([]);
    const [libraryCatalogMods, setLibraryCatalogMods] = useState<any[]>([]);
    const [workshopMods, setWorkshopMods] = useState<any[]>([]);
    const [libraryPagination, setLibraryPagination] = useState<ListPagination>(EMPTY_PAGINATION);
    const [workshopPagination, setWorkshopPagination] = useState<ListPagination>(EMPTY_PAGINATION);
    const [libraryPage, setLibraryPage] = useState(1);
    const [workshopPage, setWorkshopPage] = useState(1);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
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
    const [selectedWorkshopMod, setSelectedWorkshopMod] = useState<any | null>(null);
    const [accountInfo, setAccountInfo] = useState<any>(null);

    const defaultTemplateMod = useMemo(() => ({
        id: 'default',
        name: '默认模组',
        description: '官方默认内容模板，只可查看，不能直接覆盖。若要微调，请先另存为你的本地模组。',
        timestamp: '系统内置',
        visibility: 'readonly',
        isDefault: true,
        source_type: 'system',
        version: 1
    }), []);

    const canPublishWorkshopMods = !!accountInfo?.capabilities?.can_publish_workshop_mods;

    const showToast = (msg: string) => {
        setToast(msg);
        setTimeout(() => setToast(''), 3000);
    };

    useEffect(() => {
        const timer = window.setTimeout(() => {
            setDebouncedSearchQuery(searchQuery.trim());
        }, 250);
        return () => window.clearTimeout(timer);
    }, [searchQuery]);

    const loadLibrary = useCallback(async (targetPage?: number) => {
        setLoading(true);
        try {
            const page = targetPage ?? libraryPage;
            const sourceType = libraryFilter === 'downloaded' ? 'downloaded' : libraryFilter === 'original' ? 'original' : '';
            const visibility = libraryFilter === 'public' ? 'public' : '';
            const sortBy = librarySort === 'name' ? 'name' : 'updated_at';
            const res = await gameApi.getLibraryList({
                q: debouncedSearchQuery,
                sort_by: sortBy,
                sort_order: 'desc',
                source_type: sourceType,
                visibility,
                page,
                page_size: 12
            });
            setLibraryMods(res.data || []);
            setLibraryPagination(res.pagination || EMPTY_PAGINATION);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, [debouncedSearchQuery, libraryFilter, libraryPage, librarySort]);

    const loadSafetyData = useCallback(async () => {
        try {
            const [, , libraryRes, accountRes] = await Promise.all([
                gameApi.getUserState(),
                gameApi.getSnapshots(),
                gameApi.getLibraryList({ page: 1, page_size: 200, sort_by: 'updated_at', sort_order: 'desc' }),
                gameApi.getAccountMe()
            ]);
            setLibraryCatalogMods(libraryRes?.data || []);
            setAccountInfo(accountRes?.data || null);
        } catch (e) {
            console.warn('Failed to load safety data', e);
        }
    }, []);

    const loadWorkshop = useCallback(async (targetPage?: number) => {
        setLoading(true);
        try {
            const page = targetPage ?? workshopPage;
            const sourceType = workshopFilter === 'forked' ? 'forked' : workshopFilter === 'original' ? 'original' : '';
            const ownedOnly = workshopFilter === 'mine';
            const sortBy = workshopSort === 'name' ? 'name' : workshopSort === 'downloads' ? 'downloads' : 'updated_at';
            const baseParams = {
                q: debouncedSearchQuery,
                sort_by: sortBy,
                sort_order: 'desc' as const,
                source_type: sourceType,
                page,
                page_size: 12
            };
            const res = ownedOnly
                ? await gameApi.getMyWorkshopList(baseParams)
                : await gameApi.getWorkshopList({ ...baseParams, owned_only: ownedOnly });
            setWorkshopMods(res.data || []);
            setWorkshopPagination(res.pagination || EMPTY_PAGINATION);
        } catch (e) {
            const status = (e as any)?.response?.status;
            if (status === 401 && workshopFilter === 'mine') {
                showToast('请先登录正式账户后再查看“我的作品”。');
                setWorkshopFilter('all');
            } else {
                console.error(e);
            }
        } finally {
            setLoading(false);
        }
    }, [debouncedSearchQuery, workshopFilter, workshopPage, workshopSort]);

    useEffect(() => {
        setLibraryPage(1);
    }, [debouncedSearchQuery, libraryFilter, librarySort]);

    useEffect(() => {
        setWorkshopPage(1);
    }, [debouncedSearchQuery, workshopFilter, workshopSort]);

    useEffect(() => {
        if (activeTab === 'library') loadLibrary();
    }, [activeTab, loadLibrary, libraryPage]);

    useEffect(() => {
        if (activeTab === 'workshop') loadWorkshop();
    }, [activeTab, loadWorkshop, workshopPage]);

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

    const handleSync = async (id: string, name: string) => {
        setConfirmDialog({
            open: true,
            title: '同步模组更新',
            message: `将用原作者的最新公共版本覆盖你当前的下载副本 [${name}]。确认继续？`,
            confirmText: '确认同步',
            onConfirm: async () => {
                setActionTarget(`sync-${id}`);
                try {
                    const res = await gameApi.syncLibraryItem(id);
                    showToast(`✅ ${res?.message || '同步成功'}`);
                    loadLibrary();
                    loadSafetyData();
                } catch (e) {
                    const detail = (e as any)?.response?.data?.detail || '同步失败';
                    showToast(`❌ ${detail}`);
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
            showToast(`[${name}] 已添加到库`);
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
            showToast(`正在编辑 [${name}]`);
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
            showToast('正在查看默认模组');
            onTabChange('editor');
        } catch (e) {
            const detail = (e as any)?.response?.data?.detail || '切换默认模组失败';
            showToast(`❌ ${detail}`);
        } finally {
            setActionTarget(null);
        }
    };

    const defaultVisibleInLibrary = useMemo(() => {
        const matchesSearch =
            !debouncedSearchQuery ||
            defaultTemplateMod.name.toLowerCase().includes(debouncedSearchQuery.toLowerCase()) ||
            defaultTemplateMod.description.toLowerCase().includes(debouncedSearchQuery.toLowerCase());
        const matchesFilter = libraryFilter === 'all' || libraryFilter === 'original';
        return matchesSearch && matchesFilter && libraryPage === 1;
    }, [debouncedSearchQuery, defaultTemplateMod.description, defaultTemplateMod.name, libraryFilter, libraryPage]);

    const displayedLibraryMods = useMemo(
        () => (defaultVisibleInLibrary ? [defaultTemplateMod, ...libraryMods] : libraryMods),
        [defaultTemplateMod, defaultVisibleInLibrary, libraryMods]
    );

    const getWorkshopFocusTags = (mod: any) => {
        if (Array.isArray(mod?.focus_tags) && mod.focus_tags.length > 0) {
            return mod.focus_tags.slice(0, 3);
        }
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

    const selectedWorkshopLibraryState = useMemo(() => {
        if (!selectedWorkshopMod) return null;

        const workshopId = String(selectedWorkshopMod.id);
        const linkedEditableMod = libraryCatalogMods.find(
            (item) => String(item.linked_workshop_id || '') === workshopId
        );
        if (linkedEditableMod) {
            return {
                tone: 'info' as const,
                title: '你的本地源模组',
                body: `你的库中已有可编辑源模组「${linkedEditableMod.name}」（v${linkedEditableMod.version || 1}）。继续编辑并重新发布后，会更新这个公开版本。`
            };
        }

        const downloadedCopies = libraryCatalogMods.filter(
            (item) =>
                String(item.source_mod_id || '') === workshopId ||
                String(item.parent_workshop_id || '') === workshopId
        );

        if (downloadedCopies.length === 0) {
            return {
                tone: 'info' as const,
                title: '尚未加入你的库',
                body: '你的库中还没有这个模组副本。下载后它会作为私有副本保存，你可以在本地编辑，并在开局时单独选择使用。'
            };
        }

        const outdatedCopies = downloadedCopies.filter((item) => !!item.has_update);
        if (outdatedCopies.length > 0) {
            const highestUpstreamVersion = Math.max(
                ...outdatedCopies.map((item) => Number(item.upstream_version || item.version || 1))
            );
            return {
                tone: 'warning' as const,
                title: '你的库中有旧副本',
                body: `你的库中有 ${outdatedCopies.length} 个下载副本落后于当前公开版本；它们最高可以同步到 v${highestUpstreamVersion}。如果你准备基于最新版继续修改，建议先回到“我的库”完成同步。`
            };
        }

        const latestCopy = downloadedCopies
            .slice()
            .sort((a, b) => String(b.updated_at || b.timestamp || '').localeCompare(String(a.updated_at || a.timestamp || '')))[0];
        return {
            tone: 'info' as const,
            title: '你的库中已有最新副本',
            body: `你的库中已经有这个模组的最新下载副本「${latestCopy?.name || selectedWorkshopMod.name}」（v${latestCopy?.version || selectedWorkshopMod.version || 1}），可以直接在本地继续编辑或开局使用。`
        };
    }, [selectedWorkshopMod, libraryCatalogMods]);

    const renderPaginationControls = (
        pagination: ListPagination,
        onPageChange: (page: number) => void
    ) => {
        if ((pagination?.total_pages || 1) <= 1) return null;
        return (
            <div className="mt-4 flex items-center justify-between gap-3 border-t border-[var(--color-cyan-main)]/10 pt-4">
                <div className="text-[11px] font-bold text-slate-400">
                    第 {pagination.page} / {pagination.total_pages} 页，共 {pagination.total} 条
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => onPageChange(Math.max(1, pagination.page - 1))}
                        disabled={!pagination.has_prev}
                        className="rounded-xl border-2 border-[var(--color-cyan-main)]/10 bg-white px-3 py-2 text-[11px] font-black text-[var(--color-cyan-main)] transition-all disabled:opacity-40"
                    >
                        上一页
                    </button>
                    <button
                        onClick={() => onPageChange(pagination.page + 1)}
                        disabled={!pagination.has_next}
                        className="rounded-xl border-2 border-[var(--color-cyan-main)]/10 bg-white px-3 py-2 text-[11px] font-black text-[var(--color-cyan-main)] transition-all disabled:opacity-40"
                    >
                        下一页
                    </button>
                </div>
            </div>
        );
    };

    return (
        <div className="flex-1 flex flex-col h-full p-6 relative animate-fade-in-up">
            {/* Toast Notification */}
            {toast && (
                <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50 px-6 py-3 bg-white border-2 border-[var(--color-cyan-main)]/20 rounded-full shadow-xl text-sm font-black text-[var(--color-cyan-dark)] animate-fade-in-up">
                    {toast}
                </div>
            )}

            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-5">
                <div className="flex items-center gap-4 w-full md:w-auto">
                    {/* Tab Switcher */}
                    <div className="flex bg-[var(--color-cyan-light)]/35 p-1 rounded-2xl border border-[var(--color-cyan-main)]/10">
                        <button
                            onClick={() => setActiveTab('library')}
                            className={`px-6 py-2 rounded-xl text-sm font-black transition-all flex items-center gap-2 ${activeTab === 'library' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-main)] hover:bg-white'}`}
                        >
                            <BookOpen size={14} /> 我的库
                        </button>
                        <button
                            onClick={() => setActiveTab('workshop')}
                            className={`px-6 py-2 rounded-xl text-sm font-black transition-all flex items-center gap-2 ${activeTab === 'workshop' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-main)] hover:bg-white'}`}
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
                            className="w-full pl-10 pr-4 py-2.5 bg-white border border-[var(--color-cyan-main)]/10 rounded-2xl text-sm font-bold focus:border-[var(--color-cyan-main)] outline-none transition-all shadow-sm"
                        />
                    </div>

                    <button 
                        onClick={() => activeTab === 'library' ? loadLibrary() : loadWorkshop()}
                        className="p-3 bg-white border border-[var(--color-cyan-main)]/10 text-[var(--color-cyan-main)] rounded-2xl hover:bg-[var(--color-cyan-main)] hover:text-white transition-all shadow-sm"
                    >
                        <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            <div className="mb-4 flex flex-col xl:flex-row gap-3 xl:items-center xl:justify-between">
                <div className="flex flex-wrap gap-2">
                    {activeTab === 'library' ? (
                        <>
                            <button onClick={() => setLibraryFilter('all')} className={`px-4 py-2 rounded-full text-sm font-black border ${libraryFilter === 'all' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>全部</button>
                            <button onClick={() => setLibraryFilter('original')} className={`px-4 py-2 rounded-full text-sm font-black border ${libraryFilter === 'original' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>原创</button>
                            <button onClick={() => setLibraryFilter('downloaded')} className={`px-4 py-2 rounded-full text-sm font-black border ${libraryFilter === 'downloaded' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>下载副本</button>
                            <button onClick={() => setLibraryFilter('public')} className={`px-4 py-2 rounded-full text-sm font-black border ${libraryFilter === 'public' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>已公开</button>
                        </>
                    ) : (
                        <>
                            <button onClick={() => setWorkshopFilter('all')} className={`px-4 py-2 rounded-full text-sm font-black border ${workshopFilter === 'all' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>全部</button>
                            <button onClick={() => setWorkshopFilter('original')} className={`px-4 py-2 rounded-full text-sm font-black border ${workshopFilter === 'original' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>原创</button>
                            <button onClick={() => setWorkshopFilter('forked')} className={`px-4 py-2 rounded-full text-sm font-black border ${workshopFilter === 'forked' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}>派生</button>
                            <button
                                onClick={() => {
                                    if (!canPublishWorkshopMods) {
                                        showToast('访客模式下不能查看“我的作品”，请先登录正式账户。');
                                        return;
                                    }
                                    setWorkshopFilter('mine');
                                }}
                                className={`px-4 py-2 rounded-full text-sm font-black border ${workshopFilter === 'mine' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'} ${!canPublishWorkshopMods ? 'opacity-50' : ''}`}
                                title={canPublishWorkshopMods ? '查看我公开的作品' : '请先登录正式账户'}
                            >
                                我的作品
                            </button>
                        </>
                    )}
                </div>
                <div className="flex items-center gap-2 self-start xl:self-auto">
                    <span className="text-sm font-black text-gray-400">排序</span>
                    {activeTab === 'library' ? (
                        <select value={librarySort} onChange={(e) => setLibrarySort(e.target.value as 'updated' | 'name')} className="px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/10 bg-white text-sm font-black text-[var(--color-cyan-dark)] outline-none">
                            <option value="updated">最近更新</option>
                            <option value="name">名称</option>
                        </select>
                    ) : (
                        <select value={workshopSort} onChange={(e) => setWorkshopSort(e.target.value as 'updated' | 'downloads' | 'name')} className="px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/10 bg-white text-sm font-black text-[var(--color-cyan-dark)] outline-none">
                            <option value="updated">最近更新</option>
                            <option value="downloads">下载量</option>
                            <option value="name">名称</option>
                        </select>
                    )}
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
                {loading && (activeTab === 'library' ? libraryMods.length === 0 : workshopMods.length === 0) ? (
                    <div className="flex flex-col items-center justify-center h-64 text-[var(--color-cyan-main)] animate-pulse">
                        <RefreshCw size={48} className="animate-spin mb-4 opacity-20" />
                        <span className="font-black uppercase tracking-widest text-xs">正在连接...</span>
                    </div>
                ) : (
                    <>
                        {activeTab === 'library' ? (
                            <div className="grid grid-cols-1 xl:grid-cols-2 gap-3 pb-8">
                                {displayedLibraryMods.length === 0 ? (
                                    <div className="col-span-full py-20 text-center text-gray-400 font-bold text-sm">
                                        暂无可编辑模组。可以从上方模板另存，或从工坊下载到我的库。
                                    </div>
                                ) : (
                                    displayedLibraryMods.map(mod => (
                                        <div key={mod.id} className={`group bg-white border p-6 rounded-[2rem] shadow-sm hover:shadow-lg transition-all flex flex-col ${mod.isDefault ? 'border-amber-200 bg-amber-50/20' : 'border-[var(--color-cyan-main)]/10 hover:border-[var(--color-cyan-main)]/30'}`}>
                                            <div className="flex justify-between items-start mb-2 pr-2">
                                                <h3 className="font-black text-xl text-[var(--color-cyan-dark)] truncate">{mod.name}</h3>
                                            </div>
                                            <div className="mb-4 flex flex-wrap gap-2">
                                                {mod.isDefault ? (
                                                    <span className="text-xs bg-amber-50 text-amber-700 px-3 py-1 rounded-full font-black border border-amber-200">
                                                        只读模板
                                                    </span>
                                                ) : (
                                                    <span className="text-xs bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] px-3 py-1 rounded-full font-black border border-[var(--color-cyan-main)]/20">
                                                        {getSourceLabel(mod.source_type)} · v{mod.version || 1}
                                                    </span>
                                                )}
                                                {mod.visibility === 'public' && !mod.isDefault && (
                                                    <span className="text-xs bg-emerald-50 text-emerald-600 px-3 py-1 rounded-full font-black border border-emerald-200">
                                                        已公开
                                                    </span>
                                                )}
                                                {!!mod.has_update && (
                                                    <span className="text-xs bg-amber-50 text-amber-700 px-3 py-1 rounded-full font-black border border-amber-200">
                                                        可同步 v{mod.upstream_version || mod.version}
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-sm text-gray-500 font-semibold mb-5 line-clamp-2 min-h-[2.5rem] flex-1">
                                                {mod.description || '无描述'}
                                            </p>
                                            <div className="flex justify-between items-center text-sm text-gray-400 font-bold mb-4">
                                                <span>{mod.isDefault ? '官方模板' : '本地模组'}</span>
                                                <span>{mod.timestamp?.split(' ')[0] || '最近更新'}</span>
                                            </div>
                                            {mod.isDefault ? (
                                                <div className="flex gap-3">
                                                    <button
                                                        onClick={handleViewDefault}
                                                        disabled={actionTarget === 'edit-default'}
                                                        className="flex-1 py-3 bg-white border border-[var(--color-cyan-main)]/10 text-[var(--color-cyan-main)] rounded-2xl font-black hover:bg-[var(--color-cyan-main)]/10 transition shadow-sm text-sm disabled:opacity-50"
                                                    >
                                                        {actionTarget === 'edit-default' ? '载入中...' : '查看模板'}
                                                    </button>
                                                    <button
                                                        onClick={() => setShowSaveDialog(true)}
                                                        className="flex-1 py-3 bg-[var(--color-cyan-main)] text-white rounded-2xl flex items-center justify-center gap-2 font-black hover:bg-[var(--color-cyan-dark)] transition shadow-md text-sm"
                                                    >
                                                        <Plus size={16} />
                                                        另存为
                                                    </button>
                                                </div>
                                            ) : (
                                                <div className="flex gap-3">
                                                    <button
                                                        onClick={() => handleEdit(mod.id, mod.name)}
                                                        disabled={actionTarget === `edit-${mod.id}`}
                                                        className="flex-1 py-3 bg-white border border-[var(--color-cyan-main)]/10 text-[var(--color-cyan-main)] rounded-2xl flex items-center justify-center gap-2 font-black hover:bg-[var(--color-cyan-main)]/10 transition shadow-sm text-sm disabled:opacity-50"
                                                    >
                                                        {actionTarget === `edit-${mod.id}` ? <RefreshCw size={14} className="animate-spin" /> : <Edit3 size={14} />}
                                                        编辑
                                                    </button>
                                                    {mod.has_update ? (
                                                        <button
                                                            onClick={() => handleSync(mod.id, mod.name)}
                                                            disabled={actionTarget === `sync-${mod.id}`}
                                                            className="flex-1 py-3 bg-amber-50 text-amber-700 rounded-2xl flex items-center justify-center gap-2 font-black hover:bg-amber-100 transition shadow-sm text-sm disabled:opacity-50"
                                                        >
                                                            {actionTarget === `sync-${mod.id}` ? <RefreshCw size={14} className="animate-spin" /> : '同步'}
                                                        </button>
                                                    ) : (
                                                        <button
                                                            onClick={() => handleDelete(mod.id, mod.name)}
                                                            disabled={actionTarget === `del-${mod.id}`}
                                                            className="flex-1 py-3 bg-red-50 text-red-500 rounded-2xl flex items-center justify-center gap-2 font-black hover:bg-red-500 hover:text-white transition shadow-sm text-sm disabled:opacity-50"
                                                        >
                                                            {actionTarget === `del-${mod.id}` ? <RefreshCw size={14} className="animate-spin" /> : <Trash2 size={14} />}
                                                            删除
                                                        </button>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    ))
                                )}
                            </div>
                            
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 pb-8">
                                {workshopMods.length === 0 ? (
                                    <div className="col-span-full py-20 text-center text-gray-400 font-bold text-sm">
                                        工坊空空如也
                                    </div>
                                ) : (
                                    workshopMods.map(mod => (
                                        <div key={mod.id} className="group bg-white border border-[var(--color-cyan-main)]/10 p-6 rounded-[2rem] shadow-sm hover:shadow-lg hover:border-[var(--color-cyan-main)]/30 transition-all flex flex-col">
                                        <div className="flex justify-between items-start mb-2 pr-6">
                                            <h3 className="font-black text-xl text-[var(--color-cyan-dark)] truncate">{mod.name}</h3>
                                        </div>
                                        <div className="mb-4">
                                            <span className="text-xs bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] px-3 py-1 rounded-full font-black">
                                                {mod.type === 'prompt_pack' ? '剧情包' : '独立角色'}
                                            </span>
                                        </div>
                                        <p className="text-sm text-gray-500 font-semibold mb-6 line-clamp-2 min-h-[2.5rem] flex-1">{mod.description}</p>
                                        <div className="flex justify-between items-center text-sm text-gray-400 font-bold mb-4">
                                            <span>作者: {mod.author}</span>
                                            <span className="flex items-center gap-1"><Download size={10} /> {mod.downloads} 下载</span>
                                        </div>
                                        <div className="mb-4 flex flex-wrap gap-2">
                                            {mod.is_owned_by_current_user ? (
                                                <span className="px-3 py-1 rounded-full text-xs font-black bg-emerald-50 text-emerald-600 border border-emerald-200">
                                                    我的公开模组
                                                </span>
                                            ) : (
                                                <span className="px-3 py-1 rounded-full text-xs font-black bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] border border-[var(--color-cyan-main)]/20">
                                                    下载后可在开局选择
                                                </span>
                                            )}
                                            <span className="px-3 py-1 rounded-full text-xs font-black bg-white border border-[var(--color-cyan-main)]/15 text-[var(--color-cyan-main)]">
                                                {getSourceLabel(mod.source_type)} · v{mod.version || 1}
                                            </span>
                                        </div>
                                        <button
                                            onClick={() => setSelectedWorkshopMod(mod)}
                                            className="mb-4 w-full py-3 bg-white border border-[var(--color-cyan-main)]/10 text-[var(--color-cyan-main)] rounded-2xl font-black hover:bg-[var(--color-cyan-main)]/10 transition shadow-sm text-sm"
                                        >
                                            查看详情
                                        </button>
                                        <button
                                            onClick={() => handleDownload(mod.id, mod.name)}
                                            disabled={actionTarget === `dl-${mod.id}`}
                                            className="w-full py-4 bg-[var(--color-cyan-main)] text-white rounded-2xl flex items-center justify-center gap-2 font-black hover:bg-[var(--color-cyan-dark)] transition shadow-md text-sm disabled:opacity-50"
                                        >
                                            {actionTarget === `dl-${mod.id}` ? <RefreshCw size={14} className="animate-spin" /> : <Download size={16} />}
                                            {mod.is_owned_by_current_user ? '查看我的库副本' : '下载到我的库'}
                                        </button>
                                        </div>
                                    ))
                                )}
                            </div>
                        )}
                        {activeTab === 'library'
                            ? renderPaginationControls(libraryPagination, setLibraryPage)
                            : renderPaginationControls(workshopPagination, setWorkshopPage)}
                    </>
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
                                    placeholder="起个名字..."
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
                <WorkshopModDetailModal
                    mod={selectedWorkshopMod}
                    libraryState={selectedWorkshopLibraryState}
                    canPublishWorkshopMods={canPublishWorkshopMods}
                    focusTags={getWorkshopFocusTags(selectedWorkshopMod)}
                    sourceLabel={getSourceLabel(selectedWorkshopMod.source_type)}
                    actionTarget={actionTarget}
                    onClose={() => setSelectedWorkshopMod(null)}
                    onDownload={async () => {
                        await handleDownload(selectedWorkshopMod.id, selectedWorkshopMod.name);
                        setSelectedWorkshopMod(null);
                    }}
                />
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
