import { Plus, Trash2, UploadCloud, Edit3 } from 'lucide-react';

interface CharacterEditorProps {
    parsedRoster: any;
    onUpdateItem: (id: string, field: string, value: any) => void;
    onUploadAvatar: (id: string, file: File) => void;
    onEditSettings: (char: any) => void;
    onAddNew: () => void;
    onDelete: (id: string, name: string) => void;
}

export const CharacterEditor = ({
    parsedRoster,
    onUpdateItem,
    onUploadAvatar,
    onEditSettings,
    onAddNew,
    onDelete
}: CharacterEditorProps) => {
    return (
        <div className="flex-1 flex flex-col overflow-hidden">
            <div className="px-12 py-8 border-b border-slate-50 flex items-center justify-between shrink-0 bg-slate-50/30">
                <div>
                    <h4 className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-tight">角色管理</h4>
                </div>
                <button
                    onClick={onAddNew}
                    className="px-6 py-3 bg-[var(--color-cyan-dark)] text-white rounded-2xl font-black text-[10px] uppercase tracking-widest flex items-center hover:bg-[var(--color-cyan-main)] transition-all shadow-xl shadow-cyan-900/20"
                >
                    <Plus size={16} className="mr-2" /> 新增角色档案
                </button>
            </div>
            <div className="flex-1 overflow-y-auto custom-scrollbar p-12">
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                    {parsedRoster && Object.entries(parsedRoster).map(([id, char]: [string, any]) => (
                        <div key={id} className="bg-white/50 backdrop-blur-sm rounded-[2rem] p-6 border border-slate-100 hover:border-[var(--color-cyan-main)]/30 transition-all group/card relative shadow-sm hover:shadow-xl hover:-translate-y-1">
                            <button
                                onClick={() => onDelete(id, char.name)}
                                className="absolute top-4 right-4 p-2.5 bg-[var(--color-yellow-light)] text-[var(--color-yellow-main)] rounded-xl opacity-0 group-hover/card:opacity-100 transition-all hover:bg-[var(--color-yellow-main)] hover:text-white"
                                title="删除角色"
                            >
                                <Trash2 size={14} />
                            </button>

                            <div className="flex flex-col md:flex-row gap-6">
                                <div className="flex flex-col items-center space-y-3 shrink-0">
                                    <div
                                        className="w-24 h-24 rounded-2xl overflow-hidden bg-[var(--color-cyan-light)] border-2 border-white shadow-md relative group/avatar cursor-pointer"
                                        onClick={() => document.getElementById(`avatar-input-${id}`)?.click()}
                                    >
                                        <img src={char.avatar} className="w-full h-full object-cover" />
                                        <div className="absolute inset-0 bg-[var(--color-cyan-dark)]/40 flex items-center justify-center opacity-0 group-hover/avatar:opacity-100 transition-all">
                                            <UploadCloud className="text-white" size={20} />
                                        </div>
                                        <input
                                            id={`avatar-input-${id}`}
                                            type="file"
                                            className="hidden"
                                            accept="image/*"
                                            onChange={(e) => {
                                                const file = e.target.files?.[0];
                                                if (file) onUploadAvatar(id, file);
                                            }}
                                        />
                                    </div>
                                    <div className="px-3 py-1 bg-[var(--color-cyan-light)] rounded-lg text-[8px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest">
                                        {id.slice(0, 8)}
                                    </div>
                                </div>

                                <div className="flex-1 space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-1">
                                            <label className="text-[10px] font-bold text-[var(--color-cyan-main)] ml-1">角色姓名</label>
                                            <input
                                                value={char.name}
                                                onChange={(e) => onUpdateItem(id, 'name', e.target.value)}
                                                className="w-full px-4 py-2.5 bg-white/80 rounded-xl border border-slate-100 text-sm font-bold focus:ring-2 focus:ring-[var(--color-cyan-main)]/20 focus:border-[var(--color-cyan-main)] outline-none transition-all"
                                                placeholder="例: 林飒"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-[10px] font-bold text-[var(--color-cyan-main)] ml-1">身份标签</label>
                                            <input
                                                value={char.archetype}
                                                onChange={(e) => onUpdateItem(id, 'archetype', e.target.value)}
                                                className="w-full px-4 py-2.5 bg-white/80 rounded-xl border border-slate-100 text-sm font-bold focus:ring-2 focus:ring-[var(--color-cyan-main)]/20 focus:border-[var(--color-cyan-main)] outline-none transition-all"
                                                placeholder="例: 高冷学姐"
                                            />
                                        </div>
                                    </div>
                                    <div className="space-y-1">
                                        <label className="text-[10px] font-bold text-[var(--color-cyan-main)] ml-1">立绘资源路径</label>
                                        <input
                                            value={char.avatar}
                                            onChange={(e) => onUpdateItem(id, 'avatar', e.target.value)}
                                            className="w-full px-4 py-2.5 bg-slate-50/50 rounded-xl border border-slate-100 text-[10px] font-mono focus:bg-white focus:border-[var(--color-cyan-main)] outline-none transition-all"
                                        />
                                    </div>
                                    <div className="pt-4">
                                        <button
                                            onClick={() => onEditSettings(char)}
                                            className="w-full py-3 bg-[var(--color-cyan-dark)] text-white rounded-xl font-black text-[10px] uppercase tracking-widest flex items-center justify-center hover:bg-[var(--color-cyan-main)] transition-all shadow-lg shadow-cyan-900/10 active:scale-[0.98]"
                                        >
                                            <Edit3 size={14} className="mr-2 text-[var(--color-yellow-main)]" /> 编辑角色设定
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};
