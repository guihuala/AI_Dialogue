import { RefreshCw, FileText, Database } from 'lucide-react';
import { useMemo } from 'react';
import { Category } from './types';

interface EditorSidebarProps {
    sidebarCollapsed: boolean;
    showExplorer: boolean;
    activeCategory: Category;
    setActiveCategory: (cat: Category) => void;
    files: { md: string[], csv: string[] };
    selectedFile: { type: 'md' | 'csv', name: string } | null;
    setSelectedFile: (file: { type: 'md' | 'csv', name: string } | null) => void;
    onRefresh: () => void;
    categories: any[];
}

export const EditorSidebar = ({
    sidebarCollapsed,
    showExplorer,
    activeCategory,
    setActiveCategory,
    files,
    selectedFile,
    setSelectedFile,
    onRefresh,
    categories
}: EditorSidebarProps) => {

    const categorizedFiles = useMemo(() => {
        const result: Record<Category, { type: 'md' | 'csv', name: string }[]> = {
            world: [], char: [], event: [], skills: [], all: []
        };
        files.md.forEach(f => {
            const item = { type: 'md' as const, name: f };
            result.all.push(item);
            if (f.startsWith('world/') || f === 'main_system.md') result.world.push(item);
            else if (f.startsWith('characters/') || f.endsWith('roster.json')) result.char.push(item);
            else if (f.startsWith('skills/')) result.skills.push(item);
            else result.world.push(item);
        });
        files.csv.forEach(f => {
            const item = { type: 'csv' as const, name: f };
            result.all.push(item);
            if (f === 'timeline.json') {
                result.event.unshift(item); // Always put timeline at the top
            } else {
                result.event.push(item);
            }
        });
        return result;
    }, [files]);

    if (sidebarCollapsed) return null;

    return (
        <>
            <div className="w-16 md:w-20 border-r border-[var(--color-soft-border)] flex flex-col py-6 items-center space-y-4 shrink-0 bg-white transition-all animate-in slide-in-from-left fade-in">
                {categories.map(cat => (
                    <button
                        key={cat.id}
                        onClick={() => {
                            setActiveCategory(cat.id as Category);
                            setSelectedFile(null);
                        }}
                        title={cat.name}
                        className={`w-12 h-12 flex items-center justify-center rounded-2xl transition-all group relative ${activeCategory === cat.id ? 'bg-[var(--color-cyan-dark)] text-white shadow-lg shadow-cyan-900/20' : 'text-[var(--color-cyan-main)]/50 hover:bg-[var(--color-cyan-light)] hover:text-[var(--color-cyan-dark)]'}`}
                    >
                        <cat.icon size={20} className={`shrink-0 transition-transform ${activeCategory === cat.id ? 'scale-110' : 'group-hover:scale-110'}`} />
                        <div className="absolute left-full ml-4 px-3 py-1.5 bg-[var(--color-cyan-dark)] text-white text-[10px] font-black rounded-lg whitespace-nowrap z-50 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">
                            {cat.name}
                        </div>
                    </button>
                ))}

                <div className="mt-auto px-2">
                    <button
                        onClick={onRefresh}
                        className="w-12 h-12 flex items-center justify-center bg-white border border-[var(--color-soft-border)] rounded-2xl text-[var(--color-cyan-main)] hover:text-[var(--color-cyan-dark)] hover:border-[var(--color-cyan-main)] transition-all group"
                        title="刷新列表"
                    >
                        <RefreshCw size={18} className="group-hover:rotate-120 transition-transform" />
                    </button>
                </div>
            </div>

            {showExplorer && (
                <div className="w-56 md:w-64 border-r border-[var(--color-soft-border)] flex flex-col shrink-0 bg-[var(--color-warm-bg)] animate-in slide-in-from-left fade-in">
                    <div className="px-6 py-8 border-b border-[var(--color-soft-border)] bg-white shadow-sm">
                        <h3 className="text-lg font-black text-[var(--color-cyan-dark)] tracking-tight">资源列表</h3>
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-1">
                        {categorizedFiles[activeCategory].map(f => (
                            <div
                                key={f.name}
                                onClick={() => setSelectedFile(f)}
                                className={`px-4 py-3 rounded-xl flex items-center cursor-pointer transition-all border relative group ${selectedFile?.name === f.name ? 'border-[var(--color-cyan-main)] bg-white shadow-md text-[var(--color-cyan-dark)]' : 'border-transparent text-[var(--color-cyan-main)]/60 hover:bg-white hover:text-[var(--color-cyan-dark)]'}`}
                            >
                                <div className="mr-3">
                                    {f.type === 'md' ? <FileText size={14} className="opacity-40" /> : <Database size={14} className="opacity-40" />}
                                </div>
                                <span className="text-xs font-bold truncate">{f.name.split('/').pop()}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </>
    );
};
