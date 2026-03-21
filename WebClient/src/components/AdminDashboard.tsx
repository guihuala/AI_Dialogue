import { useState, useEffect } from 'react';
import { gameApi } from '../api/gameApi';
import { Shield, RefreshCw, LogOut, Database, History, FileClock } from 'lucide-react';
import { ConfirmDialog } from './common/ConfirmDialog';
import { AdminLoginPanel } from './admin/AdminLoginPanel';
import { AdminWorkshopTab } from './admin/AdminWorkshopTab';
import { AdminStorageTab } from './admin/AdminStorageTab';
import { AdminUsersTab } from './admin/AdminUsersTab';
import { AdminAuditTab } from './admin/AdminAuditTab';

export const AdminDashboard = () => {
    const [activeTab, setActiveTab] = useState<'workshop' | 'storage' | 'users' | 'audit'>('workshop');
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [password, setPassword] = useState('');
    const [authError, setAuthError] = useState<string | null>(null);
    const [items, setItems] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [cleaning, setCleaning] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editForm, setEditForm] = useState({ name: '', author: '', description: '' });
    const [userState, setUserState] = useState<any>(null);
    const [quota, setQuota] = useState<any>(null);
    const [auditRows, setAuditRows] = useState<any[]>([]);
    const [adminUsers, setAdminUsers] = useState<any[]>([]);
    const [adminUserStats, setAdminUserStats] = useState<any>(null);
    const [adminUserQuery, setAdminUserQuery] = useState('');
    const [adminUserPage, setAdminUserPage] = useState(1);
    const [adminUserPagination, setAdminUserPagination] = useState<any>(null);
    const [confirmDialog, setConfirmDialog] = useState<{
        open: boolean;
        title: string;
        message: string;
        confirmText?: string;
        danger?: boolean;
        onConfirm?: () => Promise<void> | void;
    }>({ open: false, title: '', message: '' });

    useEffect(() => {
        const bootstrapAdminSession = async () => {
            const token = localStorage.getItem('admin_token');
            if (!token) return;
            try {
                await gameApi.getAdminSession();
                setIsAuthenticated(true);
            } catch {
                localStorage.removeItem('admin_token');
                setIsAuthenticated(false);
            }
        };
        bootstrapAdminSession();
    }, []);

    useEffect(() => {
        if (isAuthenticated) {
            loadItems();
        }
    }, [isAuthenticated]);

    const loadItems = async () => {
        setLoading(true);
        try {
            const [wsRes, stateRes, quotaRes, auditRes] = await Promise.all([
                gameApi.getWorkshopList(),
                gameApi.getUserState(),
                gameApi.getStorageQuota(),
                gameApi.getUserAudit(20)
            ]);
            setItems(wsRes.data || []);
            setUserState(stateRes.data || null);
            setQuota(quotaRes.data || null);
            setAuditRows(auditRes.data || []);
            setAuthError(null);
        } catch (e) {
            console.error(e);
            const status = (e as any)?.response?.status;
            if (status === 401) {
                localStorage.removeItem('admin_token');
                setIsAuthenticated(false);
                setAuthError('管理员会话已失效，请重新验证。');
            }
        } finally {
            setLoading(false);
        }
    };

    const loadAdminUsers = async (targetPage?: number) => {
        try {
            const page = targetPage || adminUserPage;
            const [usersRes, statsRes] = await Promise.all([
                gameApi.getAdminUsers({
                    q: adminUserQuery.trim(),
                    sort_by: 'updated_at',
                    sort_order: 'desc',
                    page,
                    page_size: 20
                }),
                gameApi.getAdminUserStats()
            ]);
            setAdminUsers(usersRes?.data || []);
            setAdminUserPagination(usersRes?.pagination || null);
            setAdminUserStats(statsRes?.data || null);
        } catch (e) {
            const status = (e as any)?.response?.status;
            if (status === 401) {
                localStorage.removeItem('admin_token');
                setIsAuthenticated(false);
                setAuthError('管理员会话已失效，请重新验证。');
            }
        }
    };

    useEffect(() => {
        if (!isAuthenticated || activeTab !== 'users') return;
        loadAdminUsers();
    }, [isAuthenticated, activeTab, adminUserPage]);

    useEffect(() => {
        if (!isAuthenticated || activeTab !== 'users') return;
        setAdminUserPage(1);
        loadAdminUsers(1);
    }, [adminUserQuery]);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setAuthError(null);
        try {
            const res = await gameApi.adminLogin(password);
            const token = res?.data?.token;
            if (!token) {
                throw new Error('missing token');
            }
            localStorage.setItem('admin_token', token);
            setIsAuthenticated(true);
            setPassword('');
        } catch (e) {
            const detail = (e as any)?.response?.data?.detail || '验证失败：口令不正确';
            setAuthError(detail);
        }
    };

    const handleDelete = async (id: string, name: string) => {
        setConfirmDialog({
            open: true,
            title: '彻底删除模组',
            message: `确认要彻底删除模组 [${name}] 吗？此操作不可撤销。`,
            confirmText: '确认删除',
            danger: true,
            onConfirm: async () => {
                try {
                    await gameApi.deleteWorkshopItem(id);
                    loadItems();
                } catch (e) {
                    alert('删除失败');
                }
            }
        });
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
            await gameApi.updateWorkshopItem(editingId, editForm);
            setEditingId(null);
            loadItems();
        } catch (e) {
            alert('更新失败');
        } finally {
            setLoading(false);
        }
    };

    const handleCleanup = async (dryRun: boolean) => {
        setCleaning(true);
        try {
            const res = await gameApi.cleanupStorage({
                dry_run: dryRun,
                keep_recent_library: 100,
                keep_recent_snapshots: 20
            });
            const data = res?.data || {};
            const removedLib = data?.removed?.library?.length || 0;
            const removedSnap = data?.removed?.snapshots?.length || 0;
            if (dryRun) {
                alert(`预估可清理：library ${removedLib} 项，snapshots ${removedSnap} 项`);
            } else {
                alert(`已清理：library ${removedLib} 项，snapshots ${removedSnap} 项`);
                loadItems();
            }
        } catch (e) {
            alert('清理失败');
        } finally {
            setCleaning(false);
        }
    };

    if (!isAuthenticated) {
        return (
            <AdminLoginPanel
                password={password}
                authError={authError}
                onChangePassword={setPassword}
                onSubmit={handleLogin}
            />
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
                        onClick={() => handleCleanup(true)}
                        disabled={cleaning}
                        className="px-3 py-2 bg-white border border-[var(--color-cyan-main)]/20 text-[var(--color-cyan-main)] rounded-xl hover:bg-[var(--color-cyan-light)] transition-all disabled:opacity-50 text-xs font-black"
                        title="预览清理结果"
                    >
                        预览清理
                    </button>
                    <button
                        onClick={() => handleCleanup(false)}
                        disabled={cleaning}
                        className="px-3 py-2 bg-amber-50 border border-amber-200 text-amber-700 rounded-xl hover:bg-amber-100 transition-all disabled:opacity-50 text-xs font-black"
                        title="执行智能清理"
                    >
                        执行清理
                    </button>
                    <button
                        onClick={loadItems}
                        disabled={loading}
                        className="p-3 bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] rounded-xl hover:bg-[var(--color-cyan-main)] hover:text-white transition-all disabled:opacity-50"
                        title="刷新列表"
                    >
                        <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
                    </button>
                    <button
                        onClick={async () => {
                            try {
                                await gameApi.adminLogout();
                            } catch {}
                            localStorage.removeItem('admin_token');
                            setIsAuthenticated(false);
                        }}
                        className="p-3 bg-red-50 text-red-500 rounded-xl hover:bg-red-500 hover:text-white transition-all"
                        title="退出管理模式"
                    >
                        <LogOut size={20} />
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-hidden bg-[var(--color-cyan-light)]/10 rounded-3xl border border-[var(--color-cyan-main)]/5 flex flex-col">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4 border-b border-[var(--color-cyan-main)]/10 bg-white/60">
                    <div className="rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white p-4">
                        <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] flex items-center gap-2">
                            <Database size={12} />
                            当前激活
                        </div>
                        <div className="mt-2 text-sm font-black text-[var(--color-cyan-dark)]">
                            {userState?.active_source || 'default'} / {userState?.active_mod_id || 'default'}
                        </div>
                    </div>
                    <div className="rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white p-4">
                        <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] flex items-center gap-2">
                            <History size={12} />
                            快照留存
                        </div>
                        <div className="mt-2 text-sm font-black text-[var(--color-cyan-dark)]">
                            last: {userState?.last_good_snapshot_id || '-'}
                        </div>
                    </div>
                    <div className="rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white p-4">
                        <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] flex items-center gap-2">
                            <FileClock size={12} />
                            存储配额
                        </div>
                        <div className="mt-2 text-sm font-black text-[var(--color-cyan-dark)]">
                            {quota?.usage?.library_items || 0}/{quota?.limits?.library_items || 0} 模组
                        </div>
                        <div className="text-[10px] text-slate-400 font-bold">
                            {(quota?.usage?.library_bytes || 0) / (1024 * 1024) > 0 ? `${((quota?.usage?.library_bytes || 0) / (1024 * 1024)).toFixed(1)} MB` : '0 MB'}
                        </div>
                        {Array.isArray(quota?.warnings) && quota.warnings.length > 0 && (
                            <div className="text-[10px] text-amber-600 font-black mt-1">
                                {quota.warnings.join('；')}
                            </div>
                        )}
                    </div>
                </div>

                <div className="px-4 pt-4 border-b border-[var(--color-cyan-main)]/10 bg-white/40">
                    <div className="inline-flex rounded-2xl bg-[var(--color-cyan-light)]/40 p-1 border border-[var(--color-cyan-main)]/10">
                        <button
                            onClick={() => setActiveTab('workshop')}
                            className={`px-5 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${activeTab === 'workshop' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-main)] hover:bg-white'}`}
                        >
                            工坊内容
                        </button>
                        <button
                            onClick={() => setActiveTab('storage')}
                            className={`px-5 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${activeTab === 'storage' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-main)] hover:bg-white'}`}
                        >
                            存储与状态
                        </button>
                        <button
                            onClick={() => setActiveTab('audit')}
                            className={`px-5 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${activeTab === 'audit' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-main)] hover:bg-white'}`}
                        >
                            操作审计
                        </button>
                        <button
                            onClick={() => setActiveTab('users')}
                            className={`px-5 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${activeTab === 'users' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-main)] hover:bg-white'}`}
                        >
                            用户管理
                        </button>
                    </div>
                </div>

                <div className="flex-1 overflow-auto custom-scrollbar bg-white/50">
                    {activeTab === 'workshop' && (
                        <AdminWorkshopTab
                            items={items}
                            loading={loading}
                            editingId={editingId}
                            editForm={editForm}
                            setEditForm={setEditForm}
                            onStartEdit={startEdit}
                            onUpdate={handleUpdate}
                            onCancelEdit={() => setEditingId(null)}
                            onDelete={handleDelete}
                        />
                    )}

                    {activeTab === 'storage' && (
                        <AdminStorageTab
                            userState={userState}
                            quota={quota}
                            cleaning={cleaning}
                            onCleanup={handleCleanup}
                        />
                    )}

                    {activeTab === 'users' && (
                        <AdminUsersTab
                            adminUserQuery={adminUserQuery}
                            setAdminUserQuery={setAdminUserQuery}
                            adminUsers={adminUsers}
                            adminUserStats={adminUserStats}
                            adminUserPagination={adminUserPagination}
                            setAdminUserPage={setAdminUserPage}
                            onRefresh={() => loadAdminUsers()}
                        />
                    )}

                    {activeTab === 'audit' && (
                        <AdminAuditTab auditRows={auditRows} />
                    )}
                </div>

                <div className="mt-auto p-4 bg-[var(--color-cyan-main)]/5 border-t border-[var(--color-cyan-main)]/10 text-[9px] font-black text-[var(--color-cyan-main)]/40 uppercase tracking-[0.4em] text-center">
                    Mokukeki Admin Interface v2.0.0
                </div>
            </div>

            <ConfirmDialog
                open={confirmDialog.open}
                title={confirmDialog.title}
                message={confirmDialog.message}
                confirmText={confirmDialog.confirmText || '确认'}
                danger={!!confirmDialog.danger}
                onCancel={() => setConfirmDialog({ open: false, title: '', message: '' })}
                onConfirm={async () => {
                    const handler = confirmDialog.onConfirm;
                    setConfirmDialog({ open: false, title: '', message: '' });
                    if (handler) await handler();
                }}
            />
        </div>
    );
};
