import { Layers, Cloud } from 'lucide-react';

interface ModPackSelectorProps {
  workshopPacks: any[];
  selectedMod: string;
  setSelectedMod: (id: string) => void;
  onTabChange: (tab: any) => void;
}

export const ModPackSelector = ({
  workshopPacks,
  selectedMod,
  setSelectedMod,
  onTabChange
}: ModPackSelectorProps) => {
  return (
    <div className="w-full md:w-80 bg-white/60 border-r border-dashed border-[var(--color-cyan-main)]/20 p-6 flex flex-col shrink-0 overflow-y-auto custom-scrollbar">
      <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] mb-6 flex items-center tracking-[0.2em] uppercase">
        <Layers size={14} className="mr-2" /> 设定模组
      </h3>
      <div className="space-y-3 flex-1">
        <div
          onClick={() => setSelectedMod('default')}
          className={`p-4 rounded-xl cursor-pointer border-2 transition-all relative overflow-hidden group ${selectedMod === 'default' ? 'bg-[var(--color-cyan-dark)] border-[var(--color-cyan-dark)] text-white shadow-lg' : 'bg-white/80 border-[var(--color-cyan-main)]/10 text-gray-600 hover:border-[var(--color-cyan-main)]'}`}
        >
          {selectedMod === 'default' && <div className="absolute top-0 right-0 w-8 h-8 bg-[var(--color-yellow-main)] flex items-center justify-center -rotate-45 translate-x-4 -translate-y-4 shadow-md text-black font-bold">✓</div>}
          <h4 className="font-black text-sm">默认设定</h4>
          <p className="text-[9px] mt-1 opacity-60 font-bold uppercase tracking-tighter">Current Physical Files</p>
        </div>

        {workshopPacks.map(pkg => (
          <div
            key={pkg.id}
            onClick={() => setSelectedMod(pkg.id)}
            className={`p-4 rounded-xl cursor-pointer border-2 transition-all relative overflow-hidden group ${selectedMod === pkg.id ? 'bg-[var(--color-cyan-dark)] border-[var(--color-cyan-dark)] text-white shadow-lg' : 'bg-white/80 border-[var(--color-cyan-main)]/10 text-gray-600 hover:border-[var(--color-cyan-main)]'}`}
          >
            {selectedMod === pkg.id && <div className="absolute top-0 right-0 w-8 h-8 bg-[var(--color-yellow-main)] flex items-center justify-center -rotate-45 translate-x-4 -translate-y-4 shadow-md text-black font-bold">✓</div>}
            <h4 className="font-black text-sm truncate">{pkg.name}</h4>
            <p className="text-[9px] mt-1 opacity-60 font-bold uppercase tracking-tighter">Author: {pkg.author}</p>
          </div>
        ))}
      </div>

      <button
        onClick={() => onTabChange('workshop')}
        className="mt-6 flex items-center justify-center p-4 bg-white/60 border-2 border-dashed border-[var(--color-cyan-main)]/30 text-[var(--color-cyan-main)] rounded-xl hover:bg-[var(--color-cyan-main)] hover:text-white transition-all text-[9px] font-black uppercase tracking-widest"
      >
        <Cloud size={14} className="mr-2" /> 发现更多模组
      </button>
    </div>
  );
};
