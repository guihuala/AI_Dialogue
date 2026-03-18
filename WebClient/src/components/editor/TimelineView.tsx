import { useState } from 'react';
import { 
    Zap, 
    Box, 
    GitBranch, 
    UserSearch, 
    ChevronRight, 
    Settings2,
    Save,
    CalendarDays,
    Star
} from 'lucide-react';

interface TimelineViewProps {
    content: string;
    onSave: (content: string) => void;
    onSelectPool: (chapter: string, poolType: string) => void;
}

export const TimelineView = ({ content, onSave, onSelectPool }: TimelineViewProps) => {
    let timeline: Record<string, string[]> = {};
    try {
        timeline = JSON.parse(content);
    } catch (e) {
        return (
            <div className="flex-1 flex items-center justify-center text-[var(--color-cyan-dark)] font-black">
                解析 timeline.json 失败: {(e as Error).message}
            </div>
        );
    }

    const [isEditing, setIsEditing] = useState(false);
    const [editContent, setEditContent] = useState(content);

    const poolIcons: Record<string, any> = {
        'Boss': Zap,
        '通用': Box,
        '条件': GitBranch,
        '随机或专属': UserSearch,
        '随机池': Box,
        '固定': Star,
    };

    const poolColors: Record<string, string> = {
        'Boss': 'bg-[var(--color-cyan-dark)]',
        '通用': 'bg-[var(--color-cyan-main)]',
        '条件': 'bg-[var(--color-yellow-main)]',
        '随机或专属': 'bg-[var(--color-cyan-light)]',
        '固定': 'bg-[var(--color-yellow-light)]',
    };

    const years = ['1', '2', '3', '4'];
    const yearNames: Record<string, string> = {
        '1': '大一 / 启程',
        '2': '大二 / 磨合',
        '3': '大三 / 抉择',
        '4': '大四 / 终焉'
    };

    if (isEditing) {
        return (
            <div className="flex-1 flex flex-col p-8 space-y-4 bg-[var(--color-warm-bg)]">
                <div className="flex items-center justify-between">
                    <h4 className="text-xl font-black text-[var(--color-cyan-dark)] uppercase">编辑时间轴配置 (JSON)</h4>
                    <div className="flex space-x-3">
                        <button 
                            onClick={() => setIsEditing(false)}
                            className="px-6 py-2 rounded-xl font-black bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white transition-all text-xs"
                        >
                            取消
                        </button>
                        <button 
                            onClick={() => {
                                onSave(editContent);
                                setIsEditing(false);
                            }}
                            className="px-6 py-2 rounded-xl font-black bg-[var(--color-cyan-main)] text-white hover:bg-[var(--color-cyan-dark)] transition-all flex items-center shadow-lg shadow-cyan-900/20 text-xs"
                        >
                            <Save size={14} className="mr-2" /> 保存配置
                        </button>
                    </div>
                </div>
                <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="flex-1 p-6 bg-[var(--color-cyan-dark)] text-[var(--color-cyan-light)] font-mono text-sm rounded-2xl border-4 border-[var(--color-cyan-main)]/20 focus:border-[var(--color-cyan-main)] outline-none transition-all resize-none shadow-inner"
                />
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col overflow-hidden bg-[var(--color-warm-bg)]">
            {/* Header */}
            <div className="px-8 py-6 border-b border-[var(--color-soft-border)] flex items-center justify-between shrink-0 bg-white shadow-sm">
                <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-xl bg-[var(--color-cyan-main)] text-white flex items-center justify-center">
                        <CalendarDays size={20} />
                    </div>
                    <div>
                        <h4 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight">剧情时间轴概览</h4>
                        <p className="text-[10px] font-bold text-[var(--color-cyan-dark)]/40 uppercase tracking-widest">定义每一学年的剧情步进顺序与事件池类型</p>
                    </div>
                </div>
                <button
                    onClick={() => {
                         setEditContent(content);
                         setIsEditing(true);
                    }}
                    className="px-6 py-3 bg-white border-2 border-[var(--color-cyan-main)]/10 text-[var(--color-cyan-dark)] rounded-xl font-black text-[10px] uppercase tracking-widest flex items-center hover:bg-[var(--color-cyan-light)] transition-all group"
                >
                    <Settings2 size={16} className="mr-2 text-[var(--color-cyan-main)] group-hover:rotate-90 transition-transform" /> 原始 JSON 编辑
                </button>
            </div>

            {/* Timeline Scrollable Area */}
            <div className="flex-1 overflow-auto custom-scrollbar bg-[var(--color-warm-bg)] p-12">
                <div className="flex items-start justify-between min-w-[1000px] w-full">
                    {years.map((year, yIdx) => (
                        <div key={year} className="flex-1 flex flex-col items-center">
                            {/* Year Header */}
                            <div className="mb-8 relative flex flex-col items-center w-full">
                                <div className="w-16 h-16 rounded-3xl bg-white shadow-xl flex items-center justify-center border-4 border-[var(--color-cyan-main)]/20 z-10 relative group hover:scale-110 transition-transform">
                                   <span className="text-2xl font-black text-[var(--color-cyan-dark)]">0{year}</span>
                                </div>
                                <div className="mt-4 px-4 py-1.5 bg-white rounded-full shadow-md border border-[var(--color-cyan-main)]/5">
                                    <span className="text-[10px] font-black text-[var(--color-cyan-dark)]/60 uppercase tracking-widest">{yearNames[year]}</span>
                                </div>
                                {yIdx < years.length - 1 && (
                                    <div className="absolute top-8 left-full w-24 h-1 border-t-2 border-dashed border-[var(--color-cyan-main)]/20"></div>
                                )}
                            </div>

                            {/* Steps Container */}
                            <div 
                                className="flex flex-col items-center space-y-4 pb-20"
                                onDragOver={(e) => e.preventDefault()}
                            >
                                {timeline[year]?.map((pool, pIdx) => {
                                    const Icon = poolIcons[pool] || Box;
                                    const color = poolColors[pool] || 'bg-[var(--color-cyan-main)]/20';
                                    const isLight = color.includes('light');
                                    
                                    return (
                                        <div 
                                            key={pIdx} 
                                            className="flex flex-col items-center group cursor-move"
                                            draggable
                                            onDragStart={(e) => {
                                                e.dataTransfer.setData('year', year);
                                                e.dataTransfer.setData('index', pIdx.toString());
                                            }}
                                            onDrop={(e) => {
                                                e.preventDefault();
                                                const fromYear = e.dataTransfer.getData('year');
                                                const fromIndex = parseInt(e.dataTransfer.getData('index'));
                                                
                                                if (fromYear !== year) return; // Only allow reordering within same year for now
                                                
                                                const newTimeline = { ...timeline };
                                                const currentPools = [...newTimeline[year]];
                                                const item = currentPools.splice(fromIndex, 1)[0];
                                                currentPools.splice(pIdx, 0, item);
                                                newTimeline[year] = currentPools;
                                                
                                                onSave(JSON.stringify(newTimeline, null, 4));
                                            }}
                                        >
                                            {/* Connector line */}
                                            {pIdx === 0 ? (
                                                <div className="w-1 h-8 bg-[var(--color-cyan-main)]/10"></div>
                                            ) : (
                                                <div className="w-1 h-6 bg-[var(--color-soft-border)]"></div>
                                            )}
                                            
                                            {/* Step Button */}
                                            <button 
                                                onClick={() => onSelectPool(year, pool)}
                                                className="w-48 p-4 bg-white rounded-2xl shadow-sm border border-[var(--color-soft-border)] hover:border-[var(--color-cyan-main)]/50 hover:shadow-xl hover:-translate-y-1 transition-all flex items-center space-x-4 group/btn relative"
                                            >
                                                {/* Drag Handle Indicator */}
                                                <div className="absolute -left-1 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col space-y-0.5">
                                                    <div className="w-1 h-1 bg-[var(--color-cyan-main)]/30 rounded-full"></div>
                                                    <div className="w-1 h-1 bg-[var(--color-cyan-main)]/30 rounded-full"></div>
                                                    <div className="w-1 h-1 bg-[var(--color-cyan-main)]/30 rounded-full"></div>
                                                </div>

                                                <div className={`w-10 h-10 rounded-xl ${color} ${isLight ? 'text-[var(--color-cyan-dark)]' : 'text-white'} flex items-center justify-center shadow-lg group-hover/btn:scale-110 transition-all`}>
                                                    <Icon size={18} />
                                                </div>
                                                <div className="flex flex-col items-start overflow-hidden text-left">
                                                    <span className="text-[9px] font-black text-[var(--color-life-text)]/20 uppercase leading-none mb-1">STEP 0{pIdx+1}</span>
                                                    <span className="text-xs font-black text-[var(--color-cyan-dark)] truncate w-full">{pool}</span>
                                                </div>
                                                <ChevronRight size={14} className="text-[var(--color-cyan-main)]/20 group-hover/btn:translate-x-1 transition-transform ml-auto" />
                                            </button>
                                        </div>
                                    );
                                })}
                                
                                <div className="mt-4 pt-4 border-t border-dashed border-[var(--color-soft-border)] w-full flex justify-center">
                                    <button 
                                        onClick={() => onSelectPool(year, 'ANY')}
                                        className="text-[10px] font-black text-[var(--color-cyan-main)] hover:text-[var(--color-cyan-dark)] transition-colors uppercase tracking-[0.2em]"
                                    >
                                        + 查看该年所有池
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                    
                    {/* End Indicator */}
                    <div className="flex flex-col items-center pt-4">
                         <div className="w-16 h-16 rounded-full border-4 border-dashed border-[var(--color-soft-border)] flex items-center justify-center text-[var(--color-cyan-main)]/20">
                            <span className="text-[10px] font-black uppercase tracking-widest rotate-90">GRADUATE</span>
                         </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
