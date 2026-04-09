import { Download, RefreshCw, X } from 'lucide-react';

interface WorkshopLibraryState {
  tone: 'info' | 'warning';
  title: string;
  body: string;
}

interface WorkshopModDetailModalProps {
  mod: any;
  libraryState: WorkshopLibraryState | null;
  canPublishWorkshopMods: boolean;
  focusTags: string[];
  sourceLabel: string;
  actionTarget: string | null;
  onClose: () => void;
  onDownload: () => Promise<void> | void;
}

export const WorkshopModDetailModal = ({
  mod,
  libraryState,
  canPublishWorkshopMods,
  focusTags,
  sourceLabel,
  actionTarget,
  onClose,
  onDownload
}: WorkshopModDetailModalProps) => {
  const summaryCards = [
    { label: '角色', value: mod.summary?.character_count ?? 0 },
    { label: '技能', value: mod.summary?.skill_count ?? 0 },
    { label: '世界', value: mod.summary?.world_count ?? 0 },
    { label: '事件', value: mod.summary?.csv_files ?? 0 }
  ];

  const totalFiles = (mod.summary?.md_files ?? 0) + (mod.summary?.csv_files ?? 0);
  const isDownloading = actionTarget === `dl-${mod.id}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-3xl rounded-[2rem] border border-[var(--color-cyan-main)]/12 bg-white shadow-2xl animate-scale-in overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-[var(--color-cyan-main)]/10 px-6 py-5 md:px-8">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <span className="rounded-full bg-[var(--color-cyan-light)] px-3 py-1 text-xs font-black text-[var(--color-cyan-main)]">
                {sourceLabel}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-black text-slate-500">
                v{mod.version || 1}
              </span>
              {focusTags.slice(0, 2).map((tag) => (
                <span key={tag} className="rounded-full bg-amber-50 px-3 py-1 text-xs font-black text-amber-700">
                  {tag}
                </span>
              ))}
            </div>
            <h3 className="text-2xl md:text-3xl font-black tracking-tight text-[var(--color-cyan-dark)] break-words">
              {mod.name}
            </h3>
            <p className="mt-2 text-sm font-bold text-slate-500">
              作者 {mod.author} · 下载 {mod.downloads} · {mod.updated_at ? `更新于 ${String(mod.updated_at).split(' ')[0]}` : '最近更新'}
            </p>
          </div>
          <button onClick={onClose} className="shrink-0 rounded-xl p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700">
            <X size={20} />
          </button>
        </div>

        <div className="space-y-5 px-6 py-5 md:px-8 md:py-6">
          <section className="rounded-[1.5rem] border border-[var(--color-cyan-main)]/10 bg-[var(--color-cyan-light)]/18 p-5">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {summaryCards.map((item) => (
                <div key={item.label} className="rounded-2xl bg-white px-4 py-4">
                  <div className="text-xs font-black text-[var(--color-cyan-main)]">{item.label}</div>
                  <div className="mt-2 text-2xl font-black text-[var(--color-cyan-dark)]">{item.value}</div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-sm font-bold leading-7 text-slate-600">
              {mod.description || '作者还没有填写模组简介。'}
            </p>
            <div className="mt-3 text-xs font-black text-slate-400">
              共 {totalFiles} 个内容文件
            </div>
          </section>

          {libraryState && (
            <section
              className={`rounded-[1.5rem] border p-5 ${
                libraryState.tone === 'warning'
                  ? 'border-amber-200 bg-amber-50/85'
                  : 'border-[var(--color-cyan-main)]/10 bg-white'
              }`}
            >
              <div className={`text-sm font-black ${libraryState.tone === 'warning' ? 'text-amber-700' : 'text-[var(--color-cyan-main)]'}`}>
                {libraryState.title}
              </div>
              <p className={`mt-3 text-sm font-semibold leading-7 ${libraryState.tone === 'warning' ? 'text-amber-800' : 'text-slate-600'}`}>
                {libraryState.body}
              </p>
            </section>
          )}

          <section className={`rounded-[1.5rem] border p-5 ${canPublishWorkshopMods ? 'border-emerald-200 bg-emerald-50/75' : 'border-amber-200 bg-amber-50/85'}`}>
            <div className={`text-sm font-black ${canPublishWorkshopMods ? 'text-emerald-700' : 'text-amber-700'}`}>
              {canPublishWorkshopMods ? '已登录账户' : '访客模式'}
            </div>
            <p className={`mt-3 text-sm font-semibold leading-7 ${canPublishWorkshopMods ? 'text-emerald-800' : 'text-[var(--color-cyan-dark)]/70'}`}>
              {canPublishWorkshopMods
                ? '可以下载这个模组到本地库，也可以在编辑器里继续维护并公开自己的作品。'
                : '可以先下载到本地库并继续游玩；如果以后想公开自己的模组，再登录正式账户即可。'}
            </p>
          </section>
        </div>

        <div className="flex flex-col-reverse sm:flex-row gap-3 border-t border-[var(--color-cyan-main)]/10 px-6 py-5 md:px-8">
          <button
            onClick={onClose}
            className="flex-1 rounded-2xl border border-[var(--color-cyan-main)]/15 bg-white px-5 py-4 text-sm font-black text-[var(--color-cyan-main)] transition-all hover:bg-[var(--color-cyan-main)]/6"
          >
            关闭
          </button>
          <button
            onClick={onDownload}
            disabled={isDownloading}
            className="flex-[1.2] rounded-2xl bg-[var(--color-cyan-main)] px-5 py-4 text-sm font-black text-white transition-all hover:bg-[var(--color-cyan-dark)] disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isDownloading ? <RefreshCw size={16} className="animate-spin" /> : <Download size={16} />}
            {mod.is_owned_by_current_user ? '查看我的库副本' : '下载到我的库'}
          </button>
        </div>
      </div>
    </div>
  );
};
