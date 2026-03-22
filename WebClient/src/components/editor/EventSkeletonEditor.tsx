import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Search, Filter, Wrench, ChevronDown } from 'lucide-react';

type SkeletonEvent = {
    id: string;
    type: 'daily' | 'key';
    title: string;
    priority: number;
    cooldown_days: number;
    once: boolean;
    triggers: Record<string, any>;
    options: Array<Record<string, any>>;
    meta?: Record<string, any>;
};

interface EventSkeletonEditorProps {
    payload: { version?: number; generated_at?: string; events: SkeletonEvent[] } | null;
    onSavePayload: (nextPayload: { version?: number; generated_at?: string; events: SkeletonEvent[] }) => void;
    onValidate?: () => void;
    onAutoFix?: () => void;
    autoFixPreset?: string;
    autoFixPresets?: Record<string, { label: string; config: any }>;
    onApplyAutoFixPreset?: (presetId: any) => void;
    autoFixConfig?: {
        fixInvalidType: boolean;
        fixInvalidNumbers: boolean;
        fixInvalidTriggers: boolean;
        normalizeKeyOptions: boolean;
        fillKeyOptions: boolean;
        resetReviewed: boolean;
    };
    onAutoFixConfigChange?: (next: Partial<{
        fixInvalidType: boolean;
        fixInvalidNumbers: boolean;
        fixInvalidTriggers: boolean;
        normalizeKeyOptions: boolean;
        fillKeyOptions: boolean;
        resetReviewed: boolean;
    }>) => void;
    onPromote?: () => void;
    validating?: boolean;
    promoting?: boolean;
    validationResult?: any;
    canEdit?: boolean;
}

const hasLegacyTrigger = (evt: SkeletonEvent): boolean => {
    const flags = (evt?.triggers as any)?.flags_all_true;
    if (!Array.isArray(flags)) return false;
    return flags.some((x: any) => String(x || '').startsWith('legacy:'));
};

const hasMigrationNotes = (evt: SkeletonEvent): boolean => {
    const notes = (evt?.meta as any)?.migration_notes;
    return Array.isArray(notes) && notes.length > 0;
};

const isReviewed = (evt: SkeletonEvent): boolean => {
    return Boolean((evt?.meta as any)?.reviewed);
};

const isPendingReview = (evt: SkeletonEvent): boolean => {
    return !isReviewed(evt) || hasLegacyTrigger(evt) || hasMigrationNotes(evt);
};

const parseJsonSafe = <T,>(raw: string, fallback: T): T => {
    try {
        return JSON.parse(raw) as T;
    } catch {
        return fallback;
    }
};

