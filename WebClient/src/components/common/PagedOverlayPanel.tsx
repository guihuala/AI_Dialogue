import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';

export interface OverlayPage {
  title: string;
  icon: ReactNode;
  content: ReactNode;
  color: string;
}

interface PagedOverlayPanelProps {
  isOpen: boolean;
  onClose: () => void;
  pages: OverlayPage[];
  sectionLabel?: string;
}

export const PagedOverlayPanel = ({
  isOpen,
  onClose,
  pages,
  sectionLabel = '内容面板',
}: PagedOverlayPanelProps) => {
  const [currentPage, setCurrentPage] = useState(0);

  useEffect(() => {
    if (!isOpen) {
      setCurrentPage(0);
    }
  }, [isOpen]);

  if (!isOpen || pages.length === 0) return null;

  const page = pages[currentPage];

  return (
    <div className="fixed inset-0 z-[650] flex items-center justify-center bg-[var(--color-cyan-dark)]/45 backdrop-blur-md p-4 md:p-8">
      <div className="relative bg-white w-[min(92vw,56rem)] h-[min(82vh,46rem)] rounded-[2.75rem] shadow-2xl border border-white overflow-hidden animate-in zoom-in-95 duration-300 flex flex-col">
        <div className="px-8 md:px-10 py-6 md:py-7 flex items-center justify-between border-b border-[var(--color-soft-border)] bg-[var(--color-warm-bg)]/60 shrink-0">
          <div className="flex items-center space-x-4 min-w-0">
            <div
              className="w-14 h-14 rounded-[1.35rem] flex items-center justify-center text-white shadow-md shrink-0"
              style={{ backgroundColor: page.color }}
            >
              {page.icon}
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-black text-[var(--color-cyan-main)]/50 uppercase tracking-[0.35em] mb-1 truncate">
                {sectionLabel}
              </p>
              <h3 className="text-xl md:text-2xl font-black text-[var(--color-cyan-dark)] tracking-tight truncate">
                {page.title}
              </h3>
              <p className="text-[10px] font-black text-[var(--color-life-text)]/40 uppercase tracking-widest mt-1">
                第 {currentPage + 1} 页 / 共 {pages.length} 页
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-11 h-11 rounded-full bg-white flex items-center justify-center text-[var(--color-cyan-main)] hover:bg-[var(--color-cyan-main)] hover:text-white transition-all border border-[var(--color-soft-border)] shrink-0"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-8 md:px-10 py-7 md:py-8 custom-scrollbar bg-white">
          {page.content}
        </div>

        <div className="px-8 md:px-10 py-5 md:py-6 bg-[var(--color-warm-bg)]/60 border-t border-[var(--color-soft-border)] flex items-center justify-between shrink-0">
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
                className={`h-1.5 rounded-full transition-all duration-300 ${i === currentPage ? 'w-8' : 'w-1.5 bg-[var(--color-soft-border)]'}`}
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

        <img
          src="/assets/Q_portraits/anran_portrait.webp"
          alt="公告看板"
          className="pointer-events-none select-none absolute right-3 md:right-5 bottom-[4.75rem] md:bottom-[5.25rem] w-[96px] md:w-[132px] opacity-95 drop-shadow-[0_10px_24px_rgba(20,84,116,0.22)]"
        />
      </div>
    </div>
  );
};
