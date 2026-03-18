import { UploadCloud, Plus, Trash2 } from 'lucide-react';

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
    onRemoveRosterItem: (id: string) => void;
    onRemoveCsvRow: (index: number) => void;
    parsedCsvHeaders: string[];
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
    onRemoveRosterItem,
    onRemoveCsvRow,
    parsedCsvHeaders
}: EditorModalsProps) => {
    return (
        <>
            {/* Modern Publish Modal */}
            {showPublishModal && (
                <div className="fixed inset-0 z-[500] flex items-center justify-center bg-[var(--color-cyan-dark)]/40 backdrop-blur-2xl animate-in fade-in duration-500 p-10">
                    <div className="bg-white rounded-3xl p-12 w-full max-w-2xl shadow-2xl border border-[var(--color-cyan-main)]/20 animate-in zoom-in-95 duration-500 relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-full h-3 bg-gradient-to-r from-[var(--color-cyan-main)] via-[var(--color-yellow-main)] to-[var(--color-cyan-dark)]" />

                        <div className="flex items-center mb-10">
                            <div className="w-16 h-16 rounded-2xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] flex items-center justify-center mr-6 shrink-0 shadow-lg border-2 border-white">
                                <UploadCloud size={36} />
                            </div>
                            <div>
                                <h3 className="text-4xl font-black text-[var(--color-cyan-dark)] tracking-tighter leading-none">发布至多元宇宙</h3>
                            </div>
                        </div>

                        <div className="space-y-10">
                            <div>
                                <label className="block text-[10px] font-black text-[var(--color-cyan-main)] uppercase mb-4 tracking-[0.4em] ml-2">模组别名</label>
                                <input
                                    type="text"
                                    value={publishMetadata.name}
                                    onChange={(e) => setPublishMetadata({ ...publishMetadata, name: e.target.value })}
                                    className="w-full px-10 py-6 rounded-[2.5rem] border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-black text-slate-800 transition-all shadow-inner text-lg"
                                    placeholder="模组名称"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-8">
                                <div>
                                    <label className="block text-[10px] font-black text-slate-400 uppercase mb-4 tracking-[0.4em] ml-2">总架构师</label>
                                    <input
                                        type="text"
                                        value={publishMetadata.author}
                                        onChange={(e) => setPublishMetadata({ ...publishMetadata, author: e.target.value })}
                                        className="w-full px-10 py-6 rounded-[2.5rem] border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-black text-slate-800 transition-all shadow-inner"
                                    />
                                </div>
                                <div className="flex flex-col justify-end">
                                    <div className="px-10 py-6 bg-cyan-50 rounded-[2.5rem] border-2 border-dashed border-cyan-100 text-cyan-600 font-black text-[10px] tracking-widest flex items-center justify-center">
                                        已验证本地权限
                                    </div>
                                </div>
                            </div>
                            <div>
                                <label className="block text-[10px] font-black text-slate-400 uppercase mb-4 tracking-[0.4em] ml-2">项目概览</label>
                                <textarea
                                    value={publishMetadata.description}
                                    onChange={(e) => setPublishMetadata({ ...publishMetadata, description: e.target.value })}
                                    className="w-full px-10 py-6 rounded-[2.5rem] border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-black text-slate-800 h-48 resize-none transition-all shadow-inner leading-loose text-base"
                                />
                            </div>
                        </div>

                        <div className="flex space-x-6 mt-16">
                            <button
                                onClick={() => setShowPublishModal(false)}
                                className="flex-1 py-6 bg-slate-100 text-slate-400 rounded-[2.5rem] font-black hover:bg-slate-200 transition-all uppercase tracking-widest text-xs border border-transparent"
                            >
                                取消
                            </button>
                            <button
                                onClick={() => { }} // Handle publish
                                className="flex-[1.5] py-6 bg-[var(--color-cyan-dark)] text-white rounded-[2.5rem] font-black hover:bg-[var(--color-cyan-main)] transition-all shadow-2xl shadow-cyan-900/40 uppercase tracking-widest text-xs border border-transparent"
                            >
                                确认上线
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* New Item Modal */}
            {newItemModal && (
                <div className="fixed inset-0 z-[250] flex items-center justify-center bg-[var(--color-cyan-dark)]/60 backdrop-blur-xl animate-in fade-in duration-300 p-6">
                    <div className="bg-white rounded-[2.5rem] p-10 w-full max-w-xl shadow-2xl border border-white animate-in zoom-in-95 duration-300 relative overflow-hidden">
                        <div className="flex items-center mb-8">
                            <div className="w-14 h-14 rounded-2xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] flex items-center justify-center mr-5 shadow-lg">
                                <Plus size={28} />
                            </div>
                            <div>
                                <h3 className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-tight">
                                    {newItemModal.type === 'char' ? '创建新角色档案' : '新增剧情事件项'}
                                </h3>
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">创建 // 数据库记录</p>
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
                                <label className="text-[10px] font-black text-slate-400 uppercase ml-2 tracking-widest">简介/备注</label>
                                <textarea
                                    value={newItemModal.type === 'char' ? newItemModal.description : ''}
                                    onChange={(e) => {
                                        if (newItemModal.type === 'char') {
                                            setNewItemModal({ ...newItemModal, description: e.target.value });
                                        }
                                    }}
                                    className={`w-full px-6 py-4 rounded-2xl border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-bold text-slate-700 transition-all h-32 resize-none ${newItemModal.type === 'event' ? 'hidden' : ''}`}
                                    placeholder="简单描述一下..."
                                />
                            </div>
                        </div>

                        <div className="flex space-x-4 mt-10">
                            <button
                                onClick={() => setNewItemModal(null)}
                                className="flex-1 py-4 bg-slate-100 text-slate-500 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-slate-200 transition-all"
                            >
                                丢弃
                            </button>
                            <button
                                onClick={() => {
                                    if (newItemModal.type === 'char') {
                                        onAddRosterItem({ name: newItemModal.name || '新角色', archetype: newItemModal.archetype || '普通人', description: newItemModal.description || '无描述' });
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
            )}

            {/* Delete Confirmation Modal */}
            {deleteConfirm && (
                <div className="fixed inset-0 z-[300] flex items-center justify-center bg-[var(--color-cyan-dark)]/60 backdrop-blur-md animate-in fade-in duration-300 p-6">
                    <div className="bg-white rounded-[2rem] p-10 w-full max-w-sm shadow-2xl border border-yellow-100 animate-in zoom-in-95 duration-300 relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-full h-1 bg-yellow-500" />
                        <div className="flex flex-col items-center text-center">
                            <div className="w-20 h-20 rounded-full bg-yellow-50 text-yellow-500 flex items-center justify-center mb-6 shadow-inner">
                                <Trash2 size={40} />
                            </div>
                            <h3 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight">确认移除此档案？</h3>
                            <p className="text-sm font-medium text-slate-400 mt-2 mb-8 leading-relaxed">
                                您正在尝试移除 <span className="text-yellow-500 font-black">"{deleteConfirm.name}"</span>。<br />
                                此操作将同步至物理文件，不可撤销。
                            </p>

                            <div className="flex space-x-3 w-full">
                                <button
                                    onClick={() => {
                                        setDeleteConfirm(null);
                                    }}
                                    className="flex-1 py-4 bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] rounded-2xl font-black text-[10px] uppercase tracking-widest hover:bg-[var(--color-cyan-main)] hover:text-white transition-all border border-[var(--color-cyan-main)]/10"
                                >
                                    跳过且保留
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
