import { Bell, Sparkles, ScrollText } from 'lucide-react';
import { PagedOverlayPanel } from './PagedOverlayPanel';
import type { OverlayPage } from './PagedOverlayPanel';

export const AnnouncementPanel = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  const pages: OverlayPage[] = [
    {
      title: '近期公告',
      icon: <Bell />,
      color: 'var(--color-cyan-main)',
      content: (
        <div className="space-y-5">
          <div className="p-5 rounded-[1.75rem] bg-[var(--color-cyan-light)] border border-[var(--color-cyan-main)]/20">
            <p className="text-[10px] font-black uppercase tracking-[0.35em] text-[var(--color-cyan-main)]/60 mb-2">Announcement</p>
            <h4 className="text-xl font-black text-[var(--color-cyan-dark)] mb-3">宿舍系统持续施工中</h4>
            <p className="text-sm leading-relaxed text-[var(--color-life-text)]">
              当前版本已经支持动态主角、模组工作流和后台管理优化。部分 AI 生成体验仍在持续打磨，若遇到表现异常，欢迎回到编辑器与设置页进一步调整。
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-2xl bg-[var(--color-warm-bg)] border border-[var(--color-soft-border)]">
              <p className="text-[10px] font-black uppercase tracking-[0.25em] text-[var(--color-cyan-main)]/50 mb-2">推荐体验</p>
              <p className="text-xs text-[var(--color-life-text)]/80 font-medium leading-relaxed">
                首次进入时，建议先从默认模组开始游玩，确认节奏和角色组合满意后，再逐步开启自定义 prompt 与事件池修改。
              </p>
            </div>
            <div className="p-4 rounded-2xl bg-[var(--color-yellow-light)] border border-[var(--color-yellow-main)]/20">
              <p className="text-[10px] font-black uppercase tracking-[0.25em] text-[var(--color-yellow-main)]/80 mb-2">测试提醒</p>
              <p className="text-xs text-[var(--color-life-text)]/80 font-medium leading-relaxed">
                如果你刚修改了角色、事件或提示词，记得重新开始一局，确保新设定完整进入本轮游戏状态。
              </p>
            </div>
          </div>
        </div>
      ),
    },
    {
      title: '开发进度',
      icon: <Sparkles />,
      color: 'var(--color-yellow-main)',
      content: (
        <div className="space-y-4">
          {[
            '单一 DM 模式已作为主线路径，生成速度与稳定性更适合当前玩法。',
            '主角已从写死角色改为玩家可配置，系统 prompt 会随主角档案动态拼接。',
            '编辑器引导、公告面板、确认框等前端交互正在统一成可复用组件。',
          ].map((item, index) => (
            <div key={index} className="flex items-start gap-3 p-4 rounded-2xl bg-[var(--color-warm-bg)] border border-[var(--color-soft-border)]">
              <div className="w-7 h-7 rounded-full bg-[var(--color-yellow-main)] text-white flex items-center justify-center text-[11px] font-black shrink-0">
                {index + 1}
              </div>
              <p className="text-sm leading-relaxed text-[var(--color-life-text)]/85 font-medium">{item}</p>
            </div>
          ))}
        </div>
      ),
    },
    {
      title: '游玩建议',
      icon: <ScrollText />,
      color: 'var(--color-cyan-dark)',
      content: (
        <div className="space-y-4">
          <div className="p-5 rounded-[1.75rem] bg-[var(--color-warm-bg)] border border-[var(--color-soft-border)]">
            <h4 className="text-base font-black text-[var(--color-cyan-dark)] mb-3">遇到异常时可以先检查这几项</h4>
            <div className="space-y-3">
              {[
                '若剧情表现和新设定不一致，先确认当前启用的模组与角色库是否正确。',
                '若 AI 输出偶尔异常，适当降低温度、保持中等 token 会更稳定。',
                '若前端内容未刷新，可回主菜单重新开局，避免旧状态残留。',
              ].map((item, index) => (
                <div key={index} className="flex items-start gap-3">
                  <div className="mt-1.5 w-2 h-2 rounded-full bg-[var(--color-cyan-main)] shrink-0" />
                  <p className="text-sm leading-relaxed text-[var(--color-life-text)]/85">{item}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      ),
    },
  ];

  return <PagedOverlayPanel isOpen={isOpen} onClose={onClose} pages={pages} sectionLabel="系统公告" />;
};
