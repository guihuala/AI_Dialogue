import { Trash2, Edit2, Check, X, Package } from 'lucide-react';

interface AdminWorkshopTabProps {
    items: any[];
    loading: boolean;
    editingId: string | null;
    editForm: { name: string; author: string; description: string };
    setEditForm: (v: { name: string; author: string; description: string }) => void;
    onStartEdit: (item: any) => void;
    onUpdate: () => void;
    onCancelEdit: () => void;
    onDelete: (id: string, name: string) => void;
}

export const AdminWorkshopTab = ({
    items,
    loading,
    editingId,
    editForm,
    setEditForm,
    onStartEdit,
    onUpdate,
    onCancelEdit,
    onDelete,
}: AdminWorkshopTabProps) => {
    return (
        <div className="p-6 overflow-hidden">
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.2em] flex items-center">
                        <Package size={14} className="mr-2" /> 创意工坊已发布项目 ({items.length})
                    </h3>
                    <p className="mt-2 text-xs font-bold text-slate-400">
                        这里集中处理工坊公开条目的名称、作者、简介和下架操作。
                    </p>
                </div>
            </div>

            <div className="overflow-x-auto custom-scrollbar">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="text-[10px] font-black text-[var(--color-cyan-main)]/50 uppercase tracking-widest border-b border-[var(--color-cyan-main)]/5">
                            <th className="px-4 py-3 pb-4">ID / 类型</th>
                            <th className="px-4 py-3 pb-4">模组名称</th>
                            <th className="px-4 py-3 pb-4">作者</th>
                            <th className="px-4 py-3 pb-4 w-1/3">描述</th>
                            <th className="px-4 py-3 pb-4 text-right">管理操作</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-cyan-main)]/5">
                        {items.length === 0 && !loading && (
                            <tr>
                                <td colSpan={5} className="py-20 text-center text-slate-400 font-bold">暂无已发布的模组数据</td>
                            </tr>
                        )}
                        {items.map(item => (
                            <tr key={item.id} className="group hover:bg-[var(--color-cyan-main)]/5 transition-colors">
                                <td className="px-4 py-4">
                                    <div className="font-mono text-[10px] text-slate-400">#{item.id}</div>
                                    <div className="text-[8px] bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] px-2 py-0.5 rounded-full inline-block mt-1 font-black uppercase">{item.type}</div>
                                </td>
                                <td className="px-4 py-4 font-black text-[var(--color-cyan-dark)]">
                                    {editingId === item.id ? (
                                        <input
                                            className="w-full bg-white border border-[var(--color-cyan-main)]/30 rounded px-2 py-1 text-sm outline-none focus:border-[var(--color-cyan-main)]"
                                            value={editForm.name}
                                            onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                                        />
                                    ) : item.name}
                                </td>
                                <td className="px-4 py-4 font-bold text-slate-600">
                                    {editingId === item.id ? (
                                        <input
                                            className="w-full bg-white border border-[var(--color-cyan-main)]/30 rounded px-2 py-1 text-sm outline-none focus:border-[var(--color-cyan-main)]"
                                            value={editForm.author}
                                            onChange={e => setEditForm({ ...editForm, author: e.target.value })}
                                        />
                                    ) : item.author}
                                </td>
                                <td className="px-4 py-4">
                                    {editingId === item.id ? (
                                        <textarea
                                            className="w-full bg-white border border-[var(--color-cyan-main)]/30 rounded px-2 py-1 text-xs outline-none focus:border-[var(--color-cyan-main)] resize-none"
                                            rows={2}
                                            value={editForm.description}
                                            onChange={e => setEditForm({ ...editForm, description: e.target.value })}
                                        />
                                    ) : (
                                        <p className="text-xs text-slate-500 font-medium line-clamp-2 leading-relaxed">{item.description}</p>
                                    )}
                                </td>
                                <td className="px-4 py-4 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        {editingId === item.id ? (
                                            <>
                                                <button
                                                    onClick={onUpdate}
                                                    className="p-2 text-green-500 hover:bg-green-50 rounded-lg transition"
                                                    title="确认保存"
                                                >
                                                    <Check size={18} />
                                                </button>
                                                <button
                                                    onClick={onCancelEdit}
                                                    className="p-2 text-slate-400 hover:bg-slate-50 rounded-lg transition"
                                                    title="取消"
                                                >
                                                    <X size={18} />
                                                </button>
                                            </>
                                        ) : (
                                            <>
                                                <button
                                                    onClick={() => onStartEdit(item)}
                                                    className="p-2 text-[var(--color-cyan-main)] hover:bg-[var(--color-cyan-light)] rounded-lg transition"
                                                    title="编辑基本信息"
                                                >
                                                    <Edit2 size={18} />
                                                </button>
                                                <button
                                                    onClick={() => onDelete(item.id, item.name)}
                                                    className="p-2 text-red-400 hover:bg-red-50 rounded-lg transition"
                                                    title="彻底下架模组"
                                                >
                                                    <Trash2 size={18} />
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

