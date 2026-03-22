import { useState, useEffect } from 'react';
import { gameApi } from '../api/gameApi';
import { Shield, RefreshCw, LogOut, Database, History, FileClock, PanelLeft, X } from 'lucide-react';
import { ConfirmDialog } from './common/ConfirmDialog';
import { AdminLoginPanel } from './admin/AdminLoginPanel';
import { AdminWorkshopTab } from './admin/AdminWorkshopTab';
import { AdminStorageTab } from './admin/AdminStorageTab';
import { AdminUsersTab } from './admin/AdminUsersTab';
import { AdminAuditTab } from './admin/AdminAuditTab';
import { AdminPresetEditorTab } from './admin/AdminPresetEditorTab';

export const AdminDashboard = () => {
    const [activeTab, setActiveTab] = useState<'workshop' | 'preset' | 'storage' | 'users' | 'audit'>('workshop');
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
    const [mobileNavOpen, setMobileNavOpen] = useState(false);
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

    const tabItems: Array<{ id: 'workshop' | 'preset' | 'storage' | 'audit' | 'users'; label: string; desc: string }> = [
        { id: 'workshop', label: '工坊内容', desc: '公开模组管理' },
        { id: 'preset', label: '模板编辑', desc: '默认/预设编辑器' },
        { id: 'storage', label: '存储与状态', desc: '配额与快照清理' },
        { id: 'audit', label: '操作审计', desc: '最近管理操作' },
        { id: 'users', label: '用户管理', desc: '账号与会话概览' },
    ];

    const renderActiveTab = () => {
        if (activeTab === 'workshop') {
            return (
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
            );
        }
        if (activeTab === 'storage') {
            return (
                <AdminStorageTab
                    userState={userState}
                    quota={quota}
                    cleaning={cleaning}
                    onCleanup={handleCleanup}
                />
            );
        }
        if (activeTab === 'preset') {
            return <AdminPresetEditorTab />;
        }
        if (activeTab === 'users') {
            return (
                <AdminUsersTab
                    adminUserQuery={adminUserQuery}
                    setAdminUserQuery={setAdminUserQuery}
                    adminUsers={adminUsers}
                    adminUserStats={adminUserStats}
                    adminUserPagination={adminUserPagination}
                    setAdminUserPage={setAdminUserPage}
                    onRefresh={() => loadAdminUsers()}
                />
            );
        }
        return <AdminAuditTab auditRows={auditRows} />;
    };

    return (
        <div className="flex-1 h-full min-h-0 bg-white/80 backdrop-blur-md rounded-[2.5rem] border-2 border-[var(--color-cyan-main)]/20 shadow-2xl overflow-hidden animate-fade-in-up">
            <div className="h-full min-h-0 flex flex-col">
                <div className="shrink-0 px-6 py-4 border-b border-[var(--color-cyan-main)]/10 bg-white/70">
                    <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3 min-w-0">
                            <div className="w-11 h-11 bg-[var(--color-cyan-main)] text-white rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/20">
                                <Shield size={22} />
                            </div>
                            <div className="min-w-0">
                                <h2 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight truncate">后台资源管理中心</h2>
                                <div className="flex items-center gap-2">
                                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                                    <p className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.25em]">Authorized Session Active</p>
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                            <button
                                onClick={() => setMobileNavOpen(true)}
                                className="lg:hidden p-3 bg-white border border-[var(--color-cyan-main)]/20 text-[var(--color-cyan-main)] rounded-xl hover:bg-[var(--color-cyan-light)] transition-all"
                                title="打开导航"
                            >
                                <PanelLeft size={18} />
                            </button>
                            <button
                                onClick={() => handleCleanup(true)}
                                disabled={cleaning}
                                className="hidden sm:inline-flex px-3 py-2 bg-white border border-[var(--color-cyan-main)]/20 text-[var(--color-cyan-main)] rounded-xl hover:bg-[var(--color-cyan-light)] transition-all disabled:opacity-50 text-xs font-black"
                                title="预览清理结果"
                            >
                                预览清理
                            </button>
                            <button
                                onClick={() => handleCleanup(false)}
                                disabled={cleaning}
                                className="hidden sm:inline-flex px-3 py-2 bg-amber-50 border border-amber-200 text-amber-700 rounded-xl hover:bg-amber-100 transition-all disabled:opacity-50 text-xs font-black"
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
                                <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
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
                                <LogOut size={18} />
                            </button>
                        </div>
                    </div>
                </div>

                <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[240px_minmax(0,1fr)] gap-0">
                    <aside className="hidden lg:block border-r border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/15 p-4 min-h-0 overflow-auto custom-scrollbar">
                        <div className="space-y-2">
                            {tabItems.map((tab) => (
                                <button
                                    key={tab.id}
                                    onClick={() => {
                                        setActiveTab(tab.id);
                                        setMobileNavOpen(false);
                                    }}
                                    className={`w-full text-left rounded-xl border px-3 py-2.5 transition-all ${
                                        activeTab === tab.id
                                            ? 'border-[var(--color-cyan-main)] bg-[var(--color-cyan-main)]/10'
                                            : 'border-[var(--color-cyan-main)]/10 bg-white hover:bg-[var(--color-cyan-light)]/40'
                                    }`}
                                >
                                    <div className="text-sm font-black text-[var(--color-cyan-dark)]">{tab.label}</div>
                                    <div className="text-[10px] font-bold text-slate-500 mt-0.5">{tab.desc}</div>
                                </button>
                            ))}
                        </div>

                        <div className="mt-4 space-y-2">
                            <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-3">
                                <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] flex items-center gap-1">
                                    <Database size={11} />
                                    当前激活
                                </div>
                                <div className="mt-1.5 text-xs font-black text-[var(--color-cyan-dark)] break-all">
                                    {userState?.active_source || 'default'} / {userState?.active_mod_id || 'default'}
                                </div>
                            </div>
                            <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-3">
                                <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] flex items-center gap-1">
                                    <History size={11} />
                                    快照留存
                                </div>
                                <div className="mt-1.5 text-xs font-black text-[var(--color-cyan-dark)] break-all">
                                    {userState?.last_good_snapshot_id || '-'}
                                </div>
                            </div>
                            <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-3">
                                <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] flex items-center gap-1">
                                    <FileClock size={11} />
                                    存储配额
                                </div>
                                <div className="mt-1.5 text-xs font-black text-[var(--color-cyan-dark)]">
                                    {quota?.usage?.library_items || 0}/{quota?.limits?.library_items || 0} 模组
                                </div>
                            </div>
                        </div>
                    </aside>

                    <main className="min-h-0 bg-white/45">
                        <div className={`h-full min-h-0 ${activeTab === 'preset' ? 'overflow-hidden' : 'overflow-auto custom-scrollbar'}`}>
                            {renderActiveTab()}
                        </div>
                    </main>
                </div>
            </div>

            {mobileNavOpen && (
                <div className="lg:hidden fixed inset-0 z-50">
                    <div className="absolute inset-0 bg-slate-900/35" onClick={() => setMobileNavOpen(false)} />
                    <div className="absolute inset-y-0 left-0 w-[300px] max-w-[85vw] bg-white border-r border-[var(--color-cyan-main)]/15 shadow-2xl p-4 overflow-auto custom-scrollbar">
                        <div className="flex items-center justify-between mb-3">
                            <div className="text-sm font-black text-[var(--color-cyan-dark)]">后台导航</div>
                            <button
                                onClick={() => setMobileNavOpen(false)}
                                className="p-2 rounded-lg text-slate-500 hover:bg-slate-100"
                            >
                                <X size={16} />
                            </button>
                        </div>
                        <div className="space-y-2">
                            {tabItems.map((tab) => (
                                <button
                                    key={`mobile-${tab.id}`}
                                    onClick={() => {
                                        setActiveTab(tab.id);
                                        setMobileNavOpen(false);
                                    }}
                                    className={`w-full text-left rounded-xl border px-3 py-2.5 transition-all ${
                                        activeTab === tab.id
                                            ? 'border-[var(--color-cyan-main)] bg-[var(--color-cyan-main)]/10'
                                            : 'border-[var(--color-cyan-main)]/10 bg-white hover:bg-[var(--color-cyan-light)]/40'
                                    }`}
                                >
                                    <div className="text-sm font-black text-[var(--color-cyan-dark)]">{tab.label}</div>
                                    <div className="text-[10px] font-bold text-slate-500 mt-0.5">{tab.desc}</div>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            )}

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
