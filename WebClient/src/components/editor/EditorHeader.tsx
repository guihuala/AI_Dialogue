import { Layout, Eye, Code, UploadCloud, Save, HelpCircle } from 'lucide-react';

interface EditorHeaderProps {
    sidebarCollapsed: boolean;
    setSidebarCollapsed: (v: boolean) => void;
    selectedFile: { type: 'md' | 'csv', name: string } | null;
    activeSourceLabel?: string;
    activeModLabel?: string;
    contextHint?: string;
    statusNotice?: string;
    statusNoticeTone?: 'info' | 'warning';
    editMode: 'visual' | 'code';
    setEditMode: (v: 'visual' | 'code') => void;
    isSaving: boolean;
    canEdit?: boolean;
    canPublish?: boolean;
    saveLabel?: string;
    onSave: () => void;
    onPublish: () => void;
    onShowGuide: () => void;
}

export const EditorHeader = ({
    sidebarCollapsed,
    setSidebarCollapsed,
    selectedFile,
    activeSourceLabel,
    activeModLabel,
    contextHint,
    statusNotice,
    statusNoticeTone = 'info',
    editMode,
    setEditMode,
    isSaving,
    canEdit = true,
    canPublish = true,
    saveLabel,
    onSave,
    onPublish,
    onShowGuide
}: EditorHeaderProps) => {
    return (
        <div className="flex items-center justify-between px-8 py-5 bg-white/40 border-b border-white/20 shrink-0">
            <div className="flex items-center space-x-4">
                <button
                    onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                    className="w-10 h-10 rounded-xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] flex items-center justify-center hover:bg-[var(--color-cyan-main)] hover:text-white transition-all shadow-sm"
                    title={sidebarCollapsed ? "展开侧边栏" : "收起侧边栏"}
                >
                    <Layout size={20} className={sidebarCollapsed ? "rotate-180" : ""} />
                </button>
                {(activeSourceLabel || activeModLabel || contextHint || statusNotice) && (
                    <div className="flex flex-col">
                        {(activeSourceLabel || activeModLabel || contextHint) && (
                            <div className="flex flex-wrap gap-2 items-center">
                                {activeSourceLabel && (
                                    <span className="px-2 py-1 rounded-full bg-white/80 border border-[var(--color-cyan-main)]/15 text-[10px] font-black text-[var(--color-cyan-dark)]">
                                        当前来源：{activeSourceLabel}
                                    </span>
                                )}
                                {activeModLabel && (
                                    <span className="px-2 py-1 rounded-full bg-[var(--color-cyan-light)]/70 border border-[var(--color-cyan-main)]/15 text-[10px] font-black text-[var(--color-cyan-main)]">
                                        当前模组：{activeModLabel}
                                    </span>
                                )}
                                {contextHint && (
                                    <span className="text-[10px] font-bold text-[var(--color-cyan-dark)]/55">
                                        {contextHint}
                                    </span>
                                )}
                            </div>
                        )}
                        {statusNotice && (
                            <div
                                className={`mt-2 inline-flex max-w-2xl items-center rounded-2xl border px-3 py-2 text-[10px] font-black leading-5 ${
                                    statusNoticeTone === 'warning'
                                        ? 'border-amber-200 bg-amber-50 text-amber-700'
                                        : 'border-[var(--color-cyan-main)]/15 bg-white/85 text-[var(--color-cyan-dark)]'
                                }`}
                            >
                                {statusNotice}
                            </div>
                        )}
                    </div>
                )}
            </div>

            <div className="flex space-x-4 items-center scale-90 md:scale-100">
                {(selectedFile?.name.endsWith('json') || selectedFile?.type === 'csv') && (
                    <div className="flex bg-[var(--color-cyan-light)] p-1 rounded-xl border border-[var(--color-cyan-main)]/10 shadow-inner mr-4">
                        <button
                            onClick={() => setEditMode('visual')}
                            className={`flex items-center px-4 py-2 rounded-lg text-[10px] font-black transition-all ${editMode === 'visual' ? 'bg-white text-[var(--color-cyan-dark)] shadow-sm' : 'text-[var(--color-cyan-main)]/60 hover:text-[var(--color-cyan-dark)]'}`}
                        >
                            <Eye size={14} className="mr-2" /> 可视化
                        </button>
                        <button
                            onClick={() => setEditMode('code')}
                            className={`flex items-center px-4 py-2 rounded-lg text-[10px] font-black transition-all ${editMode === 'code' ? 'bg-white text-[var(--color-cyan-dark)] shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                        >
                            <Code size={14} className="mr-2" /> 原始文件
                        </button>
                    </div>
                )}
                <button
                    onClick={onShowGuide}
                    className="w-12 h-12 rounded-full bg-white/60 text-[var(--color-cyan-main)] flex items-center justify-center hover:bg-[var(--color-cyan-main)] hover:text-white transition-all border border-[var(--color-cyan-main)]/20 shadow-sm mr-2"
                    title="查看编辑器说明文档"
                >
                    <HelpCircle size={22} />
                </button>
                <button
                    onClick={onPublish}
                    disabled={!canPublish}
                    className="flex items-center px-8 py-4 bg-[var(--color-yellow-main)] hover:bg-[var(--color-yellow-light)] text-[var(--color-cyan-dark)] rounded-3xl font-black transition-all text-xs shadow-xl shadow-yellow-900/10 active:scale-95 group"
                >
                    <UploadCloud size={20} className="mr-3 group-hover:-translate-y-1 transition-transform" />
                    公开至工坊
                </button>
                <button
                    onClick={onSave}
                    disabled={isSaving || (!selectedFile && canEdit)}
                    className="flex items-center px-10 py-4 bg-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] text-white rounded-3xl font-black transition-all shadow-2xl shadow-cyan-900/20 text-xs active:scale-95 disabled:opacity-20 flex-shrink-0"
                >
                    <Save size={20} className="mr-3 text-[var(--color-cyan-main)]" />
                    {isSaving ? '同步中...' : (saveLabel || '提交修改')}
                </button>
            </div>
        </div>
    );
};
