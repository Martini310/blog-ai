import Link from "next/link";
import { ReactNode } from "react";

const navItems = [
  { name: "Dashboard", href: "/", icon: "dashboard" },
  { name: "Projects", href: "/projects", icon: "folder_open" },
  { name: "Content Schedule", href: "/schedule", icon: "calendar_month" },
  { name: "Topics Queue", href: "/topics", icon: "queue_play_next" },
  { name: "Generated Articles", href: "/articles", icon: "article" },
];

export function Sidebar() {
  return (
    <aside className="w-64 bg-surface-container-lowest h-screen fixed left-0 top-0 flex flex-col pt-8 pb-4">
      <div className="px-6 mb-10">
        <h1 className="text-xl font-display font-medium text-on-surface tracking-tight">
          Luminescent <span className="text-primary">AI</span>
        </h1>
      </div>
      
      <nav className="flex-1 space-y-2">
        {navItems.map((item) => {
          // Hardware a simplistic active state for the dashboard specifically
          const isActive = item.name === "Dashboard"; 
          
          return (
            <Link 
              key={item.name} 
              href={item.href}
              className={`flex items-center px-6 py-3 relative transition-colors ${
                isActive 
                  ? "text-primary" 
                  : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low"
              }`}
            >
              {isActive && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary drop-shadow-[0_0_8px_rgba(125,233,255,0.8)]" />
              )}
              {/* Note: In a real app we'd use icon libraries like lucide-react, using simple text placeholders here */}
              <span className="material-symbols-outlined mr-3 text-[20px]">{item.icon}</span>
              <span className="text-sm font-medium">{item.name}</span>
            </Link>
          );
        })}
      </nav>
      
      <div className="px-6">
        <Link 
          href="/settings"
          className="flex items-center py-3 text-on-surface-variant hover:text-on-surface transition-colors"
        >
          <span className="material-symbols-outlined mr-3 text-[20px]">settings</span>
          <span className="text-sm font-medium">Settings</span>
        </Link>
      </div>
    </aside>
  );
}
