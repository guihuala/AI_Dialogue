import { useMemo, useState } from 'react';
import { ChevronRight, Power, Search, Plus, FileText } from 'lucide-react';

interface SkillItem {
  key: string;
  label: string;
  desc: string;
  enabled: boolean;
  files: string[];
  primaryEditFile?: string;
  crossModuleRef?: boolean;
}

interface SkillCenterProps {
  skills: SkillItem[];
  skillTraceWindow?: Array<{ enabled_skills: string[]; tool_call_names: string[] }>;
  canEdit: boolean;
  isSavingFeatures: boolean;
  onToggleSkill: (skillKey: string) => void;
  onOpenFile: (fileName: string) => void;
  onAddNew?: () => void;
  hideHeader?: boolean;
  searchTerm?: string;
  onSearchTermChange?: (value: string) => void;
}

const matchToolToSkill = (skillKey: string, toolName: string): boolean => {
  const name = String(toolName || '').trim();
  if (!name) return false;
  if (skillKey === '__phone_system__') return name === 'phone_enqueue_message';
  if (skillKey === 'secret_note') return name === 'state_append_memory';
  if (skillKey === 'relationship_milestone') return name === 'state_append_memory';
  return name.includes(skillKey);
};

export const SkillCenter = ({
  skills,
  skillTraceWindow = [],
  canEdit,
  isSavingFeatures,
  onToggleSkill,
  onOpenFile,
  onAddNew,
  hideHeader = false,
  searchTerm: controlledSearchTerm,
  onSearchTermChange,
}: SkillCenterProps) => {
  const [internalSearchTerm, setInternalSearchTerm] = useState('');
  const searchTerm = controlledSearchTerm ?? internalSearchTerm;
  const setSearchTerm = onSearchTermChange ?? setInternalSearchTerm;
  const [activeKey, setActiveKey] = useState(skills[0]?.key || '');

  const filtered = useMemo(() => {
    const q = searchTerm.trim();
    if (!q) return skills;
    return skills.filter((s) => s.label.includes(q) || s.desc.includes(q) || s.key.includes(q));
  }, [skills, searchTerm]);

  const activeSkill = useMemo(
    () => filtered.find((s) => s.key === activeKey) || filtered[0] || null,
    [filtered, activeKey],
  );

  const usageStats = useMemo(() => {
    const turns = Array.isArray(skillTraceWindow) ? skillTraceWindow : [];
    const windowTurns = turns.length;
    const seenCount = turns.filter((t) => (t.enabled_skills || []).includes(activeSkill?.key || '')).length;
    const toolHitCount = turns.filter((t) =>
      (t.tool_call_names || []).some((name) => matchToolToSkill(activeSkill?.key || '', name))
    ).length;
    const toolTotal = turns.reduce((sum, t) => sum + Number((t.tool_call_names || []).length), 0);
    const exposureRate = windowTurns > 0 ? Math.round((seenCount / windowTurns) * 100) : 0;
    const toolHitRate = windowTurns > 0 ? Math.round((toolHitCount / windowTurns) * 100) : 0;
    return {
      windowTurns,
      seenCount,
      toolHitCount,
      toolTotal,
      exposureRate,
      toolHitRate,
    };
  }, [skillTraceWindow, activeSkill?.key]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[var(--color-warm-bg)]">
      {!hideHeader && <div className="px-7 py-6 flex flex-col lg:flex-row lg:items-center justify-between gap-4 shrink-0 bg-white border-b border-[var(--color-soft-border)]">
        <div className="space-y-1.5 text-left">
          <h4 className="text-[2rem] leading-none font-black text-[var(--color-cyan-dark)] tracking-tight">技能中心</h4>
          <p className="text-sm font-bold text-[var(--color-cyan-dark)]/45">
            管理技能启停、查看使用情况，并快速跳到关联文件。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-cyan-main)]/30" size={18} />
            <input
              type="text"
              placeholder="搜索 skill..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="h-11 w-[20rem] max-w-full pl-12 pr-5 bg-[var(--color-cyan-light)]/22 rounded-2xl border border-[var(--color-cyan-main)]/12 text-sm font-bold outline-none focus:border-[var(--color-cyan-main)]/40 focus:bg-white transition-all shadow-inner text-[var(--color-cyan-dark)]"
            />
          </div>
          {onAddNew && (
            <button
              onClick={onAddNew}
              disabled={!canEdit}
              className="inline-flex h-11 items-center justify-center gap-2 px-5 rounded-2xl text-xs font-black bg-white border border-[var(--color-cyan-main)]/20 text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-light)]/25 transition-all disabled:opacity-60"
            >
              <Plus size={14} />
              新增自定义 Skill
            </button>
          )}
        </div>
      </div>}

      <div className="flex-1 overflow-hidden p-5">
        <div className="grid grid-cols-1 xl:grid-cols-[320px_1fr] gap-5 h-full min-h-0">
          <div className="bg-white rounded-2xl border border-[var(--color-soft-border)] overflow-hidden h-full min-h-0 flex flex-col">
            <div className="px-4 py-3 border-b border-[var(--color-soft-border)] text-[11px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest">
              Skills ({filtered.length})
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
              {filtered.map((item) => (
                <button
                  key={item.key}
                  onClick={() => setActiveKey(item.key)}
                  className={`w-full px-4 py-3 text-left border-b border-[var(--color-soft-border)]/70 hover:bg-[var(--color-cyan-light)]/20 transition-all ${
                    activeSkill?.key === item.key ? 'bg-[var(--color-cyan-light)]/25' : 'bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-black text-[var(--color-cyan-dark)] text-sm">{item.label}</div>
                    <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${item.enabled ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-500'}`}>
                      {item.enabled ? 'ON' : 'OFF'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1 line-clamp-1">{item.desc}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-[var(--color-soft-border)] p-5 overflow-y-auto custom-scrollbar h-full min-h-0 shadow-sm">
            {!activeSkill ? (
              <div className="h-full flex items-center justify-center text-slate-400 font-bold">未找到匹配的 skill</div>
            ) : (
              <div className="space-y-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h5 className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-tight">{activeSkill.label}</h5>
                    <p className="text-sm text-slate-500 font-bold mt-1">{activeSkill.desc}</p>
                    <div className="text-xs text-slate-400 mt-2 font-mono">{activeSkill.key}</div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {activeSkill.crossModuleRef && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-100 text-amber-700 border border-amber-200">
                          跨模块引用
                        </span>
                      )}
                      {!!activeSkill.primaryEditFile && (
                        <button
                          onClick={() => onOpenFile(activeSkill.primaryEditFile as string)}
                          className="px-2 py-0.5 rounded-full text-[10px] font-black bg-cyan-50 text-cyan-700 border border-cyan-200 hover:bg-cyan-100 transition-all"
                        >
                          主编辑位置：{activeSkill.primaryEditFile}
                        </button>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => onToggleSkill(activeSkill.key)}
                    disabled={!canEdit || isSavingFeatures}
                    className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs font-black transition-all ${
                      activeSkill.enabled
                        ? 'bg-[var(--color-cyan-main)] text-white'
                        : 'bg-white border border-[var(--color-cyan-main)]/20 text-slate-600'
                    } ${(!canEdit || isSavingFeatures) ? 'opacity-60 cursor-not-allowed' : 'hover:opacity-90'}`}
                  >
                    <Power size={14} />
                    {activeSkill.enabled ? '关闭技能' : '开启技能'}
                  </button>
                </div>

                <div className="rounded-2xl border border-[var(--color-soft-border)] p-4">
                  <div className="text-[11px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest mb-3">
                    来源统计（最近 {usageStats.windowTurns || 0} 回合）
                  </div>
                  {usageStats.windowTurns === 0 ? (
                    <div className="text-sm text-slate-400 font-bold">暂无回合数据，进入游戏后会自动显示</div>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                      <div className="rounded-lg bg-[var(--color-cyan-light)]/18 border border-[var(--color-cyan-main)]/15 px-3 py-2">
                        <div className="text-slate-400 font-bold">启用回合</div>
                        <div className="text-[var(--color-cyan-dark)] font-black mt-0.5">{usageStats.seenCount}/{usageStats.windowTurns}</div>
                      </div>
                      <div className="rounded-lg bg-[var(--color-cyan-light)]/18 border border-[var(--color-cyan-main)]/15 px-3 py-2">
                        <div className="text-slate-400 font-bold">启用占比</div>
                        <div className="text-[var(--color-cyan-dark)] font-black mt-0.5">{usageStats.exposureRate}%</div>
                      </div>
                      <div className="rounded-lg bg-[var(--color-cyan-light)]/18 border border-[var(--color-cyan-main)]/15 px-3 py-2">
                        <div className="text-slate-400 font-bold">Tool 命中回合</div>
                        <div className="text-[var(--color-cyan-dark)] font-black mt-0.5">{usageStats.toolHitCount}/{usageStats.windowTurns}</div>
                      </div>
                      <div className="rounded-lg bg-[var(--color-cyan-light)]/18 border border-[var(--color-cyan-main)]/15 px-3 py-2">
                        <div className="text-slate-400 font-bold">Tool 命中率</div>
                        <div className="text-[var(--color-cyan-dark)] font-black mt-0.5">{usageStats.toolHitRate}%</div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="rounded-2xl border border-[var(--color-soft-border)] p-4">
                  <div className="text-[11px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest mb-3">
                    关联文件（{activeSkill.files.length}）
                  </div>
                  {activeSkill.files.length === 0 ? (
                    <div className="text-sm text-slate-400 font-bold">暂无关联文件</div>
                  ) : (
                    <div className="space-y-2">
                      {activeSkill.files.map((f) => {
                        const isPrimary = !!activeSkill.primaryEditFile && f === activeSkill.primaryEditFile;
                        const isReference = !!activeSkill.crossModuleRef && !isPrimary;
                        return (
                        <button
                          key={f}
                          onClick={() => onOpenFile(f)}
                          className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-[var(--color-cyan-main)]/12 hover:bg-[var(--color-cyan-light)]/20 transition-all text-left"
                        >
                          <span className="inline-flex items-center gap-2 text-sm font-bold text-[var(--color-cyan-dark)] min-w-0">
                            <FileText size={14} />
                            <span className="truncate">{f}</span>
                            {isPrimary && (
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-cyan-100 text-cyan-700 border border-cyan-200 shrink-0">
                                主编辑
                              </span>
                            )}
                            {isReference && (
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-amber-100 text-amber-700 border border-amber-200 shrink-0">
                                引用
                              </span>
                            )}
                          </span>
                          <ChevronRight size={14} className="text-slate-400" />
                        </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
