import { BookOpen, User, Sparkles, Clock } from 'lucide-react';
import { PagedOverlayPanel } from '../common/PagedOverlayPanel';
import type { OverlayPage } from '../common/PagedOverlayPanel';

export const EditorGuide = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  const pages: OverlayPage[] = [
    {
      title: '模组开发概览',
      icon: <BookOpen />,
      color: 'var(--color-cyan-main)',
      content: (
        <div className="space-y-4">
          <p className="text-[var(--color-life-text)] leading-relaxed text-sm">
            欢迎来到 <span className="font-black text-[var(--color-cyan-dark)]">AI 宿舍生存编辑器</span>。这是一个强大的内容中枢，您可以自由定义世界观、角色设定、AI 逻辑以及剧情走向。
          </p>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-[var(--color-warm-bg)] rounded-2xl border border-[var(--color-soft-border)]">
              <h4 className="font-black text-xs text-[var(--color-cyan-dark)] mb-2 uppercase tracking-widest">核心工作流</h4>
              <ul className="text-[10px] space-y-2 text-[var(--color-life-text)]/60 font-bold">
                <li>1. 配置世界观背景</li>
                <li>2. 完善室友档案</li>
                <li>3. 注入系统逻辑 (Skill)</li>
                <li>4. 编排时间轴事件</li>
              </ul>
            </div>
            <div className="p-4 bg-[var(--color-cyan-light)] rounded-2xl border border-[var(--color-cyan-main)]/20">
              <h4 className="font-black text-xs text-[var(--color-cyan-dark)] mb-2 uppercase tracking-widest">保存规则</h4>
              <p className="text-[10px] text-[var(--color-cyan-dark)]/70 font-bold leading-relaxed">
                编辑器支持即时预览。请务必点击右上方“提交修改”将内容同步至物理文件。
              </p>
            </div>
          </div>
        </div>
      ),
    },
    {
      title: '角色档案管理',
      icon: <User />,
      color: 'var(--color-cyan-main)',
      content: (
        <div className="space-y-4">
          <p className="text-[var(--color-life-text)] leading-relaxed text-sm">
            在“角色配置”中，您可以管理可选的室友名单。
          </p>
          <div className="space-y-3">
            {[
              '点击“创建新角色”后，系统会自动为您初始化 .md 设定文件。',
              '您可以直接上传 WebP/PNG 头像，前端会实时更新渲染。',
              '点击“设定编辑”进入代码模式，详细描述角色的性格、背景和行为准则。',
            ].map((text, i) => (
              <div key={i} className="flex items-start space-x-3">
                <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[var(--color-cyan-main)] shrink-0" />
                <p className="text-xs text-[var(--color-life-text)]/80 font-medium">{text}</p>
              </div>
            ))}
          </div>
        </div>
      ),
    },
    {
      title: 'AI 插件与逻辑 (Skill)',
      icon: <Sparkles />,
      color: 'var(--color-yellow-main)',
      content: (
        <div className="space-y-4">
          <p className="text-[var(--color-life-text)] leading-relaxed text-sm">
            Skill 是赋予 AI 新能力的“大脑插件”。通过编写 Skill，您可以让 AI 学会新的游戏系统。
          </p>
          <div className="p-4 bg-[var(--color-yellow-light)] rounded-2xl border-2 border-dashed border-[var(--color-yellow-main)]/30">
            <h4 className="font-black text-xs text-[var(--color-cyan-dark)] mb-2">✨ AI 一键生成</h4>
            <p className="text-[10px] text-[var(--color-life-text)]/80 font-bold">
              您可以点击“AI 一键生成提示词”，只需输入您的脑洞（如“宿舍点外卖系统”），AI 就会为您自动编写成具有强约束力的系统指令。
            </p>
          </div>
          <p className="text-[10px] text-[var(--color-cyan-main)] font-black">
            * 自定义 Skill 文件保存在 data/prompts/skills/ 目录下。
          </p>
        </div>
      ),
    },
    {
      title: '时间轴与事件',
      icon: <Clock />,
      color: 'var(--color-cyan-dark)',
      content: (
        <div className="space-y-4">
          <p className="text-[var(--color-life-text)] leading-relaxed text-sm">
            “剧情事件”控制着游戏的节奏。系统将事件库分为：固定剧情、通用随机、角色专属、条件触发。
          </p>
          <div className="space-y-2">
            {[
              { label: '时间轴可视化', desc: '解析 timeline.json' },
              { label: '拖拽分发', desc: '调整事件触发优先级' },
              { label: 'CSV 表格编辑', desc: '类似 Excel 的操作体验' },
            ].map((item, i) => (
              <div key={i} className="flex justify-between items-center p-3 bg-[var(--color-warm-bg)] rounded-xl border border-[var(--color-soft-border)]">
                <span className="text-xs font-black text-[var(--color-cyan-dark)]">{item.label}</span>
                <span className="text-[10px] text-[var(--color-life-text)]/40 font-bold">{item.desc}</span>
              </div>
            ))}
          </div>
        </div>
      ),
    },
  ];

  return <PagedOverlayPanel isOpen={isOpen} onClose={onClose} pages={pages} sectionLabel="编辑器引导" />;
};
