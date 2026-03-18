import { useEffect, useState, useMemo } from 'react';
import { gameApi } from '../api/gameApi';
import { Cloud, Trash2, Rocket, RotateCcw, Search } from 'lucide-react';

export const WorkshopBrowser = () => {
    const [items, setItems] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        loadItems();
    }, []);

    const loadItems = async () => {
        setLoading(true);
        try {
            const res = await gameApi.getWorkshopList();
            setItems(res.data || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const filteredItems = useMemo(() => {
        if (!searchQuery.trim()) return items;
        const query = searchQuery.toLowerCase();
        return items.filter(item =>
            item.name?.toLowerCase().includes(query) ||
            item.description?.toLowerCase().includes(query) ||
            item.author?.toLowerCase().includes(query)
        );
    }, [items, searchQuery]);

    const handleApply = async (id: string, name: string) => {
        const confirm = window.confirm(`警告：应用 [${name}] 将会彻底覆盖服务器当前的所有 Prompt 和事件文件！确认继续？`);
        if (!confirm) return;

        setLoading(true);
        try {
            await gameApi.applyWorkshopMod(id);
            setMessage(`模组 [${name}] 已成功部署。请返回游戏首页并确保重载！`);
            setTimeout(() => setMessage(''), 5000);
        } catch (e) {
            alert('部署失败');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex-1 flex flex-col h-full bg-white/80 backdrop-blur-md rounded-2xl border-2 border-[var(--color-cyan-main)]/20 shadow-xl overflow-hidden p-8 relative">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
                <div>
                    <h2 className="text-2xl font-black text-[var(--color-cyan-dark)] flex items-center tracking-wide">
                        <Cloud className="mr-3 text-[var(--color-cyan-main)]" />
                        创意工坊
                    </h2>
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto">
                    <div className="relative flex-1 md:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-cyan-main)]/50" size={18} />
                        <input
                            type="text"
                            placeholder="搜索模组、作者或描述..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 bg-white border-2 border-[var(--color-cyan-main)]/10 rounded-full text-sm font-bold focus:border-[var(--color-cyan-main)] focus:outline-none transition-all"
                        />
                    </div>
                    <button
                        onClick={loadItems}
                        disabled={loading}
                        className="p-2 bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] rounded-full hover:bg-[var(--color-cyan-main)] hover:text-white transition-all shadow-sm disabled:opacity-50 shrink-0"
                    >
                        <RotateCcw size={20} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            {message && (
                <div className="mb-6 p-4 bg-cyan-500/10 border border-cyan-500/30 text-cyan-700 rounded-xl font-bold text-sm animate-fade-in-up">
                    {message}
                </div>
            )}

            {loading && items.length === 0 ? (
                <div className="text-[var(--color-cyan-main)] font-black tracking-widest uppercase flex items-center"><span className="typing-cursor"></span> 同步中...</div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6 overflow-y-auto custom-scrollbar pr-2">
                    {filteredItems.length === 0 && (
                        <div className="col-span-full text-[var(--color-cyan-dark)]/50 font-bold text-center py-20">
                            {searchQuery ? "未找到匹配的模组" : "目前工坊空空如也..."}
                        </div>
                    )}
                    {filteredItems.map(item => (
                        <div key={item.id} className="border-2 border-[var(--color-cyan-main)]/10 p-5 rounded-2xl shadow-sm hover:shadow-[var(--color-cyan-main)]/20 hover:border-[var(--color-cyan-main)]/30 transition-all bg-white flex flex-col relative group">

                            <div className="flex justify-between items-start mb-2 pr-6">
                                <h3 className="font-black text-lg text-[var(--color-cyan-dark)] truncate">{item.name}</h3>
                            </div>

                            <div className="mb-3">
                                <span className="text-[10px] bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] px-2 py-0.5 rounded-full font-black tracking-widest uppercase mr-2">
                                    {item.type === 'prompt_pack' ? '全域设定包' : item.type}
                                </span>
                            </div>

                            <p className="text-sm text-[var(--color-cyan-dark)]/70 font-semibold mb-4 line-clamp-2 min-h-[2.5rem]">{item.description}</p>

                            <div className="flex justify-between items-center text-[10px] text-[var(--color-cyan-dark)]/40 font-black mb-4 uppercase tracking-tighter">
                                <span>作者: {item.author}</span>
                                <span>{item.downloads} 应用</span>
                            </div>

                            <button
                                onClick={() => handleApply(item.id, item.name)}
                                disabled={loading}
                                className="w-full py-3 bg-[var(--color-cyan-main)] text-white rounded-xl flex items-center justify-center font-black hover:bg-[var(--color-cyan-dark)] transition shadow-md uppercase tracking-widest disabled:opacity-50"
                            >
                                <Rocket size={16} className="mr-2" /> 应用此模组
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};
