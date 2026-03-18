import { Plus, Trash2, UploadCloud, Edit3, Star } from 'lucide-react';

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
        <div className="flex-1 flex flex-col overflow-hidden bg-[var(--color-warm-bg)]">
            <div className="px-12 py-8 border-b border-[var(--color-soft-border)] flex items-center justify-between shrink-0 bg-white">
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
                        <div key={id} className="bg-white rounded-[2rem] p-6 border border-[var(--color-soft-border)] hover:border-[var(--color-cyan-main)]/30 transition-all group/card relative shadow-sm hover:shadow-xl hover:-translate-y-1">
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
                                    <button 
                                        onClick={() => onUpdateItem(id, 'is_player', !char.is_player)}
                                        className={`px-3 py-1.5 rounded-full text-[8px] font-black uppercase tracking-widest flex items-center transition-all ${char.is_player ? 'bg-[var(--color-yellow-main)] text-white shadow-lg' : 'bg-[var(--color-soft-border)] text-slate-400 opacity-40 hover:opacity-100'}`}
                                    >
                                        <Star size={10} className={`mr-1 ${char.is_player ? 'fill-white' : ''}`} />
                                        {char.is_player ? '主角 / MC' : '设为主角'}
                                    </button>
                                </div>

                                <div className="flex-1 space-y-4 text-left">
                                    <div className="flex flex-col space-y-1">
                                        <label className="text-[10px] font-black text-[var(--color-cyan-main)] ml-1 uppercase tracking-widest">
                                            {char.is_player ? '主角姓名' : '角色姓名'}
                                        </label>
                                        <div className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight px-1">
                                            {char.name}
                                        </div>
                                    </div>
                                    <div className="flex flex-col space-y-1">
                                        <label className="text-[10px] font-black text-[var(--color-cyan-main)] ml-1 uppercase tracking-widest">核心属性</label>
                                        <div className="text-xs font-bold text-[var(--color-life-text)] bg-[var(--color-cyan-light)]/50 px-4 py-2 rounded-xl inline-block">
                                            {char.archetype}
                                        </div>
                                    </div>
                                    
                                    <div className="pt-2">
                                        <button
                                            onClick={() => onEditSettings(char)}
                                            className="w-full py-3 bg-white border-2 border-[var(--color-cyan-main)]/10 text-[var(--color-cyan-dark)] rounded-xl font-black text-[10px] uppercase tracking-widest flex items-center justify-center hover:bg-[var(--color-cyan-light)] transition-all"
                                        >
                                            <Edit3 size={14} className="mr-2 text-[var(--color-cyan-main)]" /> 具体信息 & 详细设定
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
