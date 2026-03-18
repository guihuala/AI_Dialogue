import { useState } from 'react';
import { Save, UploadCloud, Quote, Terminal, User, Hash } from 'lucide-react';

interface CharacterDetailModalProps {
    char: any;
    charContent: string;
    onClose: () => void;
    onSave: (id: string, updates: any, mdContent: string) => void;
    onUploadAvatar: (id: string, file: File) => void;
}

export const CharacterDetailModal = ({
    char,
    charContent,
    onClose,
    onSave,
    onUploadAvatar
}: CharacterDetailModalProps) => {
    const [name, setName] = useState(char.name || '');
    const [archetype, setArchetype] = useState(char.archetype || '');
    const [avatar, setAvatar] = useState(char.avatar || '');
    const [tags, setTags] = useState(char.tags ? char.tags.join(', ') : '');
    const [prompt, setPrompt] = useState(charContent || '');
    const [quotes, setQuotes] = useState(char.quotes ? char.quotes.join('\n') : '');

    const handleSave = () => {
        const tagList = tags.split(',').map((t: string) => t.trim()).filter((t: string) => t);
        const quoteList = quotes.split('\n').map((q: string) => q.trim()).filter((q: string) => q);
        onSave(char.id, {
            name,
            archetype,
            avatar,
            tags: tagList,
            quotes: quoteList
        }, prompt);
    };

    return (
        <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-[var(--color-cyan-dark)]/60 backdrop-blur-xl p-4 md:p-10 animate-fade-in">
            <div className="bg-white w-full max-w-5xl h-full max-h-[90vh] rounded-[3rem] shadow-2xl border border-white flex flex-col overflow-hidden relative animate-zoom-in">
                {/* Header */}
                <div className="px-8 py-6 border-b border-[var(--color-soft-border)] flex items-center justify-between bg-white shrink-0">
                    <div className="flex items-center space-x-4">
                        <div className="w-12 h-12 rounded-2xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] flex items-center justify-center shadow-inner">
                            <User size={24} />
                        </div>
                        <div>
                            <h3 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight">角色详细设定</h3>
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">编辑身份、形象与核心提示词</p>
                        </div>
                    </div>
                    <div className="flex items-center space-x-3">
                        <button 
                            onClick={onClose}
                            className="px-6 py-2.5 bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] rounded-xl font-black text-[10px] uppercase tracking-widest hover:bg-[var(--color-cyan-main)] hover:text-white transition-all"
                        >
                            取消
                        </button>
                        <button 
                            onClick={handleSave}
                            className="px-8 py-2.5 bg-[var(--color-cyan-dark)] text-white rounded-xl font-black text-[10px] uppercase tracking-widest flex items-center hover:bg-[var(--color-cyan-main)] transition-all shadow-lg shadow-cyan-900/20"
                        >
                            <Save size={14} className="mr-2" /> 同步所有修改
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 flex flex-col md:flex-row overflow-hidden bg-[var(--color-warm-bg)]/30">
                    {/* Left Panel: Basic Info */}
                    <div className="w-full md:w-80 border-r border-[var(--color-soft-border)] p-8 overflow-y-auto custom-scrollbar flex flex-col space-y-8 bg-white/50">
                        <div className="flex flex-col items-center space-y-4">
                            <div 
                                className="w-48 h-48 rounded-[2rem] overflow-hidden bg-[var(--color-cyan-light)] border-4 border-white shadow-xl relative group cursor-pointer"
                                onClick={() => document.getElementById('detail-avatar-input')?.click()}
                            >
                                <img src={avatar} className="w-full h-full object-cover" />
                                <div className="absolute inset-0 bg-[var(--color-cyan-dark)]/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all">
                                    <UploadCloud className="text-white" size={32} />
                                </div>
                                <input id="detail-avatar-input" type="file" className="hidden" accept="image/*" onChange={(e) => e.target.files?.[0] && onUploadAvatar(char.id, e.target.files[0])} />
                            </div>
                            <div className="w-full px-4 py-2 bg-[var(--color-cyan-light)] rounded-xl border border-[var(--color-cyan-main)]/10 text-center">
                                <span className="text-[10px] font-mono text-[var(--color-cyan-main)] truncate block">{avatar}</span>
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">角色姓名</label>
                                <input 
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="w-full px-4 py-3 bg-white rounded-xl border-2 border-[var(--color-cyan-main)]/5 focus:border-[var(--color-cyan-main)] outline-none font-bold text-[var(--color-cyan-dark)] transition-all"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">身份/原型</label>
                                <input 
                                    value={archetype}
                                    onChange={(e) => setArchetype(e.target.value)}
                                    className="w-full px-4 py-3 bg-white rounded-xl border-2 border-[var(--color-cyan-main)]/5 focus:border-[var(--color-cyan-main)] outline-none font-bold text-[var(--color-cyan-dark)] transition-all"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 flex items-center">
                                    <Hash size={10} className="mr-1" /> 标签库 (逗号分隔)
                                </label>
                                <textarea 
                                    value={tags}
                                    onChange={(e) => setTags(e.target.value)}
                                    className="w-full px-4 py-3 bg-white rounded-xl border-2 border-[var(--color-cyan-main)]/5 focus:border-[var(--color-cyan-main)] outline-none font-bold text-xs text-[var(--color-cyan-dark)] h-24 resize-none transition-all"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Right Panel: Advanced Config */}
                    <div className="flex-1 p-8 overflow-y-auto custom-scrollbar space-y-10">
                        <section className="space-y-4">
                            <div className="flex items-center space-x-2">
                                <Terminal size={18} className="text-[var(--color-cyan-main)]" />
                                <h4 className="text-sm font-black text-[var(--color-cyan-dark)] uppercase tracking-widest">核心提示词设定 (System Prompt)</h4>
                            </div>
                            <div className="relative">
                                <textarea 
                                    value={prompt}
                                    onChange={(e) => setPrompt(e.target.value)}
                                    className="w-full px-6 py-6 bg-white rounded-3xl border-2 border-[var(--color-cyan-main)]/10 focus:border-[var(--color-cyan-main)] outline-none font-medium text-sm text-[var(--color-life-text)] h-[300px] resize-none transition-all shadow-inner leading-relaxed"
                                    placeholder="输入该角色的核心性格、说话方式、背景故事..."
                                />
                                <div className="absolute top-4 right-4 animate-pulse">
                                    <div className="w-2 h-2 rounded-full bg-[var(--color-cyan-main)] shadow-[0_0_10px_var(--color-cyan-main)]" />
                                </div>
                            </div>
                        </section>

                        <section className="space-y-4">
                            <div className="flex items-center space-x-2">
                                <Quote size={18} className="text-[var(--color-yellow-main)]" />
                                <h4 className="text-sm font-black text-[var(--color-cyan-dark)] uppercase tracking-widest">角色经典语录 (自动采样)</h4>
                            </div>
                            <textarea 
                                value={quotes}
                                onChange={(e) => setQuotes(e.target.value)}
                                className="w-full px-6 py-6 bg-white rounded-3xl border-2 border-[var(--color-yellow-main)]/10 focus:border-[var(--color-yellow-main)] outline-none font-medium text-xs text-[var(--color-life-text)] h-40 resize-none transition-all shadow-inner leading-loose"
                                placeholder="输入经典台词，每行一条..."
                            />
                            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest bg-slate-50 px-3 py-1 rounded-full inline-block italic">
                                * 系统将在生成对话时随机参考这些语录，以维持角色语调一致性
                            </p>
                        </section>
                    </div>
                </div>
            </div>
        </div>
    );
};
