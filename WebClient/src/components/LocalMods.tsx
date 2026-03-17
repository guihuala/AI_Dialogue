import { useState, useEffect } from 'react';
import { Settings, Trash2, Edit } from 'lucide-react';

export const LocalMods = () => {
    const [mods, setMods] = useState<Record<string, string>>({});
    const [editing, setEditing] = useState<string | null>(null);
    const [editContent, setEditContent] = useState('');

    useEffect(() => {
        loadMods();
    }, []);

    const loadMods = () => {
        const str = localStorage.getItem('customPrompts');
        if (str) {
            setMods(JSON.parse(str));
        }
    };

    const handleDelete = (name: string) => {
        const newMods = { ...mods };
        delete newMods[name];
        localStorage.setItem('customPrompts', JSON.stringify(newMods));
        setMods(newMods);
        alert(`已删除 ${name} 的覆写规则。`);
    };

    const handleSaveEdit = () => {
        if (!editing) return;
        const newMods = { ...mods, [editing]: editContent };
        localStorage.setItem('customPrompts', JSON.stringify(newMods));
        setMods(newMods);
        setEditing(null);
    };

    return (
        <div className="flex-1 flex flex-col h-full bg-white/80 backdrop-blur-md rounded-2xl border-2 border-[var(--color-cyan-main)]/20 shadow-xl overflow-hidden p-8 relative">
            <h2 className="text-2xl font-black text-[var(--color-cyan-dark)] mb-6 flex items-center tracking-wide">
                <Settings className="mr-3 text-[var(--color-cyan-main)]" />
                本地模组管理
            </h2>
            <p className="text-sm text-[var(--color-cyan-dark)]/70 font-bold mb-6">所有的独立覆写配置保存在你的浏览器中。当你开启新对局时，只要房间内存在该化名的舍友，游戏就会优先使用此处的提示词设定而不是系统的默认设定。</p>

            <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
                {Object.keys(mods).length === 0 && (
                    <div className="text-center text-[var(--color-cyan-dark)]/50 font-bold py-10">你的本地还没有安装任何模组配置。</div>
                )}
                
                {Object.entries(mods).map(([name, prompt]) => (
                    <div key={name} className="border-2 border-[var(--color-cyan-main)]/10 rounded-xl overflow-hidden shadow-sm bg-white">
                        <div className="px-6 py-4 bg-[var(--color-cyan-light)]/50 border-b-2 border-[var(--color-cyan-main)]/10 flex justify-between items-center">
                            <span className="font-black text-[var(--color-cyan-dark)] text-lg">角色名映射: <span className="text-[var(--color-cyan-main)]">{name}</span></span>
                            <div className="flex space-x-2">
                                <button 
                                    onClick={() => { setEditing(name); setEditContent(prompt); }}
                                    className="p-2 text-[var(--color-cyan-main)] hover:bg-[var(--color-cyan-main)]/10 rounded-lg transition"
                                >
                                    <Edit size={16} />
                                </button>
                                <button 
                                    onClick={() => handleDelete(name)}
                                    className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                        {editing === name ? (
                            <div className="p-4 bg-white flex flex-col">
                                <textarea 
                                    className="w-full h-40 p-4 font-mono text-sm bg-[var(--color-cyan-light)]/30 text-[var(--color-cyan-dark)] rounded-xl border-2 border-[var(--color-cyan-main)]/20 resize-none outline-none focus:border-[var(--color-yellow-main)] focus:ring-4 focus:ring-[var(--color-yellow-main)]/20 transition-all"
                                    value={editContent}
                                    onChange={(e) => setEditContent(e.target.value)}
                                />
                                <div className="mt-4 flex justify-end space-x-3">
                                    <button onClick={() => setEditing(null)} className="px-4 py-2 text-[var(--color-cyan-dark)]/60 font-black hover:bg-[var(--color-cyan-light)] rounded-lg tracking-widest uppercase transition-colors">取消</button>
                                    <button onClick={handleSaveEdit} className="px-4 py-2 bg-[var(--color-cyan-main)] text-white font-black rounded-lg shadow-md hover:bg-[var(--color-cyan-dark)] transition-colors tracking-widest uppercase">保存修改</button>
                                </div>
                            </div>
                        ) : (
                            <div className="p-6 bg-white">
                                <pre className="text-sm text-[var(--color-cyan-dark)]/80 whitespace-pre-wrap font-mono line-clamp-3 font-semibold">
                                    {prompt}
                                </pre>
                            </div>
                        )}
                    </div>
                ))}
            </div>
            
        </div>
    );
}
