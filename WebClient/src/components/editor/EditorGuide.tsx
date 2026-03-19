import { useState } from 'react';
import { ChevronLeft, ChevronRight, X, BookOpen, User, Sparkles, Clock } from 'lucide-react';

interface GuidePage {
    title: string;
    icon: React.ReactNode;
    content: React.ReactNode;
    color: string;
}

export const EditorGuide = ({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) => {
    const [currentPage, setCurrentPage] = useState(0);

    const pages: GuidePage[] = [
        {
            title: "模组开发概览",
            icon: <BookOpen />,
            color: "var(--color-cyan-main)",
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
            )
        },
        {
            title: "角色档案管理",
            icon: <User />,
            color: "var(--color-cyan-main)",
            content: (
                <div className="space-y-4">
                    <p className="text-[var(--color-life-text)] leading-relaxed text-sm">
                        在“角色配置”中，您可以管理可选的室友名单。
                    </p>
                    <div className="space-y-3">
                        {[
                            "点击“创建新角色”后，系统会自动为您初始化 .md 设定文件。",
                            "您可以直接上传 WebP/PNG 头像，前端会实时更新渲染。",
                            "点击“设定编辑”进入代码模式，详细描述角色的性格、背景和行为准则。"
                        ].map((text, i) => (
                            <div key={i} className="flex items-start space-x-3">
                                <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[var(--color-cyan-main)] shrink-0" />
                                <p className="text-xs text-[var(--color-life-text)]/80 font-medium">{text}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )
        },
        {
            title: "AI 插件与逻辑 (Skill)",
            icon: <Sparkles />,
            color: "var(--color-yellow-main)",
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
            )
        },
        {
            title: "时间轴与事件",
            icon: <Clock />,
            color: "var(--color-cyan-dark)",
            content: (
                <div className="space-y-4">
                    <p className="text-[var(--color-life-text)] leading-relaxed text-sm">
                        “剧情事件”控制着游戏的节奏。系统将事件库分为：固定剧情、通用随机、角色专属、条件触发。
                    </p>
                    <div className="space-y-2">
                        {[
                            { label: "时间轴可视化", desc: "解析 timeline.json" },
                            { label: "拖拽分发", desc: "调整事件触发优先级" },
                            { label: "CSV 表格编辑", desc: "类似 Excel 的操作体验" }
                        ].map((item, i) => (
                            <div key={i} className="flex justify-between items-center p-3 bg-[var(--color-warm-bg)] rounded-xl border border-[var(--color-soft-border)]">
                                <span className="text-xs font-black text-[var(--color-cyan-dark)]">{item.label}</span>
                                <span className="text-[10px] text-[var(--color-life-text)]/40 font-bold">{item.desc}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )
        }
    ];

    if (!isOpen) return null;

    const page = pages[currentPage];

    return (
        <div className="fixed inset-0 z-[600] flex items-center justify-center bg-[var(--color-cyan-dark)]/40 backdrop-blur-md p-6">
            <div className="bg-white w-full max-w-lg rounded-[2.5rem] shadow-2xl border border-white overflow-hidden animate-in zoom-in-95 duration-300 flex flex-col max-h-[85vh]">
                {/* Header */}
                <div className="px-8 py-6 flex items-center justify-between border-b border-[var(--color-soft-border)] bg-[var(--color-warm-bg)]/50">
                    <div className="flex items-center space-x-4">
                        <div 
                            className="w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-md"
                            style={{ backgroundColor: page.color }}
                        >
                            {page.icon}
                        </div>
                        <div>
                            <h3 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight">{page.title}</h3>
                            <p className="text-[10px] font-black text-[var(--color-life-text)]/40 uppercase tracking-widest mt-1">
                                第 {currentPage + 1} 页 / 共 {pages.length} 页
                            </p>
                        </div>
                    </div>
                    <button 
                        onClick={onClose}
                        className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-[var(--color-cyan-main)] hover:bg-[var(--color-cyan-main)] hover:text-white transition-all border border-[var(--color-soft-border)]"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-8 custom-scrollbar bg-white">
                    {page.content}
                </div>

                {/* Footer */}
                <div className="px-8 py-6 bg-[var(--color-warm-bg)]/50 border-t border-[var(--color-soft-border)] flex items-center justify-between">
                    <button
                        onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
                        disabled={currentPage === 0}
                        className="flex items-center space-x-2 text-xs font-black disabled:opacity-20 text-[var(--color-cyan-dark)] hover:text-[var(--color-cyan-main)] transition-colors"
                    >
                        <ChevronLeft size={16} />
                        <span>上一页</span>
                    </button>

                    <div className="flex space-x-1.5">
                        {pages.map((_, i) => (
                            <div 
                                key={i}
                                className={`h-1.5 rounded-full transition-all duration-300 ${i === currentPage ? 'w-6' : 'w-1.5 bg-[var(--color-soft-border)]'}`}
                                style={{ backgroundColor: i === currentPage ? page.color : undefined }}
                            />
                        ))}
                    </div>

                    <button
                        onClick={() => setCurrentPage(prev => Math.min(pages.length - 1, prev + 1))}
                        disabled={currentPage === pages.length - 1}
                        className="flex items-center space-x-2 text-xs font-black disabled:opacity-20 text-[var(--color-cyan-dark)] hover:text-[var(--color-cyan-main)] transition-colors"
                    >
                        <span>下一页</span>
                        <ChevronRight size={16} />
                    </button>
                </div>
            </div>
        </div>
    );
};
