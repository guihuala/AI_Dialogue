import { 
    Book, 
    Compass, 
    Cpu, 
    MessageSquare, 
    Smartphone, 
    TowerControl as Control, 
    ChevronRight,
    Search,
    Plus,
    Sparkles
} from 'lucide-react';
import { useState, useMemo } from 'react';
import type { ReactNode } from 'react';

interface Topic {
    id: string;
    title: string;
    description: string;
    icon: any;
    fileName: string;
    color: string;
}

interface TopicExplorerProps {
    category: 'world' | 'skills';
    files: string[];
    onSelectTopic: (fileName: string) => void;
    onAddNew?: () => void;
    canEdit?: boolean;
    headerAddon?: ReactNode;
    hideHeader?: boolean;
    searchTerm?: string;
    onSearchTermChange?: (value: string) => void;
}

export const TopicExplorer = ({
    category,
    files,
    onSelectTopic,
    onAddNew,
    canEdit = true,
    headerAddon,
    hideHeader = false,
    searchTerm: controlledSearchTerm,
    onSearchTermChange,
}: TopicExplorerProps) => {
    const [internalSearchTerm, setInternalSearchTerm] = useState('');
    const searchTerm = controlledSearchTerm ?? internalSearchTerm;
    const setSearchTerm = onSearchTermChange ?? setInternalSearchTerm;

    const worldTopics: Topic[] = [
        { 
            id: 'base', 
            title: '基础世界设定', 
            description: '游戏的核心背景、时间线以及基本运行规则。', 
            icon: Compass, 
            fileName: 'world/base_setting.md',
            color: 'bg-[var(--color-cyan-dark)]'
        },
        { 
            id: 'city', 
            title: '城市与校区环境', 
            description: '故事发生地的地理布局、热门打卡点及环境细节。', 
            icon: Control, 
            fileName: 'world/city_setting.md',
            color: 'bg-[var(--color-cyan-main)]'
        },
        { 
            id: 'major', 
            title: '专业与学术背景', 
            description: '学科特色、课程压力以及校园内的学术竞争氛围。', 
            icon: Book, 
            fileName: 'world/major_setting.md',
            color: 'bg-[var(--color-yellow-main)]'
        },
        { 
            id: 'npcs', 
            title: '校园人物志', 
            description: '非常驻公共 NPC 的性格模版与社交关系网。', 
            icon: MessageSquare, 
            fileName: 'world/academic_npcs.md',
            color: 'bg-[var(--color-cyan-light)]'
        },
        {
            id: 'scenes',
            title: '场景与背景图谱',
            description: '配置场景名称、关键词与背景图片映射（支持自定义 URL）。',
            icon: Sparkles,
            fileName: 'world/scenes.json',
            color: 'bg-[var(--color-cyan-main)]'
        }
    ];

    const systemTopics: Topic[] = [
        { 
            id: 'exp_system', 
            title: '短输出系统提示词', 
            description: 'expression-only 的系统层提示词，控制整体文风与输出边界。', 
            icon: Cpu, 
            fileName: 'system/expression_system_prompt.md',
            color: 'bg-[var(--color-cyan-dark)]'
        },
        { 
            id: 'exp_user', 
            title: '短输出用户模板', 
            description: '每回合输入模板，决定事件上下文如何喂给模型。', 
            icon: MessageSquare, 
            fileName: 'system/expression_user_prompt.md',
            color: 'bg-[var(--color-cyan-main)]'
        },
        { 
            id: 'exp_contract', 
            title: '短输出 JSON 协议', 
            description: '约束返回字段与格式，保证前端稳定解析。', 
            icon: Book, 
            fileName: 'system/expression_json_contract.md',
            color: 'bg-[var(--color-yellow-main)]'
        },
        { 
            id: 'wechat', 
            title: '社交网络协议', 
            description: '手机社交文案与风格模板（消息触发已优先走 phone_enqueue_message 工具）。', 
            icon: Smartphone, 
            fileName: 'skills/wechat_monitor.md',
            color: 'bg-[var(--color-cyan-main)]'
        },
        { 
            id: 'slang1', 
            title: '大一语境指南', 
            description: '针对大学第一学年的俚语、黑话以及特定的社交梗。', 
            icon: MessageSquare, 
            fileName: 'skills/slang_chapter_1.md',
            color: 'bg-[var(--color-yellow-main)]'
        },
        { 
            id: 'slang2', 
            title: '大二语境指南', 
            description: '大二阶段进阶的社交词汇、圈子黑话与情感表达风格。', 
            icon: MessageSquare, 
            fileName: 'skills/slang_chapter_2.md',
            color: 'bg-[var(--color-yellow-light)]'
        },
        { 
            id: 'slang3', 
            title: '大三语境指南', 
            description: '涉及实习、抉择以及更深层社会化沟通的表达规范。', 
            icon: MessageSquare, 
            fileName: 'skills/slang_chapter_3.md',
            color: 'bg-[var(--color-cyan-light)]'
        },
        { 
            id: 'slang4', 
            title: '大四语境指南', 
            description: '考研、求职、离别等复杂情感交织下的最终话术逻辑。', 
            icon: MessageSquare, 
            fileName: 'skills/slang_chapter_4.md',
            color: 'bg-[var(--color-life-text)]/20'
        }
    ];

    const allTopics = useMemo(() => {
        const base = category === 'world' ? worldTopics : systemTopics;
        
        // Find dynamic skills not in the base list
        const dynamicSkills: Topic[] = files
            .filter(f => f.startsWith('skills/') && !base.some(b => b.fileName === f) && !f.includes('slang_chapter'))
            .map(f => ({
                id: f,
                title: f.split('/').pop()?.replace('.md', '') || '自定义技能',
                description: '玩家自定义的 AI 系统插件，已自动挂载至游戏逻辑中枢。',
                icon: Sparkles,
                fileName: f,
                color: 'bg-[var(--color-cyan-main)]'
            }));
            
        return [...base, ...dynamicSkills];
    }, [category, files]);

    const filteredTopics = useMemo(() => {
        return allTopics.filter(topic => 
            (topic.title.includes(searchTerm) || topic.description.includes(searchTerm)) &&
            files.some(f => f.includes(topic.fileName))
        );
    }, [allTopics, searchTerm, files]);

    return (
        <div className="flex-1 flex flex-col overflow-hidden bg-[var(--color-warm-bg)]">
            {!hideHeader && <div className="px-7 py-6 flex flex-col lg:flex-row lg:items-center justify-between gap-4 shrink-0 bg-white border-b border-[var(--color-soft-border)]">
                <div className="space-y-1.5 text-left">
                    <h4 className="text-[2rem] leading-none font-black text-[var(--color-cyan-dark)] tracking-tight">
                        {category === 'world' ? '世界设定档案库' : '核心系统逻辑'}
                    </h4>
                    <p className="text-sm font-bold text-[var(--color-cyan-dark)]/45">
                        {category === 'world' ? '构建故事基石，定义环境、历史与社会关系' : '配置 AI 运行底座，优化回复逻辑与系统交互'}
                    </p>
                </div>
                
                <div className="flex flex-wrap items-center gap-3">
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-cyan-main)]/30" size={18} />
                        <input 
                            type="text"
                            placeholder="搜索档案内容..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="h-11 w-[20rem] max-w-full pl-12 pr-5 bg-[var(--color-cyan-light)]/22 rounded-2xl border border-[var(--color-cyan-main)]/12 text-sm font-bold outline-none focus:border-[var(--color-cyan-main)]/35 focus:bg-white transition-all shadow-inner text-[var(--color-cyan-dark)]"
                        />
                    </div>
                </div>
            </div>}
            {headerAddon && !hideHeader && (
                <div className="px-7 py-3 bg-white border-b border-[var(--color-soft-border)]">
                    {headerAddon}
                </div>
            )}

            <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                    {filteredTopics.map((topic) => {
                        const isLight = topic.color.includes('light') || topic.color.includes('/20');
                        return (
                            <button
                                key={topic.id}
                                onClick={() => onSelectTopic(topic.fileName)}
                                className="bg-white rounded-[2rem] p-6 border border-[var(--color-soft-border)] shadow-sm hover:shadow-lg hover:border-[var(--color-cyan-main)]/20 transition-all group text-left relative overflow-hidden min-h-[260px]"
                            >
                                <topic.icon className="absolute -right-6 -bottom-6 w-28 h-28 text-[var(--color-cyan-light)]/18 group-hover:text-[var(--color-cyan-light)]/30 transition-colors opacity-70" />

                                <div className="relative z-10 flex flex-col h-full text-left">
                                    <div className={`w-14 h-14 rounded-2xl ${topic.color} ${isLight ? 'text-[var(--color-cyan-dark)]' : 'text-white'} flex items-center justify-center mb-5 shadow-md transition-transform`}>
                                        <topic.icon size={26} />
                                    </div>
                                    <h5 className="text-[28px] leading-none font-black text-[var(--color-cyan-dark)] mb-3 tracking-tight">{topic.title}</h5>
                                    <p className="text-sm font-bold text-[var(--color-life-text)]/55 leading-relaxed mb-auto line-clamp-3">{topic.description}</p>
                                    
                                    <div className="mt-6 flex items-center justify-between border-t border-[var(--color-soft-border)] pt-4">
                                        <span className="text-[11px] font-black text-[var(--color-cyan-main)]/75">进入编辑</span>
                                        <div className="w-9 h-9 rounded-full bg-[var(--color-cyan-light)]/75 flex items-center justify-center text-[var(--color-cyan-main)] group-hover:bg-[var(--color-cyan-main)] group-hover:text-white transition-all">
                                            <ChevronRight size={18} />
                                        </div>
                                    </div>
                                </div>
                            </button>
                        );
                    })}

                    {/* Add New Skill Button Card */}
                    {category === 'skills' && !searchTerm && onAddNew && (
                        <button
                            onClick={onAddNew}
                            disabled={!canEdit}
                            className="bg-white/40 rounded-[2rem] p-8 border-2 border-dashed border-[var(--color-soft-border)] hover:border-[var(--color-cyan-main)]/30 hover:bg-white transition-all group text-left flex flex-col items-center justify-center text-[var(--color-cyan-main)]/30 hover:text-[var(--color-cyan-main)] min-h-[260px]"
                        >
                            <div className="w-16 h-16 rounded-full bg-[var(--color-cyan-light)] group-hover:bg-[var(--color-cyan-main)] group-hover:text-white flex items-center justify-center mb-4 transition-colors">
                                <Plus size={32} />
                            </div>
                            <span className="text-sm font-black uppercase tracking-[0.2em]">{canEdit ? '编写自定义 SKILL' : '默认模板只读'}</span>
                            <span className="text-[10px] font-bold text-[var(--color-life-text)]/40 mt-2 uppercase">{canEdit ? '动态装载 AI 插件' : '请先另存为你的模组'}</span>
                        </button>
                    )}
                    
                    {filteredTopics.length === 0 && (
                        <div className="col-span-full py-32 flex flex-col items-center justify-center opacity-20 bg-white/50 rounded-[2rem] border-2 border-dashed border-[var(--color-soft-border)]">
                             <Search size={64} className="mb-6 text-[var(--color-cyan-main)]" />
                             <p className="text-lg font-black tracking-[0.2em] text-[var(--color-cyan-dark)]">未找到相关档案</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
