import { MessageCircle, Calendar, GraduationCap, Wallet, Brain } from 'lucide-react';

interface AppIconProps {
  id: string;
  name: string;
  icon: any;
  color: string;
  notifications?: number;
  onClick: (id: string) => void;
}

const AppIcon = ({ id, name, icon, color, notifications, onClick }: AppIconProps) => (
  <div 
    onClick={() => onClick(id)}
    className="flex flex-col items-center gap-2 group cursor-pointer transition-all active:scale-95"
  >
    <div className={`w-[60px] h-[60px] rounded-[1.2rem] ${color} flex items-center justify-center text-white relative transition-all duration-300 group-active:translate-y-0.5`}>
      <div className="relative z-10">
        {icon}
      </div>
      
      {notifications !== undefined && notifications > 0 && (
        <div className="absolute -top-1.5 -right-1.5 min-w-[20px] h-5 bg-rose-500 rounded-full border-2 border-white flex items-center justify-center text-[10px] font-bold text-white px-1">
          {notifications}
        </div>
      )}
    </div>
    <span className="text-[10px] font-bold text-slate-800 tracking-tight">{name}</span>
  </div>
);

interface HomeViewProps {
  onAppClick: (id: string) => void;
  wechatNotificationsCount: number;
}

export const HomeView = ({ onAppClick, wechatNotificationsCount }: HomeViewProps) => {
  return (
    <div className="flex-1 flex flex-col p-8 pt-20 animate-in fade-in duration-500">
      <div className="mb-10 px-4">
        <div className="text-slate-400 text-[10px] font-bold tracking-[0.2em] uppercase mb-1">Dorm OS</div>
        <div className="text-slate-800 text-3xl font-black tracking-tighter">你好，安然</div>
      </div>

      <div className="grid grid-cols-4 gap-y-8 gap-x-4 justify-items-center bg-white/40 backdrop-blur-md rounded-[2.5rem] p-6 border border-white/40">
        <AppIcon 
          id="wechat" 
          name="微信" 
          icon={<MessageCircle size={30} fill="white" fillOpacity={0.2} />} 
          color="bg-[#07C160]" 
          notifications={wechatNotificationsCount}
          onClick={onAppClick} 
        />
        <AppIcon 
          id="calendar" 
          name="行程" 
          icon={<Calendar size={30} />} 
          color="bg-[#FF9500]" 
          onClick={onAppClick} 
        />
        <AppIcon 
          id="jmu" 
          name="学工" 
          icon={<GraduationCap size={30} />} 
          color="bg-[#004b97]" 
          onClick={onAppClick} 
        />
        <AppIcon 
          id="alipay" 
          name="支付宝" 
          icon={<Wallet size={30} />} 
          color="bg-[#1677FF]" 
          onClick={onAppClick} 
        />
        <AppIcon 
          id="wellness" 
          name="心理" 
          icon={<Brain size={30} />} 
          color="bg-[#5856D6]" 
          onClick={onAppClick} 
        />
      </div>
      
      {/* Search / Dock area placeholder if needed later */}
    </div>
  );
};
