import { Plus, Trash2, Image as ImageIcon } from 'lucide-react';
import { useEffect, useState } from 'react';

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
  hideHeader?: boolean;
}

export const SceneConfigEditor = ({
  config,
  onChange,
  onSave,
  canEdit = true,
  hideHeader = false,
}: SceneConfigEditorProps) => {
  const scenes = Array.isArray(config?.scenes) ? config.scenes : [];
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (scenes.length === 0) {
      setActiveIndex(0);
      return;
    }
    if (activeIndex > scenes.length - 1) {
      setActiveIndex(scenes.length - 1);
    }
  }, [scenes.length, activeIndex]);

  const updateScene = (index: number, patch: Partial<SceneItem>) => {
    const nextScenes = scenes.map((s, i) => (i === index ? { ...s, ...patch } : s));
    onChange({ ...config, scenes: nextScenes });
  };

  const addScene = () => {
    onChange({
      ...config,
      scenes: [...scenes, { name: '新场景', image: '/assets/backgrounds/未知.jpg', keywords: [] }],
    });
    setActiveIndex(scenes.length);
  };

  const removeScene = (index: number) => {
    onChange({ ...config, scenes: scenes.filter((_, i) => i !== index) });
    if (index <= activeIndex) {
      setActiveIndex(Math.max(0, activeIndex - 1));
    }
  };

  const activeScene = scenes[activeIndex];

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-[var(--color-warm-bg)]">
      {!hideHeader && <div className="px-7 py-6 border-b border-[var(--color-soft-border)] flex flex-col lg:flex-row lg:items-center justify-between gap-4 shrink-0 bg-white">
        <div className="space-y-1.5">
          <h4 className="text-[2rem] leading-none font-black text-[var(--color-cyan-dark)] tracking-tight">场景配置</h4>
          <p className="text-sm font-bold text-[var(--color-cyan-dark)]/45">统一维护场景名称、图片和关键词匹配。</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={addScene}
            disabled={!canEdit}
            className="inline-flex h-11 items-center justify-center gap-2 px-5 rounded-2xl bg-[var(--color-cyan-dark)] text-white text-xs font-black disabled:opacity-50 shadow-sm hover:bg-[var(--color-cyan-main)] transition-all"
          >
            <Plus size={14} />
            新增场景
          </button>
          <button
            onClick={onSave}
            disabled={!canEdit}
            className="inline-flex h-11 items-center justify-center px-5 rounded-2xl bg-[var(--color-yellow-main)] text-[var(--color-cyan-dark)] text-xs font-black disabled:opacity-50 shadow-sm hover:brightness-[1.02] transition-all"
          >
            提交场景配置
          </button>
        </div>
      </div>}

      <div className="flex-1 overflow-hidden p-5">
        <div className="grid grid-cols-1 xl:grid-cols-[320px_1fr] gap-5 h-full min-h-0">
          <div className="bg-white rounded-2xl border border-[var(--color-soft-border)] overflow-hidden h-full min-h-0 flex flex-col">
            <div className="px-4 py-3 border-b border-[var(--color-soft-border)] text-[11px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest">
              场景资源 ({scenes.length})
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
              {scenes.map((scene, idx) => (
                <button
                  key={`${scene.name}-${idx}`}
                  onClick={() => setActiveIndex(idx)}
                  className={`w-full px-4 py-3 border-b border-[var(--color-soft-border)]/70 text-left transition-all ${
                    idx === activeIndex ? 'bg-[var(--color-cyan-light)]/25' : 'bg-white hover:bg-[var(--color-cyan-light)]/18'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className="text-sm font-black text-[var(--color-cyan-dark)] truncate">{scene.name || `场景 #${idx + 1}`}</div>
                    {(scene.image || '') === String(config?.default_image || '') && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-amber-100 text-amber-700 border border-amber-200 shrink-0">
                        默认图
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-500 font-bold mt-1 truncate">{scene.image || '未设置图片'}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-[var(--color-soft-border)] p-5 overflow-y-auto custom-scrollbar h-full min-h-0 shadow-sm">
            {!activeScene ? (
              <div className="h-full flex items-center justify-center text-slate-400 font-bold">请先添加场景</div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-black text-[var(--color-cyan-dark)] flex items-center">
                    <ImageIcon size={14} className="mr-2 text-[var(--color-cyan-main)]" />
                    场景 #{activeIndex + 1}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onChange({ ...config, default_image: String(activeScene.image || '') })}
                      disabled={!canEdit || !String(activeScene.image || '').trim()}
                      className="px-2.5 py-1 rounded-lg text-[10px] font-black bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 disabled:opacity-40"
                      title="将当前场景图片设为默认图"
                    >
                      设为默认图
                    </button>
                    <button
                      onClick={() => removeScene(activeIndex)}
                      disabled={!canEdit}
                      className="p-2 rounded-lg text-[var(--color-yellow-main)] hover:bg-[var(--color-yellow-light)] disabled:opacity-40"
                      title="删除当前场景"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                <div className="rounded-xl overflow-hidden border border-[var(--color-cyan-main)]/12 bg-slate-50">
                  <img
                    src={activeScene.image || String(config?.default_image || '/assets/backgrounds/宿舍.jpg')}
                    alt={activeScene.name || `scene-${activeIndex + 1}`}
                    className="w-full h-44 object-cover"
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).src = String(config?.default_image || '/assets/backgrounds/宿舍.jpg');
                    }}
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest">场景名</label>
                    <input
                      value={activeScene.name || ''}
                      onChange={(e) => updateScene(activeIndex, { name: e.target.value })}
                      disabled={!canEdit}
                      className="mt-1 w-full px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 text-sm font-bold text-[var(--color-cyan-dark)] disabled:opacity-60"
                      placeholder="宿舍阳台"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest">图片 URL/路径</label>
                    <input
                      value={activeScene.image || ''}
                      onChange={(e) => updateScene(activeIndex, { image: e.target.value })}
                      disabled={!canEdit}
                      className="mt-1 w-full px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 text-sm font-bold text-[var(--color-cyan-dark)] disabled:opacity-60"
                      placeholder="/assets/backgrounds/宿舍.jpg"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest">关键词（用逗号分隔）</label>
                  <input
                    value={(activeScene.keywords || []).join(',')}
                    onChange={(e) =>
                      updateScene(activeIndex, {
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
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
