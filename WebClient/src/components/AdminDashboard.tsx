import { useState, useEffect } from 'react';
import { gameApi } from '../api/gameApi';
import { Shield, Trash2, Edit2, Check, X, RefreshCw, LogOut, Package } from 'lucide-react';

export const AdminDashboard = () => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [password, setPassword] = useState('');
    const [items, setItems] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editForm, setEditForm] = useState({ name: '', author: '', description: '' });

    // Simple hardcoded admin password for demonstration
    // In a real app, this should be verified against a backend
    const ADMIN_PASSWORD = 'admin'; 

    useEffect(() => {
        if (isAuthenticated) {
            loadItems();
        }
    }, [isAuthenticated]);

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

    const handleLogin = (e: React.FormEvent) => {
        e.preventDefault();
        if (password === ADMIN_PASSWORD) {
            setIsAuthenticated(true);
        } else {
            alert('验证失败：口令不正确');
        }
    };

    const handleDelete = async (id: string, name: string) => {
        if (!window.confirm(`确认要彻底删除模组 [${name}] 吗？此操作不可撤销。`)) return;
        try {
            await gameApi.deleteWorkshopMod(id);
            loadItems();
        } catch (e) {
            alert('删除失败');
        }
    };

    const startEdit = (item: any) => {
        setEditingId(item.id);
        setEditForm({
            name: item.name || '',
            author: item.author || '',
            description: item.description || ''
        });
    };

    const handleUpdate = async () => {
        if (!editingId) return;
        setLoading(true);
        try {
            await gameApi.updateWorkshopMod(editingId, editForm);
            setEditingId(null);
            loadItems();
        } catch (e) {
            alert('更新失败');
        } finally {
            setLoading(false);
        }
    };

    if (!isAuthenticated) {
        return (
            <div className="flex-1 flex items-center justify-center p-8">
                <div className="w-full max-w-md bg-white/90 backdrop-blur-xl p-8 rounded-[2.5rem] border-2 border-[var(--color-cyan-main)]/20 shadow-2xl animate-fade-in">
                    <div className="flex flex-col items-center mb-8">
                        <div className="w-16 h-16 bg-[var(--color-cyan-main)]/10 rounded-2xl flex items-center justify-center mb-4">
                            <Shield size={32} className="text-[var(--color-cyan-main)]" />
                        </div>
                        <h2 className="text-2xl font-black text-[var(--color-cyan-dark)] uppercase tracking-widest">管理员验证</h2>
                        <p className="text-[10px] font-black text-[var(--color-cyan-main)]/60 mt-2 uppercase tracking-[0.3em]">Access Restricted</p>
                    </div>

                    <form onSubmit={handleLogin} className="space-y-6">
                        <div className="relative">
                            <input
                                type="password"
                                placeholder="输入管理口令..."
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full px-6 py-4 bg-[var(--color-cyan-light)]/30 border-2 border-[var(--color-cyan-main)]/10 rounded-2xl focus:border-[var(--color-cyan-main)] focus:outline-none font-bold text-center transition-all"
                                autoFocus
                            />
                        </div>
                        <button
                            type="submit"
                            className="w-full py-4 bg-[var(--color-cyan-dark)] text-white rounded-2xl font-black uppercase tracking-[0.2em] hover:bg-[var(--color-cyan-main)] transition-all shadow-lg active:scale-[0.98]"
                        >
                            执行身份注入
                        </button>
                    </form>
                    
                    <p className="mt-8 text-center text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                        Unauthorized access is monitored.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col h-full bg-white/80 backdrop-blur-md rounded-[2.5rem] border-2 border-[var(--color-cyan-main)]/20 shadow-2xl overflow-hidden p-8 animate-fade-in-up">
            <div className="flex justify-between items-center mb-8 shrink-0">
                <div className="flex items-center">
                    <div className="w-12 h-12 bg-[var(--color-cyan-main)] text-white rounded-xl flex items-center justify-center mr-4 shadow-lg shadow-cyan-500/20">
                        <Shield size={24} />
                    </div>
                    <div>
                        <h2 className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-tight">后台资源管理中心</h2>
                        <div className="flex items-center gap-2">
                            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                            <p className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.3em]">Authorized Session Active</p>
                        </div>
                    </div>
                </div>
                
                <div className="flex items-center gap-3">
                    <button
                        onClick={loadItems}
                        disabled={loading}
                        className="p-3 bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] rounded-xl hover:bg-[var(--color-cyan-main)] hover:text-white transition-all disabled:opacity-50"
                        title="刷新列表"
                    >
                        <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
                    </button>
                    <button
                        onClick={() => setIsAuthenticated(false)}
                        className="p-3 bg-red-50 text-red-500 rounded-xl hover:bg-red-500 hover:text-white transition-all"
                        title="退出管理模式"
                    >
                        <LogOut size={20} />
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-hidden bg-[var(--color-cyan-light)]/10 rounded-3xl border border-[var(--color-cyan-main)]/5 flex flex-col">
                <div className="p-6 border-b border-[var(--color-cyan-main)]/10 bg-white/50 overflow-hidden">
                   <div className="flex items-center justify-between mb-4">
                        <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.2em] flex items-center">
                            <Package size={14} className="mr-2" /> 创意工坊已发布项目 ({items.length})
                        </h3>
                   </div>

                   <div className="overflow-x-auto custom-scrollbar">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="text-[10px] font-black text-[var(--color-cyan-main)]/50 uppercase tracking-widest border-b border-[var(--color-cyan-main)]/5">
                                    <th className="px-4 py-3 pb-4">ID / 类型</th>
                                    <th className="px-4 py-3 pb-4">模组名称</th>
                                    <th className="px-4 py-3 pb-4">作者</th>
                                    <th className="px-4 py-3 pb-4 w-1/3">描述</th>
                                    <th className="px-4 py-3 pb-4 text-right">管理操作</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[var(--color-cyan-main)]/5">
                                {items.length === 0 && !loading && (
                                    <tr>
                                        <td colSpan={5} className="py-20 text-center text-slate-400 font-bold">暂无已发布的模组数据</td>
                                    </tr>
                                )}
                                {items.map(item => (
                                    <tr key={item.id} className="group hover:bg-[var(--color-cyan-main)]/5 transition-colors">
                                        <td className="px-4 py-4">
                                            <div className="font-mono text-[10px] text-slate-400">#{item.id}</div>
                                            <div className="text-[8px] bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] px-2 py-0.5 rounded-full inline-block mt-1 font-black uppercase">{item.type}</div>
                                        </td>
                                        <td className="px-4 py-4 font-black text-[var(--color-cyan-dark)]">
                                            {editingId === item.id ? (
                                                <input
                                                    className="w-full bg-white border border-[var(--color-cyan-main)]/30 rounded px-2 py-1 text-sm outline-none focus:border-[var(--color-cyan-main)]"
                                                    value={editForm.name}
                                                    onChange={e => setEditForm({...editForm, name: e.target.value})}
                                                />
                                            ) : item.name}
                                        </td>
                                        <td className="px-4 py-4 font-bold text-slate-600">
                                            {editingId === item.id ? (
                                                <input
                                                    className="w-full bg-white border border-[var(--color-cyan-main)]/30 rounded px-2 py-1 text-sm outline-none focus:border-[var(--color-cyan-main)]"
                                                    value={editForm.author}
                                                    onChange={e => setEditForm({...editForm, author: e.target.value})}
                                                />
                                            ) : item.author}
                                        </td>
                                        <td className="px-4 py-4">
                                            {editingId === item.id ? (
                                                <textarea
                                                    className="w-full bg-white border border-[var(--color-cyan-main)]/30 rounded px-2 py-1 text-xs outline-none focus:border-[var(--color-cyan-main)] resize-none"
                                                    rows={2}
                                                    value={editForm.description}
                                                    onChange={e => setEditForm({...editForm, description: e.target.value})}
                                                />
                                            ) : (
                                                <p className="text-xs text-slate-500 font-medium line-clamp-2 leading-relaxed">{item.description}</p>
                                            )}
                                        </td>
                                        <td className="px-4 py-4 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                {editingId === item.id ? (
                                                    <>
                                                        <button 
                                                            onClick={handleUpdate}
                                                            className="p-2 text-green-500 hover:bg-green-50 rounded-lg transition"
                                                            title="确认保存"
                                                        >
                                                            <Check size={18} />
                                                        </button>
                                                        <button 
                                                            onClick={() => setEditingId(null)}
                                                            className="p-2 text-slate-400 hover:bg-slate-50 rounded-lg transition"
                                                            title="取消"
                                                        >
                                                            <X size={18} />
                                                        </button>
                                                    </>
                                                ) : (
                                                    <>
                                                        <button 
                                                            onClick={() => startEdit(item)}
                                                            className="p-2 text-[var(--color-cyan-main)] hover:bg-[var(--color-cyan-light)] rounded-lg transition"
                                                            title="编辑基本信息"
                                                        >
                                                            <Edit2 size={18} />
                                                        </button>
                                                        <button 
                                                            onClick={() => handleDelete(item.id, item.name)}
                                                            className="p-2 text-red-400 hover:bg-red-50 rounded-lg transition"
                                                            title="彻底下架模组"
                                                        >
                                                            <Trash2 size={18} />
                                                        </button>
                                                    </>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                   </div>
                </div>
                
                <div className="mt-auto p-4 bg-[var(--color-cyan-main)]/5 border-t border-[var(--color-cyan-main)]/10 text-[9px] font-black text-[var(--color-cyan-main)]/40 uppercase tracking-[0.4em] text-center">
                    Project AntiGravity Admin Interface v1.0.4
                </div>
            </div>
        </div>
    );
};
