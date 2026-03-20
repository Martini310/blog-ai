import { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  glow?: boolean;
}

export function GlassCard({ children, className = "", glow = false }: GlassCardProps) {
  return (
    <div className={`glass-panel rounded-xl p-6 ${glow ? "glass-border-glow" : ""} ${className}`}>
      {children}
    </div>
  );
}
