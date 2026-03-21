interface AdminStorageTabProps {
    userState: any;
    quota: any;
    cleaning: boolean;
    onCleanup: (dryRun: boolean) => void;
}

export const AdminStorageTab = ({ userState, quota, cleaning, onCleanup }: AdminStorageTabProps) => {
    return (
        <div className="p-6 grid grid-cols-1 xl:grid-cols-2 gap-6">
            <div className="rounded-3xl border border-[var(--color-cyan-main)]/10 bg-white p-6">
                <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.2em] mb-4">
                    当前用户状态
                </h3>
                <div className="space-y-4 text-sm font-bold text-[var(--color-cyan-dark)]">
                    <div className="rounded-2xl bg-[var(--color-cyan-light)]/20 px-4 py-4">
                        当前激活模组：{userState?.active_source || 'default'} / {userState?.active_mod_id || 'default'}
                    </div>
                    <div className="rounded-2xl bg-[var(--color-cyan-light)]/20 px-4 py-4">
                        最近安全快照：{userState?.last_good_snapshot_id || '-'}
                    </div>
                    <div className="rounded-2xl bg-[var(--color-cyan-light)]/20 px-4 py-4">
                        最近状态更新时间：{userState?.updated_at || '-'}
                    </div>
                </div>
            </div>

            <div className="rounded-3xl border border-[var(--color-cyan-main)]/10 bg-white p-6">
                <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.2em] mb-4">
                    存储配额与清理
                </h3>
                <div className="space-y-4">
                    <div className="rounded-2xl bg-[var(--color-cyan-light)]/20 px-4 py-4 text-sm font-bold text-[var(--color-cyan-dark)]">
                        本地模组：{quota?.usage?.library_items || 0} / {quota?.limits?.library_items || 0}
                    </div>
                    <div className="rounded-2xl bg-[var(--color-cyan-light)]/20 px-4 py-4 text-sm font-bold text-[var(--color-cyan-dark)]">
                        占用空间：{(quota?.usage?.library_bytes || 0) / (1024 * 1024) > 0 ? `${((quota?.usage?.library_bytes || 0) / (1024 * 1024)).toFixed(1)} MB` : '0 MB'}
                    </div>
                    {Array.isArray(quota?.warnings) && quota.warnings.length > 0 && (
                        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-xs font-black text-amber-700">
                            {quota.warnings.join('；')}
                        </div>
                    )}
                    <div className="flex gap-3 pt-2">
                        <button
                            onClick={() => onCleanup(true)}
                            disabled={cleaning}
                            className="px-4 py-3 bg-white border border-[var(--color-cyan-main)]/20 text-[var(--color-cyan-main)] rounded-2xl hover:bg-[var(--color-cyan-light)] transition-all disabled:opacity-50 text-xs font-black"
                        >
                            预览清理
                        </button>
                        <button
                            onClick={() => onCleanup(false)}
                            disabled={cleaning}
                            className="px-4 py-3 bg-amber-50 border border-amber-200 text-amber-700 rounded-2xl hover:bg-amber-100 transition-all disabled:opacity-50 text-xs font-black"
                        >
                            执行清理
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

