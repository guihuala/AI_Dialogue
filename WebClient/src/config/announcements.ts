export type AnnouncementTone = 'cyan' | 'yellow' | 'dark';

export interface AnnouncementCardConfig {
  eyebrow?: string;
  title: string;
  body: string;
  tone?: AnnouncementTone;
}

export interface AnnouncementBulletListConfig {
  title?: string;
  items: string[];
}

export interface AnnouncementPageConfig {
  title: string;
  icon: 'bell' | 'sparkles' | 'scroll';
  color: string;
  introTitle?: string;
  introBody?: string;
  cards?: AnnouncementCardConfig[];
  numberedItems?: string[];
  bulletList?: AnnouncementBulletListConfig;
}

export const announcementPages: AnnouncementPageConfig[] = [
  {
    title: '近期公告',
    icon: 'bell',
    color: 'var(--color-cyan-main)',
    introTitle: '代号：大学档案 ～ AI角色模拟游戏',
    introBody:
      '本项目是一个大语言模型驱动的角色模拟游戏，是为桂花拉糕的毕设。引入 AI 的意义不应该是“我懒得写剧情，交给 AI 吧”，而是借由 LLM 这个新兴工具，把玩法打包成较为成熟的框架，让玩家尝试不同角色在不同世界观下的组合。',
    cards: [
      {
        eyebrow: '项目设想',
        title: '它不该只是“AI 驱动的游戏”',
        body: '简言之，我希望本作不仅是“AI驱动的游戏”，它还应该是一个开放的沙盒，允许玩家修改或添加设定，自定义 prompt、角色、特殊事件，并把这些内容打包成模组发布出去。',
        tone: 'cyan',
      },
      {
        eyebrow: '作者碎碎念',
        title: '代码质量请手下留情',
        body: '此外，由于主播水平比较抱歉，本项目高度依赖 gemini，代码质量不佳，见笑了。请不要拷打我。',
        tone: 'yellow',
      },
    ],
  },
  {
    title: '开发进度',
    icon: 'sparkles',
    color: 'var(--color-yellow-main)',
    numberedItems: [
      '单一 DM 模式已作为主线路径，生成速度与稳定性更适合当前玩法。',
      '主角已从写死角色改为玩家可配置，系统 prompt 会随主角档案动态拼接。',
      '编辑器引导、公告面板、确认框等前端交互正在统一成可复用组件。',
    ],
  },
  {
    title: '游玩建议',
    icon: 'scroll',
    color: 'var(--color-cyan-dark)',
    bulletList: {
      title: '遇到异常时可以先检查这几项',
      items: [
        '若剧情表现和新设定不一致，先确认当前启用的模组与角色库是否正确。',
        '若 AI 输出偶尔异常，适当降低温度、保持中等 token 会更稳定。',
        '若前端内容未刷新，可回主菜单重新开局，避免旧状态残留。',
      ],
    },
  },
];
