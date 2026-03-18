import { Wallet, Smartphone, History, PiggyBank, ReceiptText, ChevronRight } from 'lucide-react';

interface AlipayAppProps {
  money: number;
  history: any[];
}

export const AlipayApp = ({ money, history }: AlipayAppProps) => {
  // Try to find any money-related entries in the text or choice
  const txHistory = history.slice(-8).reverse().map((h, i) => {
    const isIncome = h.text.toLowerCase().includes('earned') || h.text.includes('赚') || h.text.includes('获得');
    const isExpense = h.text.includes('spent') || h.text.includes('花费') || h.text.includes('买');
    const amountMatch = h.text.match(/¥(\d+)/) || h.text.match(/(\d+)元/);
    const amount = amountMatch ? amountMatch[1] : (isIncome ? '+120.00' : (isExpense ? '-45.00' : '0.00'));
    
    return {
      turn: h.turn,
      text: h.text.split('】: ')[1] || '日用消费',
      amount: amount,
      isIncome: isIncome && !isExpense, // Simple heuristic
      time: '今日 10:05'
    };
  });

  return (
    <div className="flex-1 flex flex-col bg-slate-50 animate-in slide-in-from-right duration-500 overflow-hidden">
      <div className="bg-[#1677FF] px-8 py-10 text-white shrink-0">
        <div className="flex items-center gap-3 mb-8">
           <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-md border border-white/20"><Wallet size={24}/></div>
           <h3 className="text-xl font-black tracking-tight">支付宝 / Alipay</h3>
        </div>
        
        <div className="bg-white/10 backdrop-blur-md rounded-[2.5rem] p-8 border border-white/10 shadow-2xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -mr-10 -mt-10 blur-2xl group-hover:scale-150 transition-transform duration-1000" />
          <div className="relative z-10 flex flex-col items-center">
            <span className="text-[10px] font-black tracking-[0.4em] uppercase mb-4 opacity-60">My Balance (CNY)</span>
            <div className="text-5xl font-black mb-2 tracking-tighter">¥ {money.toLocaleString()}</div>
            <div className="text-[10px] font-black bg-white/20 px-3 py-1 rounded-full border border-white/20 uppercase tracking-widest mt-4">已启用智能安保系统</div>
          </div>
        </div>
      </div>
      
      <div className="flex-1 p-6 overflow-y-auto custom-scrollbar pb-32">
        <div className="grid grid-cols-2 gap-4 mb-8">
           <button className="bg-white p-5 rounded-3xl flex flex-col items-center gap-2 border border-slate-100 shadow-sm active:scale-95 transition-all">
              <div className="w-10 h-10 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center"><Smartphone size={20}/></div>
              <span className="text-[11px] font-black text-slate-700">扫码付</span>
           </button>
           <button className="bg-white p-5 rounded-3xl flex flex-col items-center gap-2 border border-slate-100 shadow-sm active:scale-95 transition-all">
              <div className="w-10 h-10 bg-orange-50 text-orange-500 rounded-full flex items-center justify-center"><PiggyBank size={20}/></div>
              <span className="text-[11px] font-black text-slate-700">收钱</span>
           </button>
        </div>

        <div className="bg-white rounded-[2.5rem] shadow-sm border border-slate-100 overflow-hidden">
          <div className="px-8 py-5 flex justify-between items-center border-b border-slate-50">
             <div className="flex items-center gap-2">
                <History size={18} className="text-slate-400" />
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Transaction History</span>
             </div>
             <ChevronRight size={16} className="text-slate-300" />
          </div>

          <div className="divide-y divide-gray-50">
            {txHistory.map((tx, i) => (
               <div key={i} className="px-8 py-5 flex items-center gap-4 hover:bg-slate-50 transition-colors">
                  <div className="w-12 h-12 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-400 shrink-0"><ReceiptText size={24}/></div>
                  <div className="flex-1 min-w-0">
                     <div className="flex justify-between items-baseline">
                        <span className="text-sm font-black text-slate-800 truncate pr-2">{tx.text}</span>
                        <span className={`text-md font-black tabular-nums ${tx.isIncome ? 'text-emerald-500' : 'text-slate-800'}`}>
                           {tx.isIncome ? '+' : '-'}{tx.amount}
                        </span>
                     </div>
                     <span className="text-[9px] text-slate-400 mt-1 uppercase font-black">{tx.time} • Turn {tx.turn}</span>
                  </div>
               </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
