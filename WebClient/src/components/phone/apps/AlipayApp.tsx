import { ReceiptText, TrendingDown, TrendingUp, Wallet } from 'lucide-react';

interface HistoryEntry {
  turn: number;
  text: string;
  money?: number;
  moneyDelta?: number;
  eventName?: string;
}

interface AlipayAppProps {
  money: number;
  history: HistoryEntry[];
}

export const AlipayApp = ({ money, history }: AlipayAppProps) => {
  const txHistory = history
    .filter((item) => Math.abs(Number(item.moneyDelta || 0)) > 0.001)
    .slice()
    .reverse();

  return (
    <div className="flex-1 flex flex-col bg-slate-50 animate-in slide-in-from-right duration-500 overflow-hidden">
      <div className="bg-gradient-to-r from-sky-500 to-blue-600 px-7 py-8 text-white shrink-0">
        <div className="flex items-center gap-3 mb-7">
          <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-md border border-white/20">
            <Wallet size={24} />
          </div>
          <h3 className="text-xl font-black tracking-tight">支付宝</h3>
        </div>

        <div className="rounded-[1.8rem] bg-white/12 border border-white/15 px-6 py-6 backdrop-blur-md">
          <div className="text-[10px] font-black uppercase tracking-[0.26em] text-white/65">Current Balance</div>
          <div className="mt-2 text-5xl font-black tracking-tighter">¥ {Number(money || 0).toFixed(2)}</div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 pb-28 space-y-3">
        {txHistory.length === 0 ? (
          <div className="rounded-[1.8rem] bg-white border border-slate-200 px-5 py-10 text-center text-slate-400 text-sm font-bold">
            目前还没有资金变动记录。
          </div>
        ) : (
          txHistory.map((item, index) => {
            const delta = Number(item.moneyDelta || 0);
            const income = delta > 0;
            return (
              <div key={`${item.turn}-${index}`} className="rounded-[1.6rem] bg-white border border-cyan-100/80 px-5 py-5 shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">
                    <ReceiptText size={13} /> Turn {item.turn}
                  </div>
                  <div className={`flex items-center gap-1 text-base font-black ${income ? 'text-emerald-500' : 'text-rose-500'}`}>
                    {income ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                    {income ? '+' : ''}{delta.toFixed(2)}
                  </div>
                </div>
                <div className="mt-3 text-base font-black text-slate-800">
                  {item.eventName || '资金变动'}
                </div>
                <div className="mt-2 text-[12px] font-bold text-slate-600 leading-relaxed line-clamp-3">
                  {String(item.text || '').replace(/^【你的选择】:\s*/,'').trim()}
                </div>
                <div className="mt-3 text-[11px] font-black text-slate-400">
                  变动后余额：¥ {Number(item.money || 0).toFixed(2)}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
