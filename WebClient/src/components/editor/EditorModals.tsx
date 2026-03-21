import { useState } from 'react';
import { UploadCloud, Plus, Trash2, Sparkles, Loader2 } from 'lucide-react';
import { gameApi } from '../../api/gameApi';

interface EditorModalsProps {
    showPublishModal: boolean;
    setShowPublishModal: (v: boolean) => void;
    publishMetadata: any;
    setPublishMetadata: (v: any) => void;
    newItemModal: any;
    setNewItemModal: (v: any) => void;
    deleteConfirm: any;
    setDeleteConfirm: (v: any) => void;
    onAddRosterItem: (data: any) => void;
    onAddCsvRow: (data: any) => void;
    onAddSkillItem: (data: any) => void;
    onRemoveRosterItem: (id: string) => void;
    onRemoveCsvRow: (index: number) => void;
    onGenerateSkillPrompt?: (concept: string) => Promise<string>;
    parsedCsvHeaders: string[];
    publishIntent?: 'create' | 'update' | 'fork';
    currentEditingMod?: any;
    isLoggedInAccount?: boolean;
    onNavigateAccount?: () => void;
}

export const EditorModals = ({
    showPublishModal,
    setShowPublishModal,
    publishMetadata,
    setPublishMetadata,
    newItemModal,
    setNewItemModal,
    deleteConfirm,
    setDeleteConfirm,
    onAddRosterItem,
    onAddCsvRow,
    onAddSkillItem,
    onRemoveRosterItem,
    onRemoveCsvRow,
    onGenerateSkillPrompt,
    parsedCsvHeaders,
    publishIntent = 'create',
    currentEditingMod,
    isLoggedInAccount = false,
    onNavigateAccount
}: EditorModalsProps) => {
    const [isGenerating, setIsGenerating] = useState(false);
    const [isPublishing, setIsPublishing] = useState(false);
    const [publishReport, setPublishReport] = useState<any | null>(null);
    const [publishError, setPublishError] = useState('');

    const handleAIGenerate = async () => {
        if (!newItemModal?.archetype || isGenerating || !onGenerateSkillPrompt) return;
        setIsGenerating(true);
        try {
            const generated = await onGenerateSkillPrompt(newItemModal.archetype);
            setNewItemModal({ ...newItemModal, description: generated });
        } catch (e) {
            console.error('AI generation failed', e);
        } finally {
            setIsGenerating(false);
        }
    };

    const publishActionLabel = publishIntent === 'update'
        ? '更新公开版本'
        : publishIntent === 'fork'
            ? '发布为派生作品'
            : '首次公开';

    const publishDescription = publishIntent === 'update'
        ? '你正在更新自己已经公开的模组。本次发布会保留同一个工坊作品，并递增版本号。'
        : publishIntent === 'fork'
            ? '你当前编辑的是下载副本。本次发布会创建一个新的派生作品，不会覆盖原作者的公共模组。'
            : '你当前编辑的是私有模组。本次发布会把它首次公开到工坊，并与本地模组保持同步。';

    return (
        <>
            {/* Modern Publish Modal */}
            {showPublishModal && (
                <div className="fixed inset-0 z-[500] flex items-center justify-center bg-[var(--color-cyan-dark)]/40 backdrop-blur-2xl animate-in fade-in duration-500 p-10">
                    <div className="bg-white rounded-3xl p-12 w-full max-w-2xl shadow-2xl border border-[var(--color-cyan-main)]/20 animate-in zoom-in-95 duration-500 relative overflow-hidden flex flex-col max-h-[90vh]">
                        <div className="absolute top-0 left-0 w-full h-2 bg-[var(--color-cyan-main)]" />

                        <div className="overflow-y-auto pr-4 custom-scrollbar">
                                <div className="flex items-center mb-10">
                                    <div className="w-16 h-16 rounded-2xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] flex items-center justify-center mr-6 shrink-0 shadow-lg border-2 border-white">
                                        <UploadCloud size={36} />
                                    </div>
                                    <div>
                                        <h3 className="text-4xl font-black text-[var(--color-cyan-dark)] tracking-tighter leading-none">{publishActionLabel}</h3>
                                        <div className="mt-2 text-[11px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">
                                            当前模组：{currentEditingMod?.name || publishMetadata.name || '未命名模组'}
                                        </div>
                                    </div>
                                </div>

                            <div className="space-y-10">
                                <div className="bg-[var(--color-cyan-light)]/20 border-2 border-[var(--color-cyan-main)]/10 rounded-2xl p-4">
                                    <div className="text-[10px] text-slate-500 font-bold mb-3 leading-relaxed">
                                        {publishDescription}
                                    </div>
                                    <div className="mb-3 flex flex-wrap gap-2">
                                        <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-white border border-[var(--color-cyan-main)]/15 text-[var(--color-cyan-main)]">
                                            {publishIntent === 'update' ? `当前版本 v${currentEditingMod?.version || 1}` : publishIntent === 'fork' ? '将创建新作品' : '首次公开'}
                                        </span>
                                        <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${isLoggedInAccount ? 'bg-emerald-50 border border-emerald-200 text-emerald-700' : 'bg-amber-50 border border-amber-200 text-amber-700'}`}>
                                            {isLoggedInAccount ? '已登录，可公开发布' : '需登录账户后才能发布'}
                                        </span>
                                        {publishIntent === 'fork' && currentEditingMod?.source_mod_id && (
                                            <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest bg-amber-50 border border-amber-200 text-amber-700">
                                                来源作品：{currentEditingMod.source_mod_id}
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center justify-between gap-3">
                                        <span className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">
                                            发布前校验
                                        </span>
                                        <button
                                            onClick={async () => {
                                                try {
                                                    const res = await gameApi.validateCurrentForPublish();
                                                    setPublishReport(res.report || null);
                                                } catch (e: any) {
                                                    const detail = e?.response?.data?.detail || '校验失败';
                                                    setPublishReport({ ok: false, errors: [detail], warnings: [], stats: {} });
                                                }
                                            }}
                                            className="px-3 py-1 rounded-full text-[10px] font-black bg-white border border-[var(--color-cyan-main)]/20 text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-light)] transition-all"
                                        >
                                            立即校验
                                        </button>
                                    </div>
                                    {publishReport ? (
                                        <div className="mt-3 space-y-2">
                                            <div className={`text-xs font-black ${publishReport.ok ? 'text-emerald-600' : 'text-red-500'}`}>
                                                {publishReport.ok ? '校验通过，可发布' : '校验未通过，请先修复错误'}
                                            </div>
                                            <div className="text-[10px] text-slate-500 font-bold">
                                                文件统计：MD {publishReport?.stats?.md_files || 0} / CSV {publishReport?.stats?.csv_files || 0}
                                            </div>
                                            {Array.isArray(publishReport.errors) && publishReport.errors.length > 0 && (
                                                <div className="text-[11px] text-red-500 font-bold">
                                                    错误：{publishReport.errors.join('；')}
                                                </div>
                                            )}
                                            {Array.isArray(publishReport.warnings) && publishReport.warnings.length > 0 && (
                                                <div className="text-[11px] text-amber-600 font-bold">
                                                    警告：{publishReport.warnings.join('；')}
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="mt-2 text-[10px] text-slate-400 font-bold">建议先执行一次校验再发布</div>
                                    )}
                                    {!isLoggedInAccount && (
                                        <div className="mt-3 rounded-2xl border border-amber-200 bg-amber-50/70 px-4 py-3">
                                            <div className="text-[11px] font-black text-amber-700">
                                                公开模组会绑定到正式账户名下。请先登录或注册，再回来执行发布。
                                            </div>
                                            {onNavigateAccount && (
                                                <button
                                                    onClick={onNavigateAccount}
                                                    className="mt-3 inline-flex items-center rounded-full border border-amber-300 bg-white px-3 py-1.5 text-[10px] font-black uppercase tracking-widest text-amber-700 transition-all hover:bg-amber-100"
                                                >
                                                    前往账户中心
                                                </button>
                                            )}
                                        </div>
                                    )}
                                    {publishError && (
                                        <div className="mt-3 rounded-2xl border border-red-200 bg-red-50/70 px-4 py-3 text-[11px] font-black text-red-600">
                                            {publishError}
                                        </div>
                                    )}
                                </div>

                                <div>
                                    <label className="block text-[10px] font-black text-[var(--color-cyan-main)] uppercase mb-4 tracking-[0.4em] ml-2">模组别名</label>
                                    <input
                                        type="text"
                                        value={publishMetadata.name}
                                        onChange={(e) => setPublishMetadata({ ...publishMetadata, name: e.target.value })}
                                        className="w-full px-10 py-6 rounded-[2.5rem] border-2 border-[var(--color-soft-border)] bg-white focus:border-[var(--color-cyan-main)] outline-none font-black text-[var(--color-life-text)] transition-all shadow-inner text-lg"
                                        placeholder="模组名称"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-8">
                                    <div>
                                        <label className="block text-[10px] font-black text-slate-400 uppercase mb-4 tracking-[0.4em] ml-2">作者</label>
                                        <input
                                            type="text"
                                            value={publishMetadata.author}
                                            onChange={(e) => setPublishMetadata({ ...publishMetadata, author: e.target.value })}
                                            className="w-full px-10 py-6 rounded-[2.5rem] border-2 border-[var(--color-soft-border)] bg-white focus:border-[var(--color-cyan-main)] outline-none font-black text-[var(--color-life-text)] transition-all shadow-inner"
                                        />
                                    </div>
                                    <div className="flex flex-col justify-end">
                                        <div className="px-10 py-6 bg-[var(--color-cyan-light)] rounded-[2.5rem] border-2 border-dashed border-[var(--color-cyan-main)]/20 text-[var(--color-cyan-main)] font-black text-[10px] tracking-widest flex items-center justify-center">
                                            已验证本地权限
                                        </div>
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-[10px] font-black text-slate-400 uppercase mb-4 tracking-[0.4em] ml-2">项目概览</label>
                                    <textarea
                                        value={publishMetadata.description}
                                        onChange={(e) => setPublishMetadata({ ...publishMetadata, description: e.target.value })}
                                        className="w-full px-10 py-6 rounded-[2.5rem] border-2 border-[var(--color-soft-border)] bg-white focus:border-[var(--color-cyan-main)] outline-none font-black text-[var(--color-life-text)] h-48 resize-none transition-all shadow-inner leading-loose text-base"
                                    />
                                </div>
                            </div>

                            <div className="flex space-x-6 mt-16">
                                <button
                                    onClick={() => setShowPublishModal(false)}
                                    className="flex-1 py-6 bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] rounded-[2.5rem] font-black hover:bg-[var(--color-cyan-main)] hover:text-white transition-all uppercase tracking-widest text-xs"
                                >
                                    取消轮次
                                </button>
                                <button
                                    onClick={async () => {
                                        setPublishError('');
                                        if (!isLoggedInAccount) {
                                            setPublishError('当前为访客模式，公开发布需要先登录正式账户。');
                                            return;
                                        }
                                        setIsPublishing(true);
                                        try {
                                            const validateRes = await gameApi.validateCurrentForPublish();
                                            setPublishReport(validateRes.report || null);
                                            if (!validateRes?.report?.ok) {
                                                return;
                                            }
                                            const res = publishIntent === 'update'
                                                ? await gameApi.publishUpdateMod(publishMetadata)
                                                : publishIntent === 'fork'
                                                    ? await gameApi.publishForkMod(publishMetadata)
                                                    : await gameApi.publishCreateMod(publishMetadata);
                                            if (res.status === 'success') {
                                                setShowPublishModal(false);
                                                setPublishMetadata({ name: '', author: '', description: '' });
                                                setPublishReport(null);
                                                setPublishError('');
                                                console.log('Mod published successfully:', res.id);
                                            }
                                        } catch (e: any) {
                                            const detail = e?.response?.data?.detail || '';
                                            if (e?.response?.status === 401) {
                                                setPublishError('公开发布需要登录正式账户。请先前往账户中心登录后再试。');
                                            } else {
                                                setPublishError(detail || '发布失败，请稍后重试。');
                                            }
                                            console.error('Failed to publish mod:', e);
                                        } finally {
                                            setIsPublishing(false);
                                        }
                                    }}
                                    disabled={isPublishing || !isLoggedInAccount}
                                    className="flex-[1.5] py-6 bg-[var(--color-cyan-dark)] disabled:opacity-50 text-white rounded-[2.5rem] font-black hover:bg-[var(--color-cyan-main)] transition-all shadow-2xl shadow-cyan-900/40 uppercase tracking-widest text-xs flex items-center justify-center gap-2"
                                >
                                    {isPublishing ? <Loader2 size={16} className="animate-spin" /> : null}
                                    {publishIntent === 'update' ? '确认更新公开版本' : publishIntent === 'fork' ? '确认发布派生作品' : '确认首次公开'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* New Item Modal */}
            {newItemModal && (
                <div className="fixed inset-0 z-[500] flex items-center justify-center bg-[var(--color-cyan-dark)]/60 backdrop-blur-xl animate-in fade-in duration-300 p-6">
                    <div className="bg-white rounded-[2.5rem] p-10 w-full max-w-xl shadow-2xl border border-white animate-in zoom-in-95 duration-300 relative overflow-hidden flex flex-col max-h-[90vh]">
                        <div className="overflow-y-auto pr-4 custom-scrollbar">
                            <div className="flex items-center mb-8">
                                <div className="w-14 h-14 rounded-2xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] flex items-center justify-center mr-5 shadow-lg">
                                    <Plus size={28} />
                                </div>
                                <div>
                                    <h3 className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-tight">
                                        {newItemModal.type === 'char' ? '创建新角色档案' : newItemModal.type === 'skill' ? '编写自定义 AI 插件 (Skill)' : '新增剧情事件项'}
                                    </h3>
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">创建 // {newItemModal.type === 'skill' ? '系统动态逻辑' : '数据库记录'}</p>
                                </div>
                            </div>

                            <div className="space-y-6">
                                {newItemModal.type === 'char' ? (
                                    <>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black text-slate-400 uppercase ml-2 tracking-widest">角色名称</label>
                                            <input
                                                value={newItemModal.name}
                                                onChange={(e) => setNewItemModal({ ...newItemModal, name: e.target.value })}
                                                className="w-full px-6 py-4 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/30 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-bold text-[var(--color-cyan-dark)] transition-all"
                                                placeholder="输入姓名..."
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black text-slate-400 uppercase ml-2 tracking-widest">核心身份标签</label>
                                            <input
                                                value={newItemModal.archetype}
                                                onChange={(e) => setNewItemModal({ ...newItemModal, archetype: e.target.value })}
                                                className="w-full px-6 py-4 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/30 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-bold text-[var(--color-cyan-dark)] transition-all"
                                                placeholder="例: 高冷学姐 / 阳光僚机 / 毒舌教授"
                                            />
                                        </div>
                                    </>
                                ) : newItemModal.type === 'skill' ? (
                                    <>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black text-slate-400 uppercase ml-2 tracking-widest">插件唯一标识 (文件名)</label>
                                            <input
                                                value={newItemModal.name}
                                                onChange={(e) => setNewItemModal({ ...newItemModal, name: e.target.value.replace(/[^a-z0-9_]/gi, '_') })}
                                                className="w-full px-6 py-4 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/30 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-bold text-[var(--color-cyan-dark)] transition-all"
                                                placeholder="例: player_voice_optimizer"
                                            />
                                        </div>
                                        <div className="space-y-2 relative">
                                            <div className="flex justify-between items-end">
                                                <label className="text-[10px] font-black text-slate-400 uppercase ml-2 tracking-widest">预期达成目标</label>
                                                <button
                                                    onClick={handleAIGenerate}
                                                    disabled={isGenerating || !newItemModal.archetype}
                                                    className={`flex items-center space-x-1.5 px-3 py-1 rounded-full text-[10px] font-black transition-all ${
                                                        isGenerating 
                                                        ? 'bg-[var(--color-soft-border)] text-slate-400 cursor-not-allowed' 
                                                        : 'bg-[var(--color-yellow-main)] text-[var(--color-cyan-dark)] hover:shadow-lg hover:scale-105 active:scale-95 shadow-sm'
                                                    } mb-1`}
                                                >
                                                    {isGenerating ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                                                    <span>{isGenerating ? '正在调思...' : 'AI 一键生成提示词'}</span>
                                                </button>
                                            </div>
                                            <input
                                                value={newItemModal.archetype}
                                                onChange={(e) => setNewItemModal({ ...newItemModal, archetype: e.target.value })}
                                                className="w-full px-6 py-4 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/30 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-bold text-[var(--color-cyan-dark)] transition-all"
                                                placeholder="输入您的脑洞，交给 AI 补全..."
                                            />
                                        </div>
                                    </>
                                ) : (
                                    <div className="space-y-4 max-h-[40vh] overflow-y-auto pr-2 custom-scrollbar">
                                        {parsedCsvHeaders.map(h => (
                                            <div key={h} className="space-y-2">
                                                <label className="text-[10px] font-black text-slate-400 uppercase ml-2 tracking-widest">{h}</label>
                                                <input
                                                    onChange={(e) => {
                                                        const newDesc = newItemModal.description || '{}';
                                                        let data = {};
                                                        try { data = JSON.parse(newDesc); } catch (e) { }
                                                        // @ts-ignore
                                                        data[h] = e.target.value;
                                                        setNewItemModal({ ...newItemModal, description: JSON.stringify(data) });
                                                    }}
                                                    className="w-full px-6 py-4 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/30 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-bold text-[var(--color-cyan-dark)] transition-all"
                                                    placeholder={`输入 ${h}...`}
                                                />
                                            </div>
                                        ))}
                                    </div>
                                )}

                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-slate-400 uppercase ml-2 tracking-widest">
                                        {newItemModal.type === 'skill' ? '插件提示词指令 (Prompt)' : '简介/备注'}
                                    </label>
                                    <textarea
                                        value={newItemModal.description}
                                        onChange={(e) => setNewItemModal({ ...newItemModal, description: e.target.value })}
                                        className={`w-full px-6 py-4 rounded-2xl border-2 border-[var(--color-soft-border)] bg-white focus:border-[var(--color-cyan-main)] outline-none font-bold text-[var(--color-life-text)] transition-all h-32 resize-none ${newItemModal.type === 'event' ? 'hidden' : ''}`}
                                        placeholder="输入详细描述或指令内容..."
                                    />
                                </div>
                            </div>

                            <div className="flex space-x-4 mt-10">
                                <button
                                    onClick={() => setNewItemModal(null)}
                                    className="flex-1 py-4 bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-[var(--color-cyan-main)] hover:text-white transition-all"
                                >
                                    丢弃修改
                                </button>
                                <button
                                    onClick={() => {
                                        if (newItemModal.type === 'char') {
                                            onAddRosterItem({ name: newItemModal.name || '新角色', archetype: newItemModal.archetype || '普通人', description: newItemModal.description || '无描述' });
                                        } else if (newItemModal.type === 'skill') {
                                            onAddSkillItem({ name: newItemModal.name || 'custom_skill', target: newItemModal.archetype || '未指定', content: newItemModal.description || '' });
                                        } else {
                                            let data = {};
                                            try { data = JSON.parse(newItemModal.description || '{}'); } catch (e) { }
                                            onAddCsvRow(data);
                                        }
                                    }}
                                    className="flex-1 py-4 bg-[var(--color-cyan-main)] text-white rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-[var(--color-cyan-dark)] transition-all shadow-lg"
                                >
                                    确认建立
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {deleteConfirm && (
                <div className="fixed inset-0 z-[600] flex items-center justify-center bg-[var(--color-cyan-dark)]/60 backdrop-blur-md animate-in fade-in duration-300 p-6">
                    <div className="bg-white rounded-[2rem] p-10 w-full max-sm shadow-2xl border border-[var(--color-soft-border)] animate-in zoom-in-95 duration-300 relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-full h-1 bg-[var(--color-yellow-main)]" />
                        <div className="flex flex-col items-center text-center">
                            <div className="w-20 h-20 rounded-full bg-[var(--color-yellow-light)] text-[var(--color-yellow-main)] flex items-center justify-center mb-6 shadow-inner">
                                <Trash2 size={40} />
                            </div>
                            <h3 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight">确认移除此档案？</h3>
                            <p className="text-sm font-medium text-slate-400 mt-2 mb-8 leading-relaxed">
                                您正在尝试移除 <span className="text-yellow-500 font-black">"{deleteConfirm.name}"</span>。<br />
                                此操作将同步至物理文件，不可撤销。
                            </p>

                            <div className="flex space-x-3 w-full">
                                <button
                                    onClick={() => setDeleteConfirm(null)}
                                    className="flex-1 py-4 bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] rounded-2xl font-black text-[10px] uppercase tracking-widest hover:bg-[var(--color-cyan-main)] hover:text-white transition-all border border-[var(--color-cyan-main)]/10"
                                >
                                    取消
                                </button>
                                <button
                                    onClick={() => {
                                        if (deleteConfirm?.type === 'char') onRemoveRosterItem(deleteConfirm.id);
                                        else if (deleteConfirm?.index !== undefined) onRemoveCsvRow(deleteConfirm.index);
                                    }}
                                    className="flex-1 py-4 bg-[var(--color-yellow-main)] text-[var(--color-cyan-dark)] rounded-2xl font-black text-[10px] uppercase tracking-widest hover:bg-[var(--color-yellow-dark)] hover:text-white transition-all shadow-lg shadow-yellow-900/20"
                                >
                                    确认清除
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};
