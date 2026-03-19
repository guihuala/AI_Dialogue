import { useState, useMemo } from 'react';
import { User, MessageSquare, Heart, ShieldAlert, X, Save } from 'lucide-react';

interface RelationshipMatrixProps {
    parsedRoster: any;
    parsedCsv: {
        headers: string[];
        rows: Record<string, string>[];
    } | null;
    onUpdateRow: (rowIndex: number, field: string, value: string) => void;
    onAddRow: (data: Record<string, string>) => void;
    onSaveAll?: () => void;
}

export const RelationshipMatrix = ({
    parsedRoster,
    parsedCsv,
    onUpdateRow,
    onAddRow,
    onSaveAll
}: RelationshipMatrixProps) => {
    const [selectedCell, setSelectedCell] = useState<{
        evaluator: string,
        evaluatee: string,
        rowIndex: number
    } | null>(null);

    // Get all character names from roster
    const characters = useMemo(() => {
        if (!parsedRoster) return [];
        return Object.values(parsedRoster).map((c: any) => c.name);
    }, [parsedRoster]);

    // Build a lookup map: evaluator -> evaluatee -> { rowIndex, surface, inner }
    const relationshipMap = useMemo(() => {
        const map: Record<string, Record<string, { rowIndex: number, surface: string, inner: string }>> = {};
        if (!parsedCsv) return map;

        parsedCsv.rows.forEach((row, idx) => {
            const evaluator = row['评价者'];
            const evaluatee = row['被评价者'];
            if (!map[evaluator]) map[evaluator] = {};
            map[evaluator][evaluatee] = {
                rowIndex: idx,
                surface: row['表面态度'] || '',
                inner: row['内心真实评价'] || ''
            };
        });
        return map;
    }, [parsedCsv]);

    const handleCellClick = (evaluator: string, evaluatee: string) => {
        if (evaluator === evaluatee) return;
        
        const existing = relationshipMap[evaluator]?.[evaluatee];
        if (existing) {
            setSelectedCell({ evaluator, evaluatee, rowIndex: existing.rowIndex });
        } else {
            // Create a new relationship entry if it doesn't exist
            const newRow = {
                '评价者': evaluator,
                '被评价者': evaluatee,
                '表面态度': '普通交流',
                '内心真实评价': '尚未深入了解'
            };
            onAddRow(newRow);
            // The mapping will update on next render, but for UX we might need to wait for state sync
            // For now, let's assume the user has to click again or the state is fast enough
        }
    };

    return (
        <div className="flex-1 flex flex-col overflow-hidden bg-[var(--color-warm-bg)] pt-4">
            <div className="px-12 py-6 border-b border-[var(--color-soft-border)] flex items-center justify-between shrink-0 bg-white shadow-sm z-10">
                <div>
                    <h4 className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-tight">人物关系矩阵</h4>
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1">
                        行：评价者 | 列：被评价者
                    </p>
                </div>
                {onSaveAll && (
                    <button
                        onClick={onSaveAll}
                        className="px-6 py-3 bg-[var(--color-cyan-dark)] text-white rounded-2xl font-black text-[10px] uppercase tracking-widest flex items-center hover:bg-[var(--color-cyan-main)] transition-all shadow-xl shadow-cyan-900/20"
                    >
                        <Save size={16} className="mr-2" /> 保存矩阵修改
                    </button>
                )}
            </div>

            <div className="flex-1 overflow-auto custom-scrollbar p-8">
                <div className="inline-block min-w-full align-middle bg-white/40 backdrop-blur-xl rounded-[2.5rem] p-8 border border-white/60 shadow-inner">
                    <table className="border-separate border-spacing-2">
                        <thead>
                            <tr>
                                <th className="p-4"></th>
                                {characters.map(name => (
                                    <th key={name} className="p-4 min-w-[140px]">
                                        <div className="flex flex-col items-center space-y-2">
                                            <div className="w-12 h-12 rounded-xl bg-[var(--color-cyan-light)] flex items-center justify-center text-[var(--color-cyan-dark)] shadow-sm">
                                                <User size={20} />
                                            </div>
                                            <span className="text-[11px] font-black text-[var(--color-cyan-dark)] uppercase tracking-tighter">
                                                {name}
                                            </span>
                                        </div>
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {characters.map(evaluator => (
                                <tr key={evaluator}>
                                    <td className="p-4 min-w-[120px]">
                                        <div className="flex items-center space-x-3 justify-end text-right">
                                            <span className="text-[11px] font-black text-[var(--color-cyan-dark)] uppercase tracking-tighter">
                                                {evaluator}
                                            </span>
                                            <div className="w-10 h-10 rounded-xl bg-[var(--color-cyan-dark)] flex items-center justify-center text-white shadow-md">
                                                <User size={16} />
                                            </div>
                                        </div>
                                    </td>
                                    {characters.map(evaluatee => {
                                        if (evaluator === evaluatee) {
                                            return (
                                                <td key={evaluatee} className="p-2">
                                                    <div className="w-full h-24 rounded-2xl bg-slate-100/50 border-2 border-dashed border-slate-200 flex items-center justify-center text-slate-300">
                                                        <X size={20} className="opacity-20" />
                                                    </div>
                                                </td>
                                            );
                                        }

                                        const rel = relationshipMap[evaluator]?.[evaluatee];
                                        return (
                                            <td key={evaluatee} className="p-2">
                                                <button
                                                    onClick={() => handleCellClick(evaluator, evaluatee)}
                                                    className={`w-full h-24 rounded-[1.5rem] p-4 flex flex-col items-start justify-between text-left transition-all group relative overflow-hidden ${
                                                        rel 
                                                        ? 'bg-white border-2 border-[var(--color-cyan-main)]/10 hover:border-[var(--color-cyan-main)]/40 hover:shadow-lg hover:-translate-y-1' 
                                                        : 'bg-slate-50 border-2 border-dashed border-slate-200 hover:border-[var(--color-cyan-main)]/30'
                                                    }`}
                                                >
                                                    {rel ? (
                                                        <>
                                                            <div className="flex items-center space-x-2">
                                                                <Heart size={10} className="text-[var(--color-yellow-main)]" />
                                                                <span className="text-[10px] font-black text-[var(--color-cyan-dark)] tracking-tighter truncate w-full">
                                                                    {rel.surface}
                                                                </span>
                                                            </div>
                                                            <div className="text-[9px] font-bold text-slate-400 line-clamp-2 leading-tight">
                                                                {rel.inner}
                                                            </div>
                                                            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                                <MessageSquare size={12} className="text-[var(--color-cyan-main)]" />
                                                            </div>
                                                        </>
                                                    ) : (
                                                        <div className="flex-1 flex items-center justify-center w-full text-[9px] font-black text-slate-300 uppercase tracking-widest">
                                                            未定义关系
                                                        </div>
                                                    )}
                                                </button>
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Editing Overlay/Modal */}
            {selectedCell && (
                <div className="fixed inset-0 z-[2000] flex items-center justify-center p-8 bg-[var(--color-cyan-dark)]/40 backdrop-blur-md animate-in fade-in duration-300">
                    <div className="w-full max-w-xl bg-white rounded-[3rem] p-10 border border-white shadow-2xl relative animate-in zoom-in-95 duration-300 shadow-cyan-900/40">
                        <button 
                            onClick={() => setSelectedCell(null)}
                            className="absolute top-8 right-8 p-3 bg-slate-100 text-slate-400 rounded-2xl hover:bg-[var(--color-yellow-main)] hover:text-white transition-all shadow-sm"
                        >
                            <X size={20} />
                        </button>

                        <div className="flex items-center space-x-4 mb-8">
                            <div className="flex items-center">
                                <div className="w-12 h-12 rounded-2xl bg-[var(--color-cyan-dark)] flex items-center justify-center text-white font-black shadow-lg">
                                    {selectedCell.evaluator[0]}
                                </div>
                                <div className="mx-4 h-px w-8 bg-slate-200" />
                                <div className="w-12 h-12 rounded-2xl bg-[var(--color-cyan-light)] flex items-center justify-center text-[var(--color-cyan-dark)] font-black border-2 border-[var(--color-cyan-main)]/20 shadow-md">
                                    {selectedCell.evaluatee[0]}
                                </div>
                            </div>
                            <div>
                                <h3 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight">关系编辑</h3>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                    {selectedCell.evaluator} 对 {selectedCell.evaluatee} 的态度
                                </p>
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div className="flex flex-col space-y-2">
                                <label className="text-[10px] font-black text-[var(--color-cyan-main)] ml-1 uppercase tracking-widest flex items-center">
                                    <Heart size={12} className="mr-2" /> 表面态度 (Surface Attitude)
                                </label>
                                <input
                                    type="text"
                                    value={relationshipMap[selectedCell.evaluator]?.[selectedCell.evaluatee]?.surface || ''}
                                    onChange={(e) => onUpdateRow(selectedCell.rowIndex, '表面态度', e.target.value)}
                                    placeholder="例如：正常交流、礼貌敷衍..."
                                    className="w-full px-6 py-4 bg-slate-50 border-2 border-[var(--color-cyan-main)]/10 rounded-2xl text-sm font-bold text-[var(--color-cyan-dark)] focus:border-[var(--color-cyan-main)] outline-none transition-all placeholder:text-slate-300"
                                />
                            </div>

                            <div className="flex flex-col space-y-2">
                                <label className="text-[10px] font-black text-[var(--color-cyan-main)] ml-1 uppercase tracking-widest flex items-center">
                                    <ShieldAlert size={12} className="mr-2" /> 内心真实评价 (Inner Thoughts)
                                </label>
                                <textarea
                                    value={relationshipMap[selectedCell.evaluator]?.[selectedCell.evaluatee]?.inner || ''}
                                    onChange={(e) => onUpdateRow(selectedCell.rowIndex, '内心真实评价', e.target.value)}
                                    placeholder="此人内心的真实看法..."
                                    rows={4}
                                    className="w-full px-6 py-4 bg-slate-50 border-2 border-[var(--color-cyan-main)]/10 rounded-2xl text-sm font-bold text-[var(--color-cyan-dark)] focus:border-[var(--color-cyan-main)] outline-none transition-all resize-none placeholder:text-slate-300"
                                />
                            </div>
                        </div>

                        <div className="mt-10 flex space-x-4">
                            <button
                                onClick={() => setSelectedCell(null)}
                                className="flex-1 py-4 bg-[var(--color-cyan-dark)] text-white rounded-[1.5rem] font-bold text-xs uppercase tracking-[0.2em] shadow-xl shadow-cyan-900/30 hover:bg-[var(--color-cyan-main)] transition-all flex items-center justify-center"
                            >
                                <Save size={16} className="mr-3" /> 完成编辑并应用
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
