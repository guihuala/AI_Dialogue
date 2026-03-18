import { Layout, Sparkles, Eye, Code, UploadCloud, Save, HelpCircle } from 'lucide-react';

interface EditorHeaderProps {
    sidebarCollapsed: boolean;
    setSidebarCollapsed: (v: boolean) => void;
    selectedFile: { type: 'md' | 'csv', name: string } | null;
    editMode: 'visual' | 'code';
    setEditMode: (v: 'visual' | 'code') => void;
    isSaving: boolean;
    onSave: () => void;
    onPublish: () => void;
    onShowGuide: () => void;
}

export const EditorHeader = ({
    sidebarCollapsed,
    setSidebarCollapsed,
    selectedFile,
    editMode,
    setEditMode,
    isSaving,
    onSave,
    onPublish,
    onShowGuide
}: EditorHeaderProps) => {
    return (
        <div className="flex items-center justify-between px-8 py-6 bg-white/40 border-b border-white/20 shrink-0">
            <div className="flex items-center space-x-4">
                <button
                    onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                    className="w-10 h-10 rounded-xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] flex items-center justify-center hover:bg-[var(--color-cyan-main)] hover:text-white transition-all shadow-sm"
                    title={sidebarCollapsed ? "展开侧边栏" : "收起侧边栏"}
                >
                    <Layout size={20} className={sidebarCollapsed ? "rotate-180" : ""} />
                </button>
                <div>
                    <h2 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight flex items-center">
                        内容编辑器 <span className="ml-3 px-2 py-0.5 bg-[var(--color-cyan-light)] rounded-full border border-[var(--color-cyan-main)]/20 text-[8px] text-[var(--color-cyan-main)] font-black tracking-widest">v2.1</span>
                    </h2>
                    <div className="flex items-center mt-1 space-x-2 text-[8px] font-black uppercase tracking-wider text-[var(--color-cyan-main)]">
                        <Sparkles size={10} className="text-[var(--color-yellow-main)]" />
                        <span>内容中枢</span>
                    </div>
                </div>
            </div>

            <div className="flex space-x-4 items-center scale-90 md:scale-100">
                {(selectedFile?.name.endsWith('json') || selectedFile?.type === 'csv') && (
                    <div className="flex bg-[var(--color-cyan-light)] p-1 rounded-xl border border-[var(--color-cyan-main)]/10 shadow-inner mr-4">
                        <button
                            onClick={() => setEditMode('visual')}
                            className={`flex items-center px-4 py-2 rounded-lg text-[10px] font-black transition-all ${editMode === 'visual' ? 'bg-white text-[var(--color-cyan-dark)] shadow-sm' : 'text-[var(--color-cyan-main)]/60 hover:text-[var(--color-cyan-dark)]'}`}
                        >
                            <Eye size={14} className="mr-2" /> 视觉引导
                        </button>
                        <button
                            onClick={() => setEditMode('code')}
                            className={`flex items-center px-4 py-2 rounded-lg text-[10px] font-black transition-all ${editMode === 'code' ? 'bg-white text-[var(--color-cyan-dark)] shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                        >
                            <Code size={14} className="mr-2" /> 代码注入
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
                    className="flex items-center px-8 py-4 bg-[var(--color-yellow-main)] hover:bg-[var(--color-yellow-light)] text-[var(--color-cyan-dark)] rounded-3xl font-black transition-all text-xs shadow-xl shadow-yellow-900/10 active:scale-95 group"
                >
                    <UploadCloud size={20} className="mr-3 group-hover:-translate-y-1 transition-transform" />
                    部署至工坊
                </button>
                <button
                    onClick={onSave}
                    disabled={isSaving || !selectedFile}
                    className="flex items-center px-10 py-4 bg-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] text-white rounded-3xl font-black transition-all shadow-2xl shadow-cyan-900/20 text-xs active:scale-95 disabled:opacity-20 flex-shrink-0"
                >
                    <Save size={20} className="mr-3 text-[var(--color-cyan-main)]" />
                    {isSaving ? '同步中...' : '提交修改'}
                </button>
            </div>
        </div>
    );
};
