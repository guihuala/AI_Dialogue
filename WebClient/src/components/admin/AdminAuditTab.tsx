interface AdminAuditTabProps {
    auditRows: any[];
}

export const AdminAuditTab = ({ auditRows }: AdminAuditTabProps) => {
    return (
        <div className="p-6">
            <div className="mb-4">
                <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.2em]">
                    最近审计日志
                </h3>
                <p className="mt-2 text-xs font-bold text-slate-400">
                    这里集中查看近期后台动作、状态结果和时间戳，方便快速排查问题。
                </p>
            </div>
            <div className="overflow-hidden rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white">
                {auditRows.length === 0 ? (
                    <div className="px-4 py-8 text-sm text-slate-400 font-bold">暂无日志</div>
                ) : (
                    auditRows.map((r, idx) => (
                        <div key={idx} className="px-4 py-3 text-sm font-bold text-slate-600 border-b last:border-b-0 border-[var(--color-cyan-main)]/5 flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                            <div>
                                <span className={`mr-2 ${r.status === 'ok' ? 'text-emerald-600' : 'text-red-500'}`}>[{r.status}]</span>
                                <span>{r.action}</span>
                            </div>
                            <span className="text-xs text-slate-400">{r.ts}</span>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

