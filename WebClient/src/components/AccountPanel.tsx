import { useEffect, useState } from 'react';
import { RefreshCcw, UserRound, LogIn, UserPlus, LogOut, Shield, Laptop, History } from 'lucide-react';
import { gameApi } from '../api/gameApi';

export const AccountPanel = () => {
    const [message, setMessage] = useState('');
    const [accountInfo, setAccountInfo] = useState<any>(null);
    const [accountLoading, setAccountLoading] = useState(false);
    const [accountActionLoading, setAccountActionLoading] = useState<'login' | 'register' | 'logout' | 'password' | 'bind' | 'sessions' | ''>('');
    const [sessions, setSessions] = useState<any[]>([]);
    const [auditRows, setAuditRows] = useState<any[]>([]);
    const [bindingPreview, setBindingPreview] = useState<any>(null);
    const [accountForm, setAccountForm] = useState({
        username: '',
        password: '',
        bindCurrentVisitor: true
    });
    const [passwordForm, setPasswordForm] = useState({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
    });
    const [bindStrategy, setBindStrategy] = useState<'keep_account' | 'overwrite_with_visitor'>('keep_account');

    const showMessage = (text: string) => {
        setMessage(text);
        window.setTimeout(() => setMessage(''), 3000);
    };

    const capabilityEntries = [
        {
            key: 'can_play_as_visitor',
            label: '匿名试玩',
            description: '不登录也能开始游戏并保存到当前访客目录。'
        },
        {
            key: 'can_edit_local_content',
            label: '本地编辑',
            description: '可编辑本地模组、副本与默认模板的另存版本。'
        },
        {
            key: 'can_download_workshop_mods',
            label: '下载工坊模组',
            description: '可将公共模组下载到自己的本地库。'
        },
        {
            key: 'can_publish_workshop_mods',
            label: '公开发布模组',
            description: '会绑定到正式账户名下，包含首次公开、更新与派生发布。'
        },
        {
            key: 'can_manage_account_security',
            label: '账户安全',
            description: '可修改密码、绑定访客数据。'
        },
        {
            key: 'can_manage_sessions',
            label: '多会话管理',
            description: '可查看已登录会话，并退出其他设备。'
        }
    ] as const;

    const fetchAccountInfo = async () => {
        setAccountLoading(true);
        try {
            const res = await gameApi.getAccountMe();
            const nextInfo = res?.data || null;
            setAccountInfo(nextInfo);
            if (nextInfo?.auth_mode === 'account') {
                const [sessionRes, auditRes, bindingPreviewRes] = await Promise.all([
                    gameApi.getAccountSessions(),
                    gameApi.getUserAudit(12),
                    gameApi.getVisitorBindingPreview()
                ]);
                setSessions(sessionRes?.data?.sessions || []);
                setAuditRows(auditRes?.data || []);
                setBindingPreview(bindingPreviewRes?.data || null);
            } else {
                setSessions([]);
                setAuditRows([]);
                setBindingPreview(null);
            }
        } catch (err) {
            console.error('Failed to fetch account info:', err);
        } finally {
            setAccountLoading(false);
        }
    };

    useEffect(() => {
        fetchAccountInfo();
    }, []);

    const handleAccountRegister = async () => {
        if (!accountForm.username.trim() || !accountForm.password.trim()) {
            showMessage('请输入用户名和密码。');
            return;
        }
        setAccountActionLoading('register');
        try {
            const registerRes = await gameApi.registerAccount({
                username: accountForm.username.trim(),
                password: accountForm.password,
                bind_current_visitor: accountForm.bindCurrentVisitor
            });
            const loginRes = await gameApi.loginAccount({
                username: accountForm.username.trim(),
                password: accountForm.password
            });
            const token = loginRes?.data?.token;
            if (token) {
                localStorage.setItem('account_token', token);
            }
            await fetchAccountInfo();
            const boundVisitorId = registerRes?.data?.bound_visitor_id;
            showMessage(
                boundVisitorId
                    ? '账户创建成功，已自动登录，并已绑定当前访客数据。'
                    : '账户创建成功，已自动登录。'
            );
            setAccountForm((prev) => ({ ...prev, password: '' }));
        } catch (error: any) {
            const detail = error?.response?.data?.detail || '注册失败，请重试。';
            showMessage(detail);
        } finally {
            setAccountActionLoading('');
        }
    };

    const handleAccountLogin = async () => {
        if (!accountForm.username.trim() || !accountForm.password.trim()) {
            showMessage('请输入用户名和密码。');
            return;
        }
        setAccountActionLoading('login');
        try {
            const res = await gameApi.loginAccount({
                username: accountForm.username.trim(),
                password: accountForm.password
            });
            const token = res?.data?.token;
            if (token) {
                localStorage.setItem('account_token', token);
            }
            await fetchAccountInfo();
            showMessage('登录成功。');
            setAccountForm((prev) => ({ ...prev, password: '' }));
        } catch (error: any) {
            const detail = error?.response?.data?.detail || '登录失败，请重试。';
            showMessage(detail);
        } finally {
            setAccountActionLoading('');
        }
    };

    const handleAccountLogout = async () => {
        setAccountActionLoading('logout');
        try {
            await gameApi.logoutAccount();
        } catch (error) {
            console.warn('Logout request failed, clearing local token anyway.', error);
        } finally {
            localStorage.removeItem('account_token');
            await fetchAccountInfo();
            setAccountActionLoading('');
            showMessage('已退出登录，当前回到访客模式。');
        }
    };

    const handleChangePassword = async () => {
        if (!passwordForm.currentPassword || !passwordForm.newPassword || !passwordForm.confirmPassword) {
            showMessage('请完整填写密码表单。');
            return;
        }
        if (passwordForm.newPassword !== passwordForm.confirmPassword) {
            showMessage('两次输入的新密码不一致。');
            return;
        }
        setAccountActionLoading('password');
        try {
            await gameApi.changeAccountPassword({
                current_password: passwordForm.currentPassword,
                new_password: passwordForm.newPassword
            });
            setPasswordForm({
                currentPassword: '',
                newPassword: '',
                confirmPassword: ''
            });
            await fetchAccountInfo();
            showMessage('密码修改成功。');
        } catch (error: any) {
            const detail = error?.response?.data?.detail || '修改密码失败，请重试。';
            showMessage(detail);
        } finally {
            setAccountActionLoading('');
        }
    };

    const handleBindCurrentVisitor = async () => {
        setAccountActionLoading('bind');
        try {
            const res = await gameApi.bindCurrentVisitorToAccount({ conflict_strategy: bindStrategy });
            await fetchAccountInfo();
            const alreadyLinked = !!res?.data?.already_linked;
            const migrated = !!res?.data?.migrated;
            const report = res?.data?.migration_report || {};
            const moved = Number(report?.moved_files || 0);
            const overwritten = Number(report?.overwritten_files || 0);
            const skipped = Number(report?.skipped_conflicts || 0);
            if (alreadyLinked) {
                showMessage('当前访客身份已经绑定过这个账户。');
            } else if (migrated) {
                showMessage(`迁移完成：新增 ${moved}，覆盖 ${overwritten}，冲突跳过 ${skipped}。`);
            } else {
                showMessage('已记录当前访客身份，但没有检测到新的可迁移数据。');
            }
        } catch (error: any) {
            const detail = error?.response?.data?.detail || '绑定访客数据失败，请重试。';
            showMessage(detail);
        } finally {
            setAccountActionLoading('');
        }
    };

    const handleLogoutOthers = async () => {
        setAccountActionLoading('sessions');
        try {
            const res = await gameApi.logoutOtherAccountSessions();
            await fetchAccountInfo();
            const count = Number(res?.data?.count || 0);
            showMessage(count > 0 ? `已退出其他 ${count} 个登录会话。` : '当前没有其他需要退出的会话。');
        } catch (error: any) {
            const detail = error?.response?.data?.detail || '退出其他设备失败，请重试。';
            showMessage(detail);
        } finally {
            setAccountActionLoading('');
        }
    };

    const handleRevokeSession = async (sessionId: string) => {
        setAccountActionLoading('sessions');
        try {
            await gameApi.revokeAccountSession(sessionId);
            await fetchAccountInfo();
            showMessage('已移除该登录会话。');
        } catch (error: any) {
            const detail = error?.response?.data?.detail || '移除会话失败，请重试。';
            showMessage(detail);
        } finally {
            setAccountActionLoading('');
        }
    };

    return (
        <div className="flex-1 flex flex-col h-full relative p-8">
            <div className="flex items-center justify-between mb-8 border-b border-[var(--color-cyan-main)]/15 pb-4">
                <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 rounded-xl bg-[var(--color-cyan-main)] text-white flex items-center justify-center shadow-lg shadow-cyan-main/30">
                        <UserRound size={28} />
                    </div>
                    <div>
                        <h2 className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-tight">账户中心</h2>
                        <p className="text-sm font-bold text-[var(--color-cyan-dark)]/55">管理登录状态与数据绑定。</p>
                    </div>
                </div>
                {message && (
                    <div className={`px-4 py-2 rounded-lg font-bold text-sm ${message.includes('失败') ? 'bg-red-100 text-red-600' : 'bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)]'}`}>
                        {message}
                    </div>
                )}
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar pr-4 space-y-8">
                <div className="bg-white/72 p-6 rounded-[2rem] border border-[var(--color-cyan-main)]/10 shadow-sm">
                    <div className="flex items-center space-x-3 mb-6">
                        <div className="p-2 bg-[var(--color-cyan-light)] rounded-xl text-[var(--color-cyan-main)]">
                            <UserRound size={20} />
                        </div>
                        <div>
                            <h3 className="text-lg font-black text-[var(--color-cyan-dark)]">账户状态</h3>
                            <p className="text-xs font-bold text-[var(--color-cyan-dark)]/40">
                                {accountInfo?.auth_mode === 'account' ? '当前已绑定正式账户' : '当前为访客模式'}
                            </p>
                        </div>
                    </div>

                    {accountLoading ? (
                        <div className="flex items-center gap-3 text-sm font-bold text-[var(--color-cyan-dark)]/60">
                            <RefreshCcw className="animate-spin" size={16} />
                            正在读取账户状态...
                        </div>
                    ) : accountInfo?.auth_mode === 'account' && accountInfo?.account ? (
                        <div className="space-y-6">
                            <div className="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-5">
                                <div className="text-xs font-black text-emerald-600">已登录</div>
                                <div className="mt-2 text-xl font-black text-[var(--color-cyan-dark)]">
                                    {accountInfo.account.username}
                                </div>
                                <div className="mt-2 text-sm font-bold text-[var(--color-cyan-dark)]/60">
                                    账户 ID：{accountInfo.account.account_id}
                                </div>
                                <div className="mt-1 text-sm font-bold text-[var(--color-cyan-dark)]/50">
                                    已绑定访客记录：{(accountInfo.account.linked_visitor_ids || []).length} 个
                                </div>
                            </div>

                            <div className="rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white p-5">
                                <div className="text-sm font-black text-[var(--color-cyan-main)]">当前权限</div>
                                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {capabilityEntries.map((item) => {
                                        const enabled = !!accountInfo?.capabilities?.[item.key];
                                        return (
                                            <div
                                                key={item.key}
                                                className={`rounded-2xl border p-4 ${enabled ? 'border-emerald-200 bg-emerald-50/60' : 'border-amber-200 bg-amber-50/60'}`}
                                            >
                                                <div className="flex items-center justify-between gap-3">
                                                    <div className="text-sm font-black text-[var(--color-cyan-dark)]">{item.label}</div>
                                                    <div className={`rounded-full px-2.5 py-1 text-xs font-black ${enabled ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-700'}`}>
                                                        {enabled ? '可用' : '需登录'}
                                                    </div>
                                                </div>
                                                <div className="mt-2 text-xs font-bold text-[var(--color-cyan-dark)]/55 leading-relaxed">
                                                    {item.description}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="rounded-2xl border-2 border-[var(--color-cyan-main)]/10 bg-white p-5">
                                <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">安全设置</div>
                                <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <input
                                        type="password"
                                        value={passwordForm.currentPassword}
                                        onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                                        className="w-full bg-[var(--color-cyan-light)]/30 text-[var(--color-cyan-dark)] font-bold p-3.5 rounded-xl border-2 border-transparent focus:border-[var(--color-cyan-main)]/30 focus:bg-white outline-none transition-all"
                                        placeholder="当前密码"
                                    />
                                    <input
                                        type="password"
                                        value={passwordForm.newPassword}
                                        onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                                        className="w-full bg-[var(--color-cyan-light)]/30 text-[var(--color-cyan-dark)] font-bold p-3.5 rounded-xl border-2 border-transparent focus:border-[var(--color-cyan-main)]/30 focus:bg-white outline-none transition-all"
                                        placeholder="新密码"
                                    />
                                    <input
                                        type="password"
                                        value={passwordForm.confirmPassword}
                                        onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                                        className="w-full bg-[var(--color-cyan-light)]/30 text-[var(--color-cyan-dark)] font-bold p-3.5 rounded-xl border-2 border-transparent focus:border-[var(--color-cyan-main)]/30 focus:bg-white outline-none transition-all"
                                        placeholder="确认新密码"
                                    />
                                </div>
                                <div className="mt-4 flex flex-wrap gap-3">
                                    <button
                                        onClick={handleChangePassword}
                                        disabled={accountActionLoading !== '' && accountActionLoading !== 'password'}
                                        className="inline-flex items-center gap-2 rounded-2xl bg-[var(--color-cyan-main)] px-5 py-3 text-xs font-black uppercase tracking-widest text-white transition-all hover:bg-[var(--color-cyan-dark)] disabled:opacity-50"
                                    >
                                        {accountActionLoading === 'password' ? <RefreshCcw className="animate-spin" size={14} /> : <LogIn size={14} />}
                                        修改密码
                                    </button>
                                    <button
                                        onClick={handleBindCurrentVisitor}
                                        disabled={accountActionLoading !== '' && accountActionLoading !== 'bind'}
                                        className="inline-flex items-center gap-2 rounded-2xl border-2 border-[var(--color-cyan-main)]/20 bg-white px-5 py-3 text-xs font-black uppercase tracking-widest text-[var(--color-cyan-main)] transition-all hover:bg-[var(--color-cyan-light)] disabled:opacity-50"
                                    >
                                        {accountActionLoading === 'bind' ? <RefreshCcw className="animate-spin" size={14} /> : <UserPlus size={14} />}
                                        绑定当前访客数据
                                    </button>
                                    <button
                                        onClick={handleAccountLogout}
                                        disabled={accountActionLoading === 'logout'}
                                        className="inline-flex items-center gap-2 rounded-2xl bg-red-500 px-5 py-3 text-xs font-black uppercase tracking-widest text-white transition-all hover:bg-red-600 disabled:opacity-50"
                                    >
                                        {accountActionLoading === 'logout' ? <RefreshCcw className="animate-spin" size={14} /> : <LogOut size={14} />}
                                        退出登录
                                    </button>
                                </div>
                            </div>

                            <div className="rounded-2xl border-2 border-[var(--color-cyan-main)]/10 bg-white p-5">
                                <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">访客绑定预览</div>
                                <div className="mt-2 text-xs font-bold text-[var(--color-cyan-dark)]/55">
                                    在正式绑定前，先看看当前访客身份里大概有哪些内容，以及是否可能与账户现有文件重名。
                                </div>
                                <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <div className="rounded-2xl bg-[var(--color-cyan-light)]/20 p-4">
                                        <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">当前访客</div>
                                        <div className="mt-2 text-sm font-black text-[var(--color-cyan-dark)]">
                                            {bindingPreview?.visitor_id || '无可绑定访客'}
                                        </div>
                                        <div className="mt-2 text-xs font-bold text-[var(--color-cyan-dark)]/55">
                                            文件总数：{bindingPreview?.visitor_summary?.total_files || 0}
                                        </div>
                                        <div className="mt-1 text-xs font-bold text-[var(--color-cyan-dark)]/55">
                                            模组：{bindingPreview?.visitor_summary?.library_items || 0}，存档：{bindingPreview?.visitor_summary?.save_files || 0}
                                        </div>
                                    </div>
                                    <div className="rounded-2xl bg-[var(--color-cyan-light)]/20 p-4">
                                        <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">账户现有内容</div>
                                        <div className="mt-2 text-sm font-black text-[var(--color-cyan-dark)]">
                                            {accountInfo.account.username}
                                        </div>
                                        <div className="mt-2 text-xs font-bold text-[var(--color-cyan-dark)]/55">
                                            文件总数：{bindingPreview?.account_summary?.total_files || 0}
                                        </div>
                                        <div className="mt-1 text-xs font-bold text-[var(--color-cyan-dark)]/55">
                                            模组：{bindingPreview?.account_summary?.library_items || 0}，存档：{bindingPreview?.account_summary?.save_files || 0}
                                        </div>
                                    </div>
                                    <div className="rounded-2xl bg-amber-50/70 p-4 border border-amber-100">
                                        <div className="text-[10px] font-black uppercase tracking-widest text-amber-600">冲突提示</div>
                                        <div className="mt-2 text-sm font-black text-[var(--color-cyan-dark)]">
                                            {bindingPreview?.conflicts?.count || 0} 个潜在重名文件
                                        </div>
                                        <div className="mt-2 text-xs font-bold text-[var(--color-cyan-dark)]/55 leading-relaxed">
                                            {bindingPreview?.already_linked
                                                ? '这个访客身份已经绑定过当前账户。'
                                                : bindingPreview?.conflicts?.count
                                                    ? '迁移时若遇到同名文件，会优先保留账户里已存在的那份。'
                                                    : '当前看起来没有明显的重名冲突。'}
                                        </div>
                                    </div>
                                </div>
                                {!!bindingPreview?.conflicts?.examples?.length && (
                                    <div className="mt-4 rounded-2xl border border-amber-100 bg-amber-50/50 px-4 py-3 text-xs font-bold text-[var(--color-cyan-dark)]/65">
                                        例子：{bindingPreview.conflicts.examples.join('、')}
                                    </div>
                                )}
                                <div className="mt-4 flex flex-wrap items-center gap-3">
                                    <span className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">冲突处理策略</span>
                                    <button
                                        onClick={() => setBindStrategy('keep_account')}
                                        className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${bindStrategy === 'keep_account' ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]' : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/15'}`}
                                    >
                                        保留账户已有内容
                                    </button>
                                    <button
                                        onClick={() => setBindStrategy('overwrite_with_visitor')}
                                        className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${bindStrategy === 'overwrite_with_visitor' ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-amber-700 border-amber-200'}`}
                                    >
                                        用访客内容覆盖冲突
                                    </button>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                                <div className="rounded-2xl border-2 border-[var(--color-cyan-main)]/10 bg-white p-5">
                                    <div className="flex items-center justify-between gap-3">
                                        <div className="flex items-center gap-2">
                                            <div className="rounded-xl bg-[var(--color-cyan-light)] p-2 text-[var(--color-cyan-main)]">
                                                <Laptop size={16} />
                                            </div>
                                            <div>
                                                <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">会话管理</div>
                                                <div className="text-xs font-bold text-[var(--color-cyan-dark)]/50">查看当前登录状态，并可退出其他设备</div>
                                            </div>
                                        </div>
                                        <button
                                            onClick={handleLogoutOthers}
                                            disabled={accountActionLoading !== '' && accountActionLoading !== 'sessions'}
                                            className="inline-flex items-center gap-2 rounded-2xl border-2 border-[var(--color-cyan-main)]/20 bg-white px-4 py-2 text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] transition-all hover:bg-[var(--color-cyan-light)] disabled:opacity-50"
                                        >
                                            {accountActionLoading === 'sessions' ? <RefreshCcw className="animate-spin" size={12} /> : <Shield size={12} />}
                                            退出其他设备
                                        </button>
                                    </div>
                                    <div className="mt-4 space-y-3">
                                        {sessions.length > 0 ? sessions.map((session) => (
                                            <div
                                                key={session.session_id}
                                                className={`rounded-2xl border p-4 ${session.is_current ? 'border-emerald-200 bg-emerald-50/60' : 'border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/15'}`}
                                            >
                                                <div className="flex items-start justify-between gap-3">
                                                    <div>
                                                        <div className="text-sm font-black text-[var(--color-cyan-dark)]">
                                                            {session.is_current ? '当前设备' : `登录会话 ${session.session_id}`}
                                                        </div>
                                                        <div className="mt-1 text-xs font-bold text-[var(--color-cyan-dark)]/50">
                                                            创建于 {session.created_at || '未知时间'}
                                                        </div>
                                                        <div className="mt-1 text-xs font-bold text-[var(--color-cyan-dark)]/50">
                                                            将在 {session.expires_at || '未知时间'} 过期
                                                        </div>
                                                    </div>
                                                    {!session.is_current && (
                                                        <button
                                                            onClick={() => handleRevokeSession(session.session_id)}
                                                            disabled={accountActionLoading === 'sessions'}
                                                            className="rounded-xl border border-red-200 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-red-500 transition-all hover:bg-red-50 disabled:opacity-50"
                                                        >
                                                            移除
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        )) : (
                                            <div className="rounded-2xl border border-dashed border-[var(--color-cyan-main)]/20 bg-[var(--color-cyan-light)]/10 px-4 py-5 text-sm font-bold text-[var(--color-cyan-dark)]/50">
                                                当前只有这个登录会话。
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="rounded-2xl border-2 border-[var(--color-cyan-main)]/10 bg-white p-5">
                                    <div className="flex items-center gap-2">
                                        <div className="rounded-xl bg-[var(--color-cyan-light)] p-2 text-[var(--color-cyan-main)]">
                                            <History size={16} />
                                        </div>
                                        <div>
                                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">最近活动</div>
                                            <div className="text-xs font-bold text-[var(--color-cyan-dark)]/50">最近账户与内容相关操作记录</div>
                                        </div>
                                    </div>
                                    <div className="mt-4 space-y-3">
                                        {auditRows.length > 0 ? auditRows.map((row, index) => (
                                            <div key={`${row.ts || 'row'}-${index}`} className="rounded-2xl border border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/10 p-4">
                                                <div className="flex items-center justify-between gap-3">
                                                    <div className="text-sm font-black text-[var(--color-cyan-dark)]">{row.action || 'unknown_action'}</div>
                                                    <div className={`rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-widest ${row.status === 'ok' ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-500'}`}>
                                                        {row.status || 'unknown'}
                                                    </div>
                                                </div>
                                                <div className="mt-2 text-xs font-bold text-[var(--color-cyan-dark)]/55">
                                                    {row.detail || '无附加说明'}
                                                </div>
                                                <div className="mt-1 text-[11px] font-bold text-[var(--color-cyan-dark)]/40">
                                                    {row.ts || '未知时间'}
                                                </div>
                                            </div>
                                        )) : (
                                            <div className="rounded-2xl border border-dashed border-[var(--color-cyan-main)]/20 bg-[var(--color-cyan-light)]/10 px-4 py-5 text-sm font-bold text-[var(--color-cyan-dark)]/50">
                                                暂无最近活动记录。
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            <div className="rounded-2xl border border-amber-100 bg-amber-50/70 p-5 text-sm font-bold text-[var(--color-cyan-dark)]/70 leading-relaxed">
                                当前仍在使用访客模式。建议注册正式账户来稳定绑定存档、模组和工坊作品。
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-black text-[var(--color-cyan-dark)]/40 mb-2 ml-1">用户名</label>
                                    <input
                                        type="text"
                                        value={accountForm.username}
                                        onChange={(e) => setAccountForm({ ...accountForm, username: e.target.value })}
                                        className="w-full bg-[var(--color-cyan-light)]/30 text-[var(--color-cyan-dark)] font-bold p-3.5 rounded-xl border-2 border-transparent focus:border-[var(--color-cyan-main)]/30 focus:bg-white outline-none transition-all"
                                        placeholder="3-32 位字母、数字或下划线"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-black text-[var(--color-cyan-dark)]/40 mb-2 ml-1">密码</label>
                                    <input
                                        type="password"
                                        value={accountForm.password}
                                        onChange={(e) => setAccountForm({ ...accountForm, password: e.target.value })}
                                        className="w-full bg-[var(--color-cyan-light)]/30 text-[var(--color-cyan-dark)] font-bold p-3.5 rounded-xl border-2 border-transparent focus:border-[var(--color-cyan-main)]/30 focus:bg-white outline-none transition-all"
                                        placeholder="至少 6 位"
                                    />
                                </div>
                            </div>

                            <label className="flex items-center gap-3 rounded-2xl bg-[var(--color-cyan-light)]/30 px-4 py-3 text-sm font-bold text-[var(--color-cyan-dark)]">
                                <input
                                    type="checkbox"
                                    checked={accountForm.bindCurrentVisitor}
                                    onChange={(e) => setAccountForm({ ...accountForm, bindCurrentVisitor: e.target.checked })}
                                    className="h-4 w-4 accent-[var(--color-cyan-main)]"
                                />
                                注册时绑定当前访客数据
                            </label>

                            <div className="flex flex-wrap gap-3">
                                <button
                                    onClick={handleAccountRegister}
                                    disabled={accountActionLoading !== ''}
                                    className="inline-flex items-center gap-2 rounded-2xl bg-[var(--color-cyan-main)] px-5 py-3 text-sm font-black text-white transition-all hover:bg-[var(--color-cyan-dark)] disabled:opacity-50"
                                >
                                    {accountActionLoading === 'register' ? <RefreshCcw className="animate-spin" size={14} /> : <UserPlus size={14} />}
                                    注册并登录
                                </button>
                                <button
                                    onClick={handleAccountLogin}
                                    disabled={accountActionLoading !== ''}
                                    className="inline-flex items-center gap-2 rounded-2xl border border-[var(--color-cyan-main)]/20 bg-white px-5 py-3 text-sm font-black text-[var(--color-cyan-main)] transition-all hover:bg-[var(--color-cyan-light)] disabled:opacity-50"
                                >
                                    {accountActionLoading === 'login' ? <RefreshCcw className="animate-spin" size={14} /> : <LogIn size={14} />}
                                    登录已有账户
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
