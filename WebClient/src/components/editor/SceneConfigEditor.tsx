import { Plus, Trash2, Image as ImageIcon } from 'lucide-react';

interface SceneItem {
  name: string;
  image: string;
  keywords?: string[];
}

interface SceneConfig {
  default_image: string;
  scenes: SceneItem[];
}

interface SceneConfigEditorProps {
  config: SceneConfig;
  onChange: (next: SceneConfig) => void;
  onSave: () => void;
  canEdit?: boolean;
}

export const SceneConfigEditor = ({
  config,
  onChange,
  onSave,
  canEdit = true,
}: SceneConfigEditorProps) => {
  const scenes = Array.isArray(config?.scenes) ? config.scenes : [];

  const updateScene = (index: number, patch: Partial<SceneItem>) => {
    const nextScenes = scenes.map((s, i) => (i === index ? { ...s, ...patch } : s));
    onChange({ ...config, scenes: nextScenes });
  };

  const addScene = () => {
    onChange({
      ...config,
      scenes: [...scenes, { name: '新场景', image: '/assets/backgrounds/未知.jpg', keywords: [] }],
    });
  };

  const removeScene = (index: number) => {
    onChange({ ...config, scenes: scenes.filter((_, i) => i !== index) });
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[var(--color-warm-bg)]">
      <div className="px-12 py-8 border-b border-[var(--color-soft-border)] flex flex-wrap items-center justify-between gap-3 shrink-0 bg-white">
        <div>
          <h4 className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-tight">场景配置</h4>
          <p className="text-[11px] font-bold text-slate-500 mt-1">每个场景支持：名称 + 图片 + 关键词匹配。</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={addScene}
            disabled={!canEdit}
            className="px-4 py-2 rounded-xl bg-[var(--color-cyan-dark)] text-white text-[10px] font-black uppercase tracking-widest disabled:opacity-50"
          >
            <Plus size={14} className="inline mr-1" />
            新增场景
          </button>
          <button
            onClick={onSave}
            disabled={!canEdit}
            className="px-4 py-2 rounded-xl bg-[var(--color-yellow-main)] text-[var(--color-cyan-dark)] text-[10px] font-black uppercase tracking-widest disabled:opacity-50"
          >
            提交场景配置
          </button>
        </div>
      </div>

      <div className="p-8 border-b border-[var(--color-soft-border)] bg-white/70">
        <label className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest">默认背景图</label>
        <input
          value={String(config?.default_image || '')}
          onChange={(e) => onChange({ ...config, default_image: e.target.value })}
          disabled={!canEdit}
          className="mt-2 w-full px-4 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 text-sm font-bold text-[var(--color-cyan-dark)] disabled:opacity-60"
          placeholder="/assets/backgrounds/宿舍.jpg"
        />
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-8 space-y-4">
        {scenes.map((scene, idx) => (
          <div key={`${scene.name}-${idx}`} className="bg-white rounded-2xl border border-[var(--color-soft-border)] p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-black text-[var(--color-cyan-dark)] flex items-center">
                <ImageIcon size={14} className="mr-2 text-[var(--color-cyan-main)]" />
                场景 #{idx + 1}
              </div>
              <button
                onClick={() => removeScene(idx)}
                disabled={!canEdit}
                className="p-2 rounded-lg text-[var(--color-yellow-main)] hover:bg-[var(--color-yellow-light)] disabled:opacity-40"
              >
                <Trash2 size={14} />
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest">场景名</label>
                <input
                  value={scene.name || ''}
                  onChange={(e) => updateScene(idx, { name: e.target.value })}
                  disabled={!canEdit}
                  className="mt-1 w-full px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 text-sm font-bold text-[var(--color-cyan-dark)] disabled:opacity-60"
                  placeholder="宿舍阳台"
                />
              </div>
              <div>
                <label className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest">图片 URL/路径</label>
                <input
                  value={scene.image || ''}
                  onChange={(e) => updateScene(idx, { image: e.target.value })}
                  disabled={!canEdit}
                  className="mt-1 w-full px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 text-sm font-bold text-[var(--color-cyan-dark)] disabled:opacity-60"
                  placeholder="/assets/backgrounds/宿舍.jpg"
                />
              </div>
            </div>
            <div className="mt-3">
              <label className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest">关键词（用逗号分隔）</label>
              <input
                value={(scene.keywords || []).join(',')}
                onChange={(e) =>
                  updateScene(idx, {
                    keywords: e.target.value
                      .split(',')
                      .map((k) => k.trim())
                      .filter(Boolean),
                  })
                }
                disabled={!canEdit}
                className="mt-1 w-full px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 text-sm font-bold text-[var(--color-cyan-dark)] disabled:opacity-60"
                placeholder="宿舍,寝室,阳台"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