export const EventSkeletonEditor = ({
    payload,
    onSavePayload,
    onValidate,
    onAutoFix,
    autoFixPreset = 'balanced',
    autoFixPresets = {},
    onApplyAutoFixPreset,
    autoFixConfig,
    onAutoFixConfigChange,
    onPromote,
    validating = false,
    promoting = false,
    validationResult = null,
    canEdit = true
}: EventSkeletonEditorProps) => {
    const [searchTerm, setSearchTerm] = useState('');
    const [pendingOnly, setPendingOnly] = useState(true);
    const [triggerDrafts, setTriggerDrafts] = useState<Record<string, string>>({});
    const [optionDrafts, setOptionDrafts] = useState<Record<string, string>>({});
    const [focusedEventId, setFocusedEventId] = useState('');
    const [expandedEventIds, setExpandedEventIds] = useState<Record<string, boolean>>({});
    const [issuesPage, setIssuesPage] = useState(1);
    const issuesPageSize = 12;
    const [showAdvancedTools, setShowAdvancedTools] = useState(false);
    const [showIssuesPanel, setShowIssuesPanel] = useState(false);

    const events = Array.isArray(payload?.events) ? payload!.events : [];
    const pendingCount = useMemo(() => events.filter(isPendingReview).length, [events]);

    const filtered = useMemo(() => {
        return events
            .filter((evt) => (pendingOnly ? isPendingReview(evt) : true))
            .filter((evt) => {
                const key = `${evt.id} ${evt.title}`.toLowerCase();
                return searchTerm.trim() ? key.includes(searchTerm.trim().toLowerCase()) : true;
            });
    }, [events, pendingOnly, searchTerm]);

    const allIssues = useMemo(() => {
        const raw = Array.isArray(validationResult?.issues) ? validationResult.issues : [];
        return raw;
    }, [validationResult]);

    const issuesTotalPages = useMemo(
        () => Math.max(1, Math.ceil(allIssues.length / issuesPageSize)),
        [allIssues.length]
    );

    useEffect(() => {
        setIssuesPage(1);
    }, [validationResult]);

    useEffect(() => {
        if (!allIssues.length) {
            setShowIssuesPanel(false);
        }
    }, [allIssues.length]);

    const pagedIssues = useMemo(() => {
        const safePage = Math.min(Math.max(issuesPage, 1), issuesTotalPages);
        const start = (safePage - 1) * issuesPageSize;
        return allIssues.slice(start, start + issuesPageSize);
    }, [allIssues, issuesPage, issuesTotalPages]);

    const updateEvent = (eventId: string, updater: (evt: SkeletonEvent) => SkeletonEvent) => {
        const nextEvents = events.map((evt) => (evt.id === eventId ? updater(evt) : evt));
        onSavePayload({
            ...payload,
            events: nextEvents,
        });
    };

    if (!payload) {
        return (
            <div className="flex-1 flex items-center justify-center text-sm font-bold text-slate-400">
                当前文件不是有效的骨架事件 JSON
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col overflow-hidden bg-[var(--color-warm-bg)]">
            <div className="px-8 py-6 border-b border-[var(--color-soft-border)] bg-white shadow-sm space-y-4">
                <div className="flex items-center justify-between gap-4">
                    <div>
                        <h4 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight leading-none mb-1">骨架事件复核台</h4>
                        <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/70">
                            总计 {events.length} 条 · 待复核 {pendingCount} 条
                        </div>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap justify-end">
                        <button
                            onClick={() => onValidate && onValidate()}
                            className="px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/20 hover:bg-[var(--color-cyan-light)]/40"
                        >
                            {validating ? '校验中...' : '运行校验'}
                        </button>
                        <button
                            onClick={() => onPromote && onPromote()}
                            disabled={!canEdit}
                            className="px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)] hover:bg-[var(--color-cyan-dark)] disabled:opacity-50"
                        >
                            {promoting ? '发布中...' : '发布为正式骨架'}
                        </button>
                        <button
                            onClick={() => setPendingOnly((v) => !v)}
                            className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border flex items-center gap-2 ${
                                pendingOnly
                                    ? 'bg-[var(--color-cyan-main)] text-white border-[var(--color-cyan-main)]'
                                    : 'bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/20'
                            }`}
                        >
                            <Filter size={12} />
                            {pendingOnly ? '仅待复核' : '显示全部'}
                        </button>
                        <button
                            onClick={() => setShowAdvancedTools((v) => !v)}
                            className="px-3 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/20 hover:bg-[var(--color-cyan-light)]/40 inline-flex items-center gap-1"
                        >
                            <Wrench size={12} />
                            工具
                            <ChevronDown size={12} className={`transition-transform ${showAdvancedTools ? 'rotate-180' : ''}`} />
                        </button>
                    </div>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                    <div className="relative w-72 max-w-full">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-cyan-main)]/30" size={14} />
                        <input
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            placeholder="搜索 ID / 标题..."
                            className="w-full pl-9 pr-4 py-2 bg-[var(--color-cyan-light)]/30 rounded-xl border border-transparent text-[11px] font-bold text-[var(--color-cyan-dark)] outline-none focus:bg-white focus:border-[var(--color-cyan-main)] transition-all"
                        />
                    </div>
                    {allIssues.length > 0 && (
                        <button
                            onClick={() => setShowIssuesPanel((v) => !v)}
                            className="px-3 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/20 hover:bg-[var(--color-cyan-light)]/40 inline-flex items-center gap-1"
                        >
                            问题清单
                            <ChevronDown size={12} className={`transition-transform ${showIssuesPanel ? 'rotate-180' : ''}`} />
                        </button>
                    )}
                </div>
                {showAdvancedTools && autoFixConfig && onAutoFixConfigChange && (
                    <div className="rounded-xl border border-[var(--color-cyan-main)]/15 bg-white p-3 space-y-2">
                        <div className="flex items-center justify-between">
                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/60">自动修复策略</div>
                            <button
                                onClick={() => onAutoFix && onAutoFix()}
                                disabled={!canEdit}
                                className="px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest border bg-white text-[var(--color-cyan-main)] border-[var(--color-cyan-main)]/20 hover:bg-[var(--color-cyan-light)]/40 disabled:opacity-50"
                            >
                                批量修复
                            </button>
                        </div>
                        {onApplyAutoFixPreset && Object.keys(autoFixPresets || {}).length > 0 && (
                            <div className="flex items-center gap-2">
                                <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/60">预设</div>
                                <select
                                    value={autoFixPreset}
                                    onChange={(e) => onApplyAutoFixPreset(e.target.value)}
                                    className="px-3 py-1.5 rounded-lg border border-[var(--color-cyan-main)]/20 text-xs font-black text-[var(--color-cyan-dark)] bg-white"
                                >
                                    {Object.entries(autoFixPresets).map(([id, item]) => (
                                        <option key={id} value={id}>{item.label}</option>
                                    ))}
                                </select>
                            </div>
                        )}
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-[11px] font-bold text-[var(--color-cyan-dark)]">
                            <label className="inline-flex items-center gap-2">
                                <input type="checkbox" checked={autoFixConfig.fixInvalidType} onChange={(e) => onAutoFixConfigChange({ fixInvalidType: e.target.checked })} />
                                修正非法 type
                            </label>
                            <label className="inline-flex items-center gap-2">
                                <input type="checkbox" checked={autoFixConfig.fixInvalidNumbers} onChange={(e) => onAutoFixConfigChange({ fixInvalidNumbers: e.target.checked })} />
                                修正非法数值
                            </label>
                            <label className="inline-flex items-center gap-2">
                                <input type="checkbox" checked={autoFixConfig.fixInvalidTriggers} onChange={(e) => onAutoFixConfigChange({ fixInvalidTriggers: e.target.checked })} />
                                修正 triggers 结构
                            </label>
                            <label className="inline-flex items-center gap-2">
                                <input type="checkbox" checked={autoFixConfig.normalizeKeyOptions} onChange={(e) => onAutoFixConfigChange({ normalizeKeyOptions: e.target.checked })} />
                                规范 key 选项
                            </label>
                            <label className="inline-flex items-center gap-2">
                                <input type="checkbox" checked={autoFixConfig.fillKeyOptions} onChange={(e) => onAutoFixConfigChange({ fillKeyOptions: e.target.checked })} />
                                补齐 key 选项
                            </label>
                            <label className="inline-flex items-center gap-2">
                                <input type="checkbox" checked={autoFixConfig.resetReviewed} onChange={(e) => onAutoFixConfigChange({ resetReviewed: e.target.checked })} />
                                修复后重置 reviewed
                            </label>
                        </div>
                    </div>
                )}
                {validationResult?.summary && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="rounded-xl border border-[var(--color-cyan-main)]/15 bg-white px-3 py-2">
                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/50">events</div>
                            <div className="text-sm font-black text-[var(--color-cyan-dark)]">{validationResult.summary.total_events || 0}</div>
                        </div>
                        <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2">
                            <div className="text-[10px] font-black uppercase tracking-widest text-amber-700/70">pending</div>
                            <div className="text-sm font-black text-amber-800">{validationResult.summary.pending_review || 0}</div>
                        </div>
                        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2">
                            <div className="text-[10px] font-black uppercase tracking-widest text-red-700/70">errors</div>
                            <div className="text-sm font-black text-red-700">{validationResult.summary.error_count || 0}</div>
                        </div>
                        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                            <div className="text-[10px] font-black uppercase tracking-widest text-slate-600/70">warnings</div>
                            <div className="text-sm font-black text-slate-700">{validationResult.summary.warning_count || 0}</div>
                        </div>
                    </div>
                )}
                {showIssuesPanel && allIssues.length > 0 && (
                    <div className="rounded-xl border border-[var(--color-cyan-main)]/15 bg-white p-3">
                        <div className="flex items-center justify-between mb-2">
                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/60">问题清单（全量分页）</div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => setIssuesPage((p) => Math.max(1, p - 1))}
                                    disabled={issuesPage <= 1}
                                    className="px-2 py-1 rounded border border-[var(--color-cyan-main)]/20 text-[10px] font-black text-[var(--color-cyan-main)] disabled:opacity-40"
                                >
                                    上一页
                                </button>
                                <div className="text-[10px] font-black text-slate-500">{Math.min(Math.max(issuesPage, 1), issuesTotalPages)} / {issuesTotalPages}</div>
                                <button
                                    onClick={() => setIssuesPage((p) => Math.min(issuesTotalPages, p + 1))}
                                    disabled={issuesPage >= issuesTotalPages}
                                    className="px-2 py-1 rounded border border-[var(--color-cyan-main)]/20 text-[10px] font-black text-[var(--color-cyan-main)] disabled:opacity-40"
                                >
                                    下一页
                                </button>
                            </div>
                        </div>
                        <div className="space-y-2 max-h-40 overflow-auto custom-scrollbar pr-1">
                            {pagedIssues.map((issue: any, idx: number) => {
                                const eid = String(issue?.event_id || '').trim();
                                const isError = String(issue?.level || '') === 'error';
                                return (
                                    <div key={`issue-${idx}`} className="flex items-center justify-between gap-2 text-xs">
                                        <div className={`${isError ? 'text-red-700' : 'text-amber-700'} font-bold`}>
                                            [{isError ? 'E' : 'W'}] {issue?.message || '-'}
                                        </div>
                                        <button
                                            disabled={!eid}
                                            onClick={() => {
                                                setFocusedEventId(eid);
                                                const el = document.getElementById(`skeleton-event-${eid}`);
                                                if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                            }}
                                            className="px-2 py-1 rounded-lg border border-[var(--color-cyan-main)]/20 text-[10px] font-black text-[var(--color-cyan-main)] disabled:opacity-40"
                                        >
                                            {eid ? `定位 ${eid}` : '无ID'}
                                        </button>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-8 space-y-6">
                {filtered.map((evt) => {
                    const notes = Array.isArray((evt.meta as any)?.migration_notes) ? (evt.meta as any).migration_notes : [];
                    const reviewState = isReviewed(evt);
                    const isExpanded = Boolean(expandedEventIds[evt.id]);
                    return (
                        <div
                            id={`skeleton-event-${evt.id}`}
                            key={evt.id}
                            className={`bg-white rounded-2xl border shadow-sm p-6 space-y-4 transition-all ${
                                focusedEventId === evt.id
                                    ? 'border-[var(--color-cyan-main)] shadow-md shadow-cyan-100'
                                    : 'border-[var(--color-soft-border)]'
                            }`}
                        >
                            <div className="flex items-start justify-between gap-4 flex-wrap">
                                <div className="min-w-0">
                                    <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/60">
                                        ID: {evt.id}
                                    </div>
                                    {isExpanded ? (
                                        <input
                                            value={evt.title || ''}
                                            disabled={!canEdit}
                                            onChange={(e) => updateEvent(evt.id, (old) => ({ ...old, title: e.target.value }))}
                                            className="mt-1 w-full md:w-[28rem] px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/15 text-sm font-black text-[var(--color-cyan-dark)] outline-none focus:border-[var(--color-cyan-main)]"
                                        />
                                    ) : (
                                        <div className="mt-1 text-sm font-black text-[var(--color-cyan-dark)] truncate md:max-w-[28rem]">
                                            {evt.title || '未命名事件'}
                                        </div>
                                    )}
                                    {!isExpanded && (
                                        <div className="mt-2 flex items-center gap-2 flex-wrap text-[10px] font-black uppercase tracking-widest text-slate-500">
                                            <span className="px-2 py-1 rounded-full bg-slate-100 border border-slate-200">{evt.type || 'daily'}</span>
                                            <span className="px-2 py-1 rounded-full bg-slate-100 border border-slate-200">priority {Number(evt.priority || 0)}</span>
                                            <span className="px-2 py-1 rounded-full bg-slate-100 border border-slate-200">cooldown {Number(evt.cooldown_days || 0)}</span>
                                            <span className="px-2 py-1 rounded-full bg-slate-100 border border-slate-200">{evt.once ? 'once' : 'repeat'}</span>
                                        </div>
                                    )}
                                </div>
                                <div className="flex items-center gap-2 flex-wrap">
                                    {isPendingReview(evt) ? (
                                        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-black uppercase tracking-widest">
                                            <AlertTriangle size={12} />
                                            待复核
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-black uppercase tracking-widest">
                                            <CheckCircle2 size={12} />
                                            已通过
                                        </span>
                                    )}
                                    <button
                                        onClick={() =>
                                            setExpandedEventIds((prev) => ({
                                                ...prev,
                                                [evt.id]: !Boolean(prev[evt.id]),
                                            }))
                                        }
                                        className="px-3 py-1.5 rounded-lg border border-[var(--color-cyan-main)]/20 text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] inline-flex items-center gap-1"
                                    >
                                        {isExpanded ? '收起' : '展开编辑'}
                                        <ChevronDown size={12} className={`transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                                    </button>
                                </div>
                            </div>

                            {isExpanded && (
                                <>
                                    <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                                        <div className="space-y-1">
                                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/50">type</div>
                                            <select
                                                value={evt.type || 'daily'}
                                                disabled={!canEdit}
                                                onChange={(e) => updateEvent(evt.id, (old) => ({ ...old, type: e.target.value as 'daily' | 'key' }))}
                                                className="w-full px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/15 text-sm font-bold text-[var(--color-cyan-dark)] outline-none"
                                            >
                                                <option value="daily">daily</option>
                                                <option value="key">key</option>
                                            </select>
                                        </div>
                                        <div className="space-y-1">
                                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/50">priority</div>
                                            <input
                                                type="number"
                                                value={Number(evt.priority || 0)}
                                                disabled={!canEdit}
                                                onChange={(e) => updateEvent(evt.id, (old) => ({ ...old, priority: Number(e.target.value || 0) }))}
                                                className="w-full px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/15 text-sm font-bold text-[var(--color-cyan-dark)] outline-none"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/50">cooldown_days</div>
                                            <input
                                                type="number"
                                                value={Number(evt.cooldown_days || 0)}
                                                disabled={!canEdit}
                                                onChange={(e) => updateEvent(evt.id, (old) => ({ ...old, cooldown_days: Number(e.target.value || 0) }))}
                                                className="w-full px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/15 text-sm font-bold text-[var(--color-cyan-dark)] outline-none"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/50">once</div>
                                            <select
                                                value={evt.once ? 'true' : 'false'}
                                                disabled={!canEdit}
                                                onChange={(e) => updateEvent(evt.id, (old) => ({ ...old, once: e.target.value === 'true' }))}
                                                className="w-full px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/15 text-sm font-bold text-[var(--color-cyan-dark)] outline-none"
                                            >
                                                <option value="false">false</option>
                                                <option value="true">true</option>
                                            </select>
                                        </div>
                                        <div className="space-y-1">
                                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/50">review</div>
                                            <button
                                                disabled={!canEdit}
                                                onClick={() =>
                                                    updateEvent(evt.id, (old) => ({
                                                        ...old,
                                                        meta: {
                                                            ...(old.meta || {}),
                                                            reviewed: !reviewState,
                                                            reviewed_at: !reviewState ? new Date().toISOString() : '',
                                                        },
                                                    }))
                                                }
                                                className={`w-full px-3 py-2 rounded-xl text-xs font-black border transition-all ${
                                                    reviewState
                                                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                                        : 'bg-amber-50 text-amber-700 border-amber-200'
                                                }`}
                                            >
                                                {reviewState ? '已复核' : '标记复核'}
                                            </button>
                                        </div>
                                    </div>

                                    {notes.length > 0 && (
                                        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
                                            <div className="text-[10px] font-black uppercase tracking-widest text-amber-700 mb-1">迁移提示</div>
                                            {notes.map((note: string, idx: number) => (
                                                <div key={`${evt.id}-note-${idx}`} className="text-xs font-bold text-amber-800/90">
                                                    - {note}
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="space-y-1">
                                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/50">triggers (json)</div>
                                            <textarea
                                                rows={6}
                                                disabled={!canEdit}
                                                value={triggerDrafts[evt.id] ?? JSON.stringify(evt.triggers || {}, null, 2)}
                                                onChange={(e) => setTriggerDrafts((prev) => ({ ...prev, [evt.id]: e.target.value }))}
                                                onBlur={() => {
                                                    const raw = triggerDrafts[evt.id];
                                                    if (typeof raw !== 'string') return;
                                                    updateEvent(evt.id, (old) => ({
                                                        ...old,
                                                        triggers: parseJsonSafe(raw, old.triggers || {}),
                                                    }));
                                                }}
                                                className="w-full px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/15 text-xs font-mono text-[var(--color-cyan-dark)] outline-none bg-[var(--color-cyan-light)]/10"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)]/50">options (json)</div>
                                            <textarea
                                                rows={6}
                                                disabled={!canEdit}
                                                value={optionDrafts[evt.id] ?? JSON.stringify(evt.options || [], null, 2)}
                                                onChange={(e) => setOptionDrafts((prev) => ({ ...prev, [evt.id]: e.target.value }))}
                                                onBlur={() => {
                                                    const raw = optionDrafts[evt.id];
                                                    if (typeof raw !== 'string') return;
                                                    updateEvent(evt.id, (old) => ({
                                                        ...old,
                                                        options: parseJsonSafe(raw, old.options || []),
                                                    }));
                                                }}
                                                className="w-full px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/15 text-xs font-mono text-[var(--color-cyan-dark)] outline-none bg-[var(--color-cyan-light)]/10"
                                            />
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    );
                })}

                {filtered.length === 0 && (
                    <div className="py-14 text-center text-sm font-bold text-slate-400">当前筛选下没有事件</div>
                )}
            </div>
        </div>
    );
};
