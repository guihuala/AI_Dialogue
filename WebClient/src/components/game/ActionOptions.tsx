interface ActionOptionsProps {
  options: string[];
  onSelect: (option: string) => void;
  onHover?: (option: string) => void;
  disabled: boolean;
}

const decodeOptionLabel = (raw: string): { title: string; badge: string | null; tooltip?: string } => {
  const text = String(raw || '').trim();
  const m = text.match(/^【关键事件:([^:：\]】]+):([^】\]]+)】\s*(.*)$/);
  if (!m) {
    return { title: text, badge: null as string | null };
  }
  const eventId = String(m[1] || '').trim();
  const choiceId = String(m[2] || '').trim();
  const tail = String(m[3] || '').trim();

  // tail usually like: "寝室临时决策 - 支持（不可逆）"
  // If tail is empty, fallback to choice id for readability.
  const prettyTail = tail || `关键事件选项（${choiceId}）`;
  // internal id may still be useful in debug hover, but not in primary text
  return {
    title: prettyTail,
    badge: '关键事件',
    tooltip: `event=${eventId}, choice=${choiceId}`,
  };
};

export const ActionOptions = ({ options, onSelect, onHover, disabled }: ActionOptionsProps) => {
  if (options.length === 0) return null;

  return (
    <div className="absolute left-10 bottom-[28vh] w-96 flex flex-col space-y-4 pointer-events-auto z-30">
      {options.map((opt, idx) => {
        const decoded = decodeOptionLabel(opt);
        return (
          <button
            key={idx}
            disabled={disabled}
            onClick={() => onSelect(opt)}
            onMouseEnter={() => !disabled && onHover && onHover(opt)}
            title={decoded.tooltip || ''}
            className="p-4 bg-white/95 backdrop-blur-xl border-2 border-[var(--color-cyan-main)]/30 rounded-2xl shadow-2xl hover:border-[var(--color-yellow-main)] hover:bg-white hover:-translate-x-2 transition-all duration-300 disabled:opacity-50 font-black text-[var(--color-cyan-dark)] flex items-center group relative overflow-hidden text-left active:scale-95"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-cyan-light)]/0 via-[var(--color-cyan-light)]/50 to-[var(--color-cyan-light)]/0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
            <div className="w-10 h-10 rounded-xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] flex items-center justify-center text-sm font-black mr-4 group-hover:bg-[var(--color-yellow-main)] transition-all shrink-0 border border-[var(--color-cyan-main)]/20 shadow-sm">
              {String.fromCharCode(65 + idx)}
            </div>
            <div className="leading-snug text-sm relative z-10 min-w-0">
              {decoded.badge && (
                <div className="text-[10px] font-black tracking-wider uppercase text-amber-600 mb-0.5">
                  {decoded.badge}
                </div>
              )}
              <span>{decoded.title}</span>
            </div>
          </button>
        );
      })}
    </div>
  );
};
