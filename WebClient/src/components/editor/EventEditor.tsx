import { useState, useMemo } from 'react';
import { Plus, Trash2, ScrollText, Search, ArrowLeft } from 'lucide-react';

interface EventEditorProps {
    parsedCsv: { headers: string[], rows: Record<string, string>[] } | null;
    onUpdateRow: (rowIndex: number, field: string, value: string) => void;
    onAddNew: () => void;
    onDeleteRow: (index: number, name: string) => void;
    onBack?: () => void;
    filter?: { chapter?: string, type?: string };
    focusMode?: 'default' | 'opening';
    canEdit?: boolean;
}

export const EventEditor = ({
    parsedCsv,
    onUpdateRow,
    onAddNew,
    onDeleteRow,
    onBack,
    filter,
    focusMode = 'default',
    canEdit = true
}: EventEditorProps) => {
    const [searchTerm, setSearchTerm] = useState('');
    const isOpeningFocus = focusMode === 'opening';
    
    const filteredRows = useMemo(() => {
        if (!parsedCsv) return [];
        return parsedCsv.rows.map((row, index) => ({ ...row, originalIndex: index }))
            .filter(rowItem => {
               const row = rowItem as any;
               const values = Object.values(row).map(v => String(v).toLowerCase());
               const matchesSearch = searchTerm === '' || 
                  values.some(val => val.includes(searchTerm.toLowerCase()));
               
               const matchesChapter = !filter?.chapter || 
                  String(row['所属章节']) === filter.chapter;
               
               const matchesType = !filter?.type || 
                  (filter.type === 'Boss' ? row['是否Boss'] === 'TRUE' : 
                   filter.type === 'General' ? (row['事件类型'] === '随机池' || row['事件类型'] === '通用池') :
                   filter.type === 'Persona' ? row['事件类型'] === '专属池' :
                   (typeof row['事件类型'] === 'string' && String(row['事件类型']).includes(filter.type)) || filter.type === 'ANY');
               
               return matchesSearch && matchesChapter && matchesType;
            });
    }, [parsedCsv, searchTerm, filter]);

    const getRenderHeaders = () => {
        if (!parsedCsv?.headers) return [];
        if (!isOpeningFocus) return parsedCsv.headers;
        const preferredOrder = ['事件标题', '场景与冲突描述', '预设剧本', '玩家交互', '结果', 'Event_ID'];
        const preferred = preferredOrder.filter((h) => parsedCsv.headers.includes(h));
        const others = parsedCsv.headers.filter((h) => !preferredOrder.includes(h));
        return [...preferred, ...others];
    };

    return (
        <div className="flex-1 flex flex-col overflow-hidden bg-[var(--color-warm-bg)]">
            <div className="px-8 py-6 border-b border-[var(--color-soft-border)] flex flex-col md:flex-row md:items-center justify-between shrink-0 bg-white shadow-sm gap-4">
                <div className="flex items-center space-x-4">
                    {onBack && (
                        <button 
                            onClick={onBack}
                            className="p-2 hover:bg-[var(--color-cyan-light)] rounded-xl text-[var(--color-cyan-main)] transition-all border border-[var(--color-soft-border)]"
                        >
                            <ArrowLeft size={18} />
                        </button>
                    )}
                    <div className="text-left">
                        <h4 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight leading-none mb-1">
                            {isOpeningFocus ? '开场固定剧情编辑' : '剧情事件池'}
                        </h4>
                        {filter && (
                             <div className="flex items-center text-[var(--color-cyan-main)]/60 text-[10px] font-black uppercase tracking-widest">
                                 <span>{filter.chapter ? `学年 ${filter.chapter}` : '跨学年'}</span>
                                 <span className="mx-2 opacity-30">•</span>
                                 <span>{filter.type || '所有类型'}</span>
                             </div>
                        )}
                        {isOpeningFocus && (
                            <div className="text-[10px] font-black text-[var(--color-cyan-main)]/70 uppercase tracking-widest mt-1">
                                重点编辑「预设剧本」对话内容，条件字段默认弱化显示
                            </div>
                        )}
                    </div>
                </div>
                
                <div className="flex items-center space-x-3">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-cyan-main)]/30" size={14} />
                        <input 
                            type="text"
                            placeholder="搜索事件..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="pl-9 pr-4 py-2 bg-[var(--color-cyan-light)]/30 rounded-xl border border-transparent text-[var(--color-cyan-dark)] text-xs font-bold outline-none focus:bg-white focus:border-[var(--color-cyan-main)] transition-all w-48"
                        />
                    </div>
                    <button
                        onClick={onAddNew}
                        disabled={!canEdit}
                        className="px-6 py-2.5 bg-[var(--color-cyan-dark)] text-white rounded-xl font-black text-[10px] uppercase tracking-widest flex items-center hover:bg-[var(--color-cyan-main)] transition-all shadow-xl shadow-cyan-900/20"
                    >
                        <Plus size={14} className="mr-2" /> {canEdit ? '新增项' : '模板只读'}
                    </button>
                </div>
            </div>
            <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
                <div className="grid grid-cols-1 gap-6">
                    {filteredRows.map((rowItem) => {
                        const row = rowItem as any;
                        return (
                            <div key={row.originalIndex} className="bg-white rounded-2xl p-6 border border-[var(--color-soft-border)] hover:border-[var(--color-cyan-main)]/30 transition-all group/card relative shadow-sm hover:shadow-md">
                                <button
                                    onClick={() => onDeleteRow(row.originalIndex, (parsedCsv?.headers && row[parsedCsv.headers[0]]) || `行 ${row.originalIndex + 1}`)}
                                    disabled={!canEdit}
                                    className="absolute top-4 right-4 p-2 text-[var(--color-yellow-main)] hover:bg-[var(--color-yellow-light)] rounded-xl opacity-0 group-hover/card:opacity-100 transition-all"
                                >
                                    <Trash2 size={14} />
                                </button>
                                
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 text-left">
                                    {getRenderHeaders().map((h) => {
                                        const isDialogueField = h === '预设剧本';
                                        const isSecondaryField = isOpeningFocus && ['触发条件', '专属角色', '是否Boss', '事件类型', '潜在冲突点', '所属章节'].includes(h);
                                        const fieldClass = isDialogueField
                                            ? 'md:col-span-4 space-y-1'
                                            : isOpeningFocus && (h === '场景与冲突描述' || h === '玩家交互' || h === '结果')
                                                ? 'md:col-span-2 space-y-1'
                                                : 'space-y-1';
                                        const inputRows = isDialogueField ? 6 : 1;
                                        return (
                                        <div key={h} className={fieldClass}>
                                            <label className="text-[10px] font-black text-[var(--color-cyan-main)]/50 ml-1 uppercase tracking-widest leading-none">{h}</label>
                                            <textarea
                                                value={row[h]}
                                                onChange={(e) => onUpdateRow(row.originalIndex, h, e.target.value)}
                                                disabled={!canEdit}
                                                className={`w-full px-4 py-3 rounded-xl border border-transparent text-sm font-bold text-[var(--color-cyan-dark)] focus:bg-white focus:border-[var(--color-cyan-main)] outline-none transition-all resize-none overflow-hidden ${
                                                    isDialogueField
                                                        ? 'bg-[var(--color-yellow-light)]/40 border-[var(--color-yellow-main)]/30'
                                                        : isSecondaryField
                                                            ? 'bg-slate-100/60 text-slate-500'
                                                            : 'bg-[var(--color-cyan-light)]/20'
                                                }`}
                                                rows={inputRows}
                                                onInput={(e) => {
                                                    const target = e.target as HTMLTextAreaElement;
                                                    target.style.height = 'auto';
                                                    target.style.height = target.scrollHeight + 'px';
                                                }}
                                            />
                                        </div>
                                    );})}
                                </div>
                            </div>
                        );
                    })}
                    {filteredRows.length === 0 && (
                        <div className="flex flex-col items-center justify-center py-20 opacity-20">
                            <ScrollText size={48} className="mb-4 text-[var(--color-cyan-main)]" />
                            <p className="text-sm font-black uppercase tracking-widest text-[var(--color-cyan-dark)]">暂无匹配事件数据</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
