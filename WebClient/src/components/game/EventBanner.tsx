interface EventBannerProps {
  title: string;
  visible: boolean;
}

export const EventBanner = ({ title, visible }: EventBannerProps) => {
  const trimmedTitle = String(title || '').trim();
  if (!trimmedTitle) return null;

  return (
    <div
      className={`absolute left-1/2 top-[18%] z-30 -translate-x-1/2 pointer-events-none transition-all duration-500 ${
        visible ? 'opacity-100 scale-100' : 'opacity-0 scale-95'
      }`}
    >
      <div className="min-w-[300px] max-w-[70vw] rounded-[2rem] border border-[var(--color-cyan-main)]/20 bg-[var(--color-cyan-light)]/92 px-8 py-4 text-center shadow-[0_18px_45px_rgba(0,188,212,0.18)] backdrop-blur-md">
        <div className="flex items-center justify-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-[var(--color-yellow-main)] shadow-[0_0_10px_var(--color-yellow-main)]" />
          <span className="text-[10px] font-black uppercase tracking-[0.35em] text-[var(--color-cyan-main)]/70">Event</span>
          <span className="h-2.5 w-2.5 rounded-full bg-[var(--color-yellow-main)] shadow-[0_0_10px_var(--color-yellow-main)]" />
        </div>
        <div className="mt-2 text-2xl font-black tracking-wide text-[var(--color-cyan-dark)] md:text-3xl">{trimmedTitle}</div>
      </div>
    </div>
  );
};
