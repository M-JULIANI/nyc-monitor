// Minimal Spinner Component
export default function Spinner(){
    return (
    <div className="absolute inset-0 flex items-center justify-center z-30">
      <div className="relative">
        <div className="w-12 h-12 border-4 border-zinc-600 border-t-white rounded-full animate-spin"></div>
        <div className="mt-4 text-white text-sm text-center">Connecting...</div>
      </div>
    </div>
  );
}