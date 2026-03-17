import { useEffect, useState } from 'react';
import { gameApi } from '../api/gameApi';
import { Cloud, Trash2, Rocket, RotateCcw } from 'lucide-react';

export const WorkshopBrowser = () => {
    const [items, setItems] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');

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

    const handleDelete = async (id: string) => {
        if (!window.confirm("确定要从工坊删除这个包吗？")) return;
        try {
            await gameApi.deleteWorkshopMod(id);
            loadItems();
        } catch (e) {
            alert('删除失败');
        }
    };

    return (
        <div className="flex-1 flex flex-col h-full bg-white/80 backdrop-blur-md rounded-2xl border-2 border-[var(--color-cyan-main)]/20 shadow-xl overflow-hidden p-8 relative">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-black text-[var(--color-cyan-dark)] flex items-center tracking-wide">
                    <Cloud className="mr-3 text-[var(--color-cyan-main)]" />
                    创意工坊 (联机仓库)
                </h2>
                <button 
                    onClick={loadItems}
                    disabled={loading}
                    className="p-2 bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] rounded-full hover:bg-[var(--color-cyan-main)] hover:text-white transition-all shadow-sm disabled:opacity-50"
                >
                    <RotateCcw size={20} className={loading ? 'animate-spin' : ''} />
                </button>
            </div>
            
            {message && (
                <div className="mb-6 p-4 bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 rounded-xl font-bold text-sm animate-fade-in-up">
                    {message}
                </div>
            )}
            
            {loading && items.length === 0 ? (
                <div className="text-[var(--color-cyan-main)] font-black tracking-widest uppercase flex items-center"><span className="typing-cursor"></span> 同步中...</div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6 overflow-y-auto custom-scrollbar pr-2">
                    {items.length === 0 && <div className="col-span-full text-[var(--color-cyan-dark)]/50 font-bold">目前工坊空空如也...</div>}
                    {items.map(item => (
                        <div key={item.id} className="border-2 border-[var(--color-cyan-main)]/10 p-5 rounded-2xl shadow-sm hover:shadow-[var(--color-cyan-main)]/20 hover:border-[var(--color-cyan-main)]/30 transition-all bg-white flex flex-col relative group">
                            
                            <button 
                                onClick={() => handleDelete(item.id)}
                                className="absolute top-4 right-4 p-2 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
                                title="从工坊下架"
                            >
                                <Trash2 size={16} />
                            </button>

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
                                <Rocket size={16} className="mr-2" /> 应用此全量包
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};
