interface ToastProps {
  message: string;
}

export const Toast = ({ message }: ToastProps) => {
  return (
    <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[10000] bg-black/80 backdrop-blur-xl text-white px-8 py-4 rounded-2xl font-black animate-in zoom-in-90 duration-300 border border-white/20 shadow-2xl">
      {message}
    </div>
  );
};
