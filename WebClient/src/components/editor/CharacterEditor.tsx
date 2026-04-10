import { Plus, Trash2, UploadCloud, Edit3, Star } from 'lucide-react';

interface CharacterEditorProps {
    parsedRoster: any;
    onUpdateItem: (id: string, field: string, value: any) => void;
    onUploadAvatar: (id: string, file: File) => void;
    onEditSettings: (char: any) => void;
    onAddNew: () => void;
    onDelete: (id: string, name: string) => void;
    canEdit?: boolean;
    hideHeader?: boolean;
}

export const CharacterEditor = ({
    parsedRoster,
    onUpdateItem,
    onUploadAvatar,
    onEditSettings,
    onAddNew,
    onDelete,
    canEdit = true,
    hideHeader = false,
}: CharacterEditorProps) => {
    return (
        <div className="flex-1 flex flex-col overflow-hidden bg-[var(--color-warm-bg)]">
            {!hideHeader && (
                <div className="px-7 py-6 border-b border-[var(--color-soft-border)] flex flex-col lg:flex-row lg:items-center justify-between shrink-0 bg-white gap-4">
                    <div className="space-y-1.5">
                        <h4 className="text-[2rem] leading-none font-black text-[var(--color-cyan-dark)] tracking-tight">角色管理</h4>
                        <div className="text-sm font-bold text-[var(--color-cyan-dark)]/45">集中维护角色档案、头像和核心设定入口。</div>
                    </div>
                    <button
                        onClick={onAddNew}
                        disabled={!canEdit}
                        className="inline-flex h-11 items-center justify-center gap-2 px-5 bg-[var(--color-cyan-dark)] text-white rounded-2xl font-black text-xs hover:bg-[var(--color-cyan-main)] transition-all shadow-sm"
                    >
                        <Plus size={16} /> {canEdit ? '新增角色档案' : '默认模板只读'}
                    </button>
                </div>
            )}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                    {parsedRoster && Object.entries(parsedRoster).map(([id, char]: [string, any]) => (
                        <div key={id} className="bg-white rounded-[2rem] p-6 border border-[var(--color-soft-border)] hover:border-[var(--color-cyan-main)]/22 transition-all group/card relative shadow-sm hover:shadow-lg">
                            <button
                                onClick={() => onDelete(id, char.name)}
                                disabled={!canEdit}
                                className="absolute top-4 right-4 p-2.5 bg-[var(--color-yellow-light)] text-[var(--color-yellow-main)] rounded-xl opacity-0 group-hover/card:opacity-100 transition-all hover:bg-[var(--color-yellow-main)] hover:text-white"
                                title="删除角色"
                            >
                                <Trash2 size={14} />
                            </button>

                            <div className="flex flex-col md:flex-row gap-6">
                                <div className="flex flex-col items-center space-y-3 shrink-0">
                                    <div
                                            className="w-24 h-24 rounded-2xl overflow-hidden bg-[var(--color-cyan-light)] border-2 border-white shadow-sm relative group/avatar cursor-pointer"
                                        onClick={() => {
                                            if (canEdit) {
                                                document.getElementById(`avatar-input-${id}`)?.click();
                                            }
                                        }}
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
                                            disabled={!canEdit}
                                            onChange={(e) => {
                                                const file = e.target.files?.[0];
                                                if (file) onUploadAvatar(id, file);
                                            }}
                                        />
                                    </div>
                                    <button 
                                        onClick={() => onUpdateItem(id, 'is_player', true)}
                                        disabled={!canEdit}
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
                                            disabled={!canEdit}
                                            className="w-full py-3 bg-white border border-[var(--color-cyan-main)]/12 text-[var(--color-cyan-dark)] rounded-2xl font-black text-sm flex items-center justify-center hover:bg-[var(--color-cyan-light)]/30 transition-all"
                                        >
                                            <Edit3 size={14} className="mr-2 text-[var(--color-cyan-main)]" /> {canEdit ? '编辑详细设定' : '模板设定只读'}
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
