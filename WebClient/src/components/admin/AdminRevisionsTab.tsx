import { useMemo, useState } from 'react';

interface AdminRevisionsTabProps {
  revisions: any[];
  loading?: boolean;
  onRefresh: () => void;
  onApprove: (proposalId: string) => Promise<void>;
  onReject: (proposalId: string) => Promise<void>;
  onApplyMemory: (proposalId: string) => Promise<void>;
  onApplyDraft: (proposalId: string) => Promise<void>;
  onForceApplyDraft: (proposalId: string, reason: string) => Promise<void>;
  onRollback: (proposalId: string) => Promise<void>;
}

export const AdminRevisionsTab = ({
  revisions,
  loading = false,
  onRefresh,
  onApprove,
  onReject,
  onApplyMemory,
  onApplyDraft,
  onForceApplyDraft,
  onRollback,
}: AdminRevisionsTabProps) => {
  const [statusFilter, setStatusFilter] = useState<'queue' | 'applied' | 'rejected'>('queue');
  const [groupMode, setGroupMode] = useState<'topic' | 'flat'>('topic');
  const [batchingGroupKey, setBatchingGroupKey] = useState<string>('');
  const rows = useMemo(() => {
    return (revisions || []).filter((x) => String(x?.status || '') === statusFilter);
  }, [revisions, statusFilter]);
  const groupedRows = useMemo(() => {
    const normalizeSummary = (raw: string) => {
      const cleaned = String(raw || '').replace(/\s+/g, ' ').trim();
      return cleaned ? cleaned.slice(0, 14) : '未命名提案';
    };
    const bucket = new Map<string, { key: string; modId: string; topic: string; items: any[] }>();
    (rows || []).forEach((row) => {
      const modId = String(row?.target_mod_id || '-');
      const topic = normalizeSummary(String(row?.summary || ''));
      const key = `${modId}::${topic}`;
      const existing = bucket.get(key);
      if (existing) {
        existing.items.push(row);
      } else {
        bucket.set(key, { key, modId, topic, items: [row] });
      }
    });
    return Array.from(bucket.values()).sort((a, b) => {
      const aTime = String(a.items?.[0]?.created_at || '');
      const bTime = String(b.items?.[0]?.created_at || '');
      return bTime.localeCompare(aTime);
    });
  }, [rows]);

  const getGroupRecommendation = (items: any[]) => {
    const list = Array.isArray(items) ? items : [];
    if (!list.length) {
      return { level: 'neutral', text: '建议人工复核' };
    }
    const total = list.length;
    const duplicateCount = list.filter((x) => Boolean(x?.validator?.duplicate_proposal)).length;
    const lowQualityCount = list.filter((x) => Number(x?.quality_score || 0) < 50).length;
    const avgQuality = list.reduce((acc, x) => acc + Number(x?.quality_score || 0), 0) / total;
    const duplicateRatio = duplicateCount / total;
    const lowRatio = lowQualityCount / total;

    if (duplicateRatio >= 0.6 || (duplicateRatio >= 0.4 && lowRatio >= 0.5)) {
      return { level: 'reject', text: '建议整组驳回（重复/低质量占比高）' };
    }
    if (avgQuality >= 75 && duplicateRatio <= 0.2 && lowRatio <= 0.2) {
      return { level: 'approve', text: '建议优先通过（质量较高且重复低）' };
    }
    return { level: 'neutral', text: '建议人工复核（质量分布混合）' };
  };

  const renderRow = (row: any) => {
    const q = Number(row?.quality_score || 0);
    const samples = Number(row?.validator?.run_sample_count || 0);
    const blocked = Array.isArray(row?.validator?.blocked_rules) && row.validator.blocked_rules.includes('insufficient_run_samples');
    const duplicated = Boolean(row?.validator?.duplicate_proposal);
    const duplicateWith = String(row?.validator?.duplicate_with || '');
    const mergeSuggestion = Boolean(row?.validator?.merge_suggestion);
    const mergeWith = String(row?.validator?.merge_with || '');
    const canApplyDraft = q >= 50 && samples >= 2 && !blocked;
    return (
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-black text-[var(--color-cyan-dark)] break-all">{row.summary || row.proposal_id}</div>
          <div className="mt-1 text-xs text-slate-500">
            {row.proposal_id} · mod {row.target_mod_id || '-'} · risk {row.risk_level || 'medium'}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            changes {row.changes_count || 0} · memory {row.memory_candidates_count || 0}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            quality {Number(row.quality_score || 0)} · priority {String(row.priority || 'medium')}
            {typeof row?.validator?.structured_ratio === 'number' && (
              <span> · structured {(Number(row.validator.structured_ratio) * 100).toFixed(0)}%</span>
            )}
            {typeof row?.validator?.run_sample_count === 'number' && (
              <span> · samples {Number(row.validator.run_sample_count || 0)}</span>
            )}
          </div>
          {Array.isArray(row?.validator?.blocked_rules) && row.validator.blocked_rules.length > 0 && (
            <div className="mt-1 text-[11px] font-bold text-amber-700">
              规则提示：{row.validator.blocked_rules.join(', ')}
            </div>
          )}
          {duplicated && (
            <div className="mt-1 text-[11px] font-bold text-rose-700">
              重复提案：与 {duplicateWith || '最近提案'} 指纹一致，建议驳回或合并。
            </div>
          )}
          {!duplicated && mergeSuggestion && (
            <div className="mt-1 text-[11px] font-bold text-indigo-700">
              合并建议：与 {mergeWith || '近期提案'} 文件重叠较高，可先合并再审。
            </div>
          )}
          {!canApplyDraft && statusFilter === 'applied' && (
            <div className="mt-1 text-[11px] font-bold text-rose-700">
              门禁拦截：质量或样本不足（需要备注 force_apply 才可强制应用）
            </div>
          )}
          {Array.isArray(row?.validator?.common_issues) && row.validator.common_issues.length > 0 && (
            <div className="mt-1 text-[11px] text-slate-500">
              共性问题：{row.validator.common_issues.slice(0, 3).join(', ')}
            </div>
          )}
        </div>
        <div className="shrink-0 flex items-center gap-2">
          {statusFilter === 'queue' && (
            <>
              <button
                onClick={() => onApprove(String(row.proposal_id))}
                className="px-2.5 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-black"
              >
                通过
              </button>
              <button
                onClick={() => onReject(String(row.proposal_id))}
                className="px-2.5 py-1.5 rounded-lg bg-rose-50 text-rose-700 border border-rose-200 text-xs font-black"
              >
                驳回
              </button>
            </>
          )}
          {statusFilter === 'applied' && (
            <>
              <button
                onClick={() => onApplyDraft(String(row.proposal_id))}
                disabled={!canApplyDraft}
                className="px-2.5 py-1.5 rounded-lg bg-cyan-50 text-cyan-700 border border-cyan-200 text-xs font-black"
              >
                应用到草稿
              </button>
              {!canApplyDraft && (
                <button
                  onClick={() => {
                    const reason = window.prompt('请输入强制应用原因（会写入审计）', '质量门禁人工放行');
                    if (reason === null) return;
                    onForceApplyDraft(String(row.proposal_id), String(reason || '').trim() || 'manual_force_apply');
                  }}
                  className="px-2.5 py-1.5 rounded-lg bg-rose-50 text-rose-700 border border-rose-200 text-xs font-black"
                  title="质量门禁拦截时强制应用（会写审计）"
                >
                  强制应用
                </button>
              )}
              <button
                onClick={() => onApplyMemory(String(row.proposal_id))}
                className="px-2.5 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200 text-xs font-black"
              >
                入长期记忆
              </button>
              <button
                onClick={() => onRollback(String(row.proposal_id))}
                className="px-2.5 py-1.5 rounded-lg bg-amber-50 text-amber-700 border border-amber-200 text-xs font-black"
              >
                回滚
              </button>
            </>
          )}
        </div>
      </div>
    );
  };

  const runGroupAction = async (groupKey: string, items: any[], action: 'approve' | 'reject') => {
    const ids = (items || []).map((x) => String(x?.proposal_id || '')).filter(Boolean);
    if (!ids.length) return;
    const preview = ids.slice(0, 8);
    const remain = Math.max(0, ids.length - preview.length);
    const actionText = action === 'approve' ? '整组通过' : '整组驳回';
    const lines = [
      `即将执行：${actionText}`,
      `共 ${ids.length} 条提案`,
      '',
      '预览 proposal_id：',
      ...preview,
      ...(remain > 0 ? [`... 以及另外 ${remain} 条`] : []),
      '',
      '确认继续？',
    ];
    if (!window.confirm(lines.join('\n'))) return;
    setBatchingGroupKey(groupKey);
    try {
      for (const id of ids) {
        if (action === 'approve') {
          await onApprove(id);
        } else {
          await onReject(id);
        }
      }
      onRefresh();
    } finally {
      setBatchingGroupKey('');
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white p-4 flex items-center justify-between">
        <div>
          <div className="text-xl font-black text-[var(--color-cyan-dark)]">修订提案队列</div>
          <div className="text-xs font-bold text-slate-500 mt-1">AI 自迭代提案只允许人工审计后应用</div>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 text-sm font-bold text-[var(--color-cyan-dark)]"
          >
            <option value="queue">待审</option>
            <option value="applied">已通过</option>
            <option value="rejected">已驳回</option>
          </select>
          <select
            value={groupMode}
            onChange={(e) => setGroupMode(e.target.value as any)}
            className="px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 text-sm font-bold text-[var(--color-cyan-dark)]"
          >
            <option value="topic">按主题聚合</option>
            <option value="flat">平铺列表</option>
          </select>
          <button
            onClick={onRefresh}
            className="px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 text-sm font-black text-[var(--color-cyan-main)] hover:bg-[var(--color-cyan-light)]/30"
          >
            刷新
          </button>
        </div>
      </div>

      <div className="rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white overflow-hidden">
        {loading ? (
          <div className="p-6 text-sm font-bold text-slate-500">加载中...</div>
        ) : rows.length === 0 ? (
          <div className="p-6 text-sm font-bold text-slate-500">当前筛选下暂无提案</div>
        ) : groupMode === 'flat' ? (
          <div className="divide-y divide-[var(--color-cyan-main)]/10">
            {rows.map((row) => (
              <div key={row.proposal_id} className="p-4">
                {renderRow(row)}
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 space-y-4">
            {groupedRows.map((group) => (
              <div key={group.key} className="rounded-xl border border-[var(--color-cyan-main)]/15 overflow-hidden">
                <div className="px-3 py-2 bg-[var(--color-cyan-light)]/20 border-b border-[var(--color-cyan-main)]/10 flex items-center justify-between">
                  <div className="min-w-0">
                    <div className="text-xs font-black text-[var(--color-cyan-dark)] truncate">
                      {group.modId} · {group.topic}
                    </div>
                    {(() => {
                      const rec = getGroupRecommendation(group.items);
                      const cls =
                        rec.level === 'reject'
                          ? 'text-rose-700'
                          : rec.level === 'approve'
                            ? 'text-emerald-700'
                            : 'text-slate-600';
                      return <div className={`text-[11px] font-bold mt-0.5 ${cls}`}>{rec.text}</div>;
                    })()}
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="text-[11px] font-bold text-slate-500">{group.items.length} 条提案</div>
                    {statusFilter === 'queue' && (
                      <>
                        <button
                          onClick={() => runGroupAction(group.key, group.items, 'approve')}
                          disabled={batchingGroupKey === group.key}
                          className="px-2 py-1 rounded-md border border-emerald-200 bg-emerald-50 text-emerald-700 text-[11px] font-black disabled:opacity-60"
                        >
                          整组通过
                        </button>
                        <button
                          onClick={() => runGroupAction(group.key, group.items, 'reject')}
                          disabled={batchingGroupKey === group.key}
                          className="px-2 py-1 rounded-md border border-rose-200 bg-rose-50 text-rose-700 text-[11px] font-black disabled:opacity-60"
                        >
                          整组驳回
                        </button>
                      </>
                    )}
                  </div>
                </div>
                <div className="divide-y divide-[var(--color-cyan-main)]/10">
                  {group.items.map((row) => (
                    <div key={row.proposal_id} className="p-4">
                      {renderRow(row)}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
