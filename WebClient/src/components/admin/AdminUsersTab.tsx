interface AdminUsersTabProps {
    adminUserQuery: string;
    setAdminUserQuery: (v: string) => void;
    adminUsers: any[];
    adminUserStats: any;
    adminUserPagination: any;
    setAdminUserPage: (setter: (prev: number) => number) => void;
    onRefresh: () => void;
}

export const AdminUsersTab = ({
    adminUserQuery,
    setAdminUserQuery,
    adminUsers,
    adminUserStats,
    adminUserPagination,
    setAdminUserPage,
    onRefresh,
}: AdminUsersTabProps) => {
    return (
        <div className="p-6">
            <div className="mb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div>
                    <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.2em]">
                        账户用户检索
                    </h3>
                    <p className="mt-2 text-xs font-bold text-slate-400">
                        支持按用户名/账户 ID 搜索，查看账户规模和活跃会话统计。
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <input
                        type="text"
                        value={adminUserQuery}
                        onChange={(e) => setAdminUserQuery(e.target.value)}
                        placeholder="搜索用户名或账户 ID"
                        className="px-4 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 bg-white text-sm font-bold text-[var(--color-cyan-dark)] outline-none focus:border-[var(--color-cyan-main)]"
                    />
                    <button
                        onClick={onRefresh}
                        className="px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 bg-white text-[var(--color-cyan-main)] text-xs font-black hover:bg-[var(--color-cyan-light)]"
                    >
                        刷新
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-4">
                <div className="rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white p-3">
                    <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">账户总数</div>
                    <div className="mt-1 text-lg font-black text-[var(--color-cyan-dark)]">{adminUserStats?.total_accounts ?? 0}</div>
                </div>
                <div className="rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white p-3">
                    <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">活跃会话</div>
                    <div className="mt-1 text-lg font-black text-[var(--color-cyan-dark)]">{adminUserStats?.active_sessions ?? 0}</div>
                </div>
                <div className="rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white p-3">
                    <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">绑定访客数</div>
                    <div className="mt-1 text-lg font-black text-[var(--color-cyan-dark)]">{adminUserStats?.total_linked_visitors ?? 0}</div>
                </div>
                <div className="rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white p-3">
                    <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">公开模组</div>
                    <div className="mt-1 text-lg font-black text-[var(--color-cyan-dark)]">{adminUserStats?.public_mods ?? 0}</div>
                </div>
                <div className="rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white p-3">
                    <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]">工坊作者数</div>
                    <div className="mt-1 text-lg font-black text-[var(--color-cyan-dark)]">{adminUserStats?.workshop_owner_accounts ?? 0}</div>
                </div>
            </div>

            <div className="overflow-hidden rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="text-[10px] font-black text-[var(--color-cyan-main)]/50 uppercase tracking-widest border-b border-[var(--color-cyan-main)]/5">
                            <th className="px-4 py-3">账户 ID</th>
                            <th className="px-4 py-3">用户名</th>
                            <th className="px-4 py-3">绑定访客</th>
                            <th className="px-4 py-3">创建时间</th>
                            <th className="px-4 py-3">最近更新</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-cyan-main)]/5">
                        {adminUsers.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="py-12 text-center text-slate-400 font-bold">暂无用户数据</td>
                            </tr>
                        ) : adminUsers.map((u) => (
                            <tr key={u.account_id} className="hover:bg-[var(--color-cyan-main)]/5 transition-colors">
                                <td className="px-4 py-3 font-mono text-xs text-slate-500">{u.account_id}</td>
                                <td className="px-4 py-3 text-sm font-black text-[var(--color-cyan-dark)]">{u.username}</td>
                                <td className="px-4 py-3 text-sm font-bold text-slate-600">{u.linked_visitor_count}</td>
                                <td className="px-4 py-3 text-xs font-bold text-slate-500">{u.created_at || '-'}</td>
                                <td className="px-4 py-3 text-xs font-bold text-slate-500">{u.updated_at || '-'}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {adminUserPagination && (
                <div className="mt-4 flex items-center justify-between text-xs font-bold text-slate-500">
                    <div>
                        第 {adminUserPagination.page} / {adminUserPagination.total_pages} 页，共 {adminUserPagination.total} 条
                    </div>
                    <div className="flex gap-2">
                        <button
                            disabled={!adminUserPagination.has_prev}
                            onClick={() => setAdminUserPage((p) => Math.max(1, p - 1))}
                            className="px-3 py-2 rounded-lg border border-[var(--color-cyan-main)]/20 disabled:opacity-40"
                        >
                            上一页
                        </button>
                        <button
                            disabled={!adminUserPagination.has_next}
                            onClick={() => setAdminUserPage((p) => p + 1)}
                            className="px-3 py-2 rounded-lg border border-[var(--color-cyan-main)]/20 disabled:opacity-40"
                        >
                            下一页
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

