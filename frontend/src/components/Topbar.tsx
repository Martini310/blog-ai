export function Topbar() {
  return (
    <header className="h-20 bg-surface-container-lowest/80 backdrop-blur-md flex items-center justify-between px-8 sticky top-0 z-10">
      <div>
        <h2 className="text-sm text-on-surface-variant font-semibold uppercase tracking-wider">Project Alpha</h2>
        <p className="text-xs text-primary mt-1 flex items-center">
          <span className="w-2 h-2 rounded-full bg-primary mr-2 shadow-[0_0_8px_rgba(125,233,255,0.8)]" />
          Active Workspace
        </p>
      </div>
      
      <div className="flex items-center space-x-4">
        <button className="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center text-on-surface hover:bg-surface-container-high transition-colors">
          <span className="material-symbols-outlined text-[20px]">notifications</span>
        </button>
        <div className="flex items-center space-x-3 bg-surface-container px-3 py-1.5 rounded-full border border-surface-container-high/50 cursor-pointer hover:bg-surface-container-high transition-colors">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-on-primary-container font-bold text-sm">
            A
          </div>
          <span className="text-sm font-medium pr-2">Architect</span>
          <span className="material-symbols-outlined text-on-surface-variant text-[18px]">expand_more</span>
        </div>
      </div>
    </header>
  );
}
