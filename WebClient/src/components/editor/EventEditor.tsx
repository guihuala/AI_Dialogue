import { Plus, Trash2, ScrollText } from 'lucide-react';

interface EventEditorProps {
    parsedCsv: { headers: string[], rows: Record<string, string>[] } | null;
    onUpdateRow: (rowIndex: number, field: string, value: string) => void;
    onAddNew: () => void;
    onDeleteRow: (index: number, name: string) => void;
}

export const EventEditor = ({
    parsedCsv,
    onUpdateRow,
    onAddNew,
    onDeleteRow
}: EventEditorProps) => {
    return (
        <div className="flex-1 flex flex-col overflow-hidden">
            <div className="px-8 py-6 border-b border-slate-50 flex items-center justify-between shrink-0 bg-slate-50/30">
                <div>
                    <h4 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight">剧情事件管理</h4>
                </div>
                <button
                    onClick={onAddNew}
                    className="px-6 py-3 bg-[var(--color-cyan-dark)] text-white rounded-xl font-black text-[10px] uppercase tracking-widest flex items-center hover:bg-[var(--color-cyan-main)] transition-all shadow-xl shadow-cyan-900/20"
                >
                    <Plus size={16} className="mr-2" /> 新增剧情事件
                </button>
            </div>
            <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
                <div className="grid grid-cols-1 gap-6">
                    {parsedCsv?.rows.map((row, idx) => (
                        <div key={idx} className="bg-white/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-100 hover:border-[var(--color-cyan-main)]/30 transition-all group/card relative shadow-sm hover:shadow-md">
                            <button
                                onClick={() => onDeleteRow(idx, (parsedCsv?.headers && row[parsedCsv.headers[0]]) || `行 ${idx + 1}`)}
                                className="absolute top-4 right-4 p-2 text-[var(--color-yellow-main)] hover:text-[var(--color-yellow-dark)] opacity-0 group-hover/card:opacity-100 transition-all"
                            >
                                <Trash2 size={14} />
                            </button>

                            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                                {parsedCsv?.headers?.map((h, hIdx) => (
                                    <div key={h} className={hIdx === (parsedCsv?.headers?.length || 0) - 1 ? "md:col-span-3 space-y-1" : "space-y-1"}>
                                        <label className="text-[10px] font-bold text-[var(--color-cyan-main)]/50 ml-1 uppercase">{h}</label>
                                        <textarea
                                            value={row[h]}
                                            onChange={(e) => onUpdateRow(idx, h, e.target.value)}
                                            className="w-full px-4 py-2 bg-white/80 rounded-xl border border-[var(--color-cyan-main)]/10 text-sm font-medium text-[var(--color-cyan-dark)] focus:border-[var(--color-cyan-main)] outline-none transition-all resize-none overflow-hidden"
                                            rows={1}
                                            onInput={(e) => {
                                                const target = e.target as HTMLTextAreaElement;
                                                target.style.height = 'auto';
                                                target.style.height = target.scrollHeight + 'px';
                                            }}
                                        />
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                    {parsedCsv?.rows.length === 0 && (
                        <div className="flex flex-col items-center justify-center py-20 opacity-20">
                            <ScrollText size={48} className="mb-4" />
                            <p className="text-sm font-black uppercase tracking-widest">暂无事件数据</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
