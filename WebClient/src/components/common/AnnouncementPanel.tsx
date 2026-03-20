import { Bell, ScrollText, Sparkles } from 'lucide-react';
import { announcementPages } from '../../config/announcements';
import { PagedOverlayPanel } from './PagedOverlayPanel';
import type { OverlayPage } from './PagedOverlayPanel';

const iconMap = {
  bell: <Bell />,
  sparkles: <Sparkles />,
  scroll: <ScrollText />,
};

const toneCardClassMap = {
  cyan: 'bg-[var(--color-cyan-light)] border-[var(--color-cyan-main)]/20',
  yellow: 'bg-[var(--color-yellow-light)] border-[var(--color-yellow-main)]/20',
  dark: 'bg-[var(--color-warm-bg)] border-[var(--color-soft-border)]',
};

export const AnnouncementPanel = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  const pages: OverlayPage[] = announcementPages.map(page => ({
    title: page.title,
    icon: iconMap[page.icon],
    color: page.color,
    content: (
      <div className="space-y-5">
        {(page.introTitle || page.introBody) && (
          <div className="p-5 rounded-[1.75rem] bg-[var(--color-cyan-light)] border border-[var(--color-cyan-main)]/20">
            <p className="text-[10px] font-black uppercase tracking-[0.35em] text-[var(--color-cyan-main)]/60 mb-2">Announcement</p>
            {page.introTitle && <h4 className="text-xl font-black text-[var(--color-cyan-dark)] mb-3">{page.introTitle}</h4>}
            {page.introBody && <p className="text-sm leading-relaxed text-[var(--color-life-text)]">{page.introBody}</p>}
          </div>
        )}

        {page.cards && page.cards.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {page.cards.map((card, index) => (
              <div
                key={`${page.title}-card-${index}`}
                className={`p-4 rounded-2xl border ${toneCardClassMap[card.tone || 'dark']}`}
              >
                {card.eyebrow && (
                  <p className="text-[10px] font-black uppercase tracking-[0.25em] text-[var(--color-cyan-main)]/50 mb-2">
                    {card.eyebrow}
                  </p>
                )}
                <h4 className="text-sm font-black text-[var(--color-cyan-dark)] mb-2">{card.title}</h4>
                <p className="text-xs text-[var(--color-life-text)]/80 font-medium leading-relaxed">{card.body}</p>
              </div>
            ))}
          </div>
        )}

        {page.numberedItems && page.numberedItems.length > 0 && (
          <div className="space-y-4">
            {page.numberedItems.map((item, index) => (
              <div
                key={`${page.title}-item-${index}`}
                className="flex items-start gap-3 p-4 rounded-2xl bg-[var(--color-warm-bg)] border border-[var(--color-soft-border)]"
              >
                <div className="w-7 h-7 rounded-full bg-[var(--color-yellow-main)] text-white flex items-center justify-center text-[11px] font-black shrink-0">
                  {index + 1}
                </div>
                <p className="text-sm leading-relaxed text-[var(--color-life-text)]/85 font-medium">{item}</p>
              </div>
            ))}
          </div>
        )}

        {page.bulletList && (
          <div className="p-5 rounded-[1.75rem] bg-[var(--color-warm-bg)] border border-[var(--color-soft-border)]">
            {page.bulletList.title && (
              <h4 className="text-base font-black text-[var(--color-cyan-dark)] mb-3">{page.bulletList.title}</h4>
            )}
            <div className="space-y-3">
              {page.bulletList.items.map((item, index) => (
                <div key={`${page.title}-bullet-${index}`} className="flex items-start gap-3">
                  <div className="mt-1.5 w-2 h-2 rounded-full bg-[var(--color-cyan-main)] shrink-0" />
                  <p className="text-sm leading-relaxed text-[var(--color-life-text)]/85">{item}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    ),
  }));

  return <PagedOverlayPanel isOpen={isOpen} onClose={onClose} pages={pages} sectionLabel="系统公告" />;
};
