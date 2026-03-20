"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { GlassCard } from "@/components/GlassCard";
import { api } from "@/lib/api";

const colorMap: Record<string, string> = {
  primary: "text-primary",
  secondary: "text-secondary",
  tertiary: "text-tertiary",
  error: "text-error",
};

export default function DashboardOverview() {
  const [userName, setUserName] = useState("Architect");
  const [projectCount, setProjectCount] = useState<number | null>(null);
  const [activeProject, setActiveProject] = useState<any>(null);
  const [pipeline, setPipeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [me, projectsRes] = await Promise.all([
          api.auth.me().catch(() => null),
          api.projects.list().catch(() => null),
        ]);
        
        if (me?.full_name) setUserName(me.full_name.split(" ")[0]);
        
        if (projectsRes?.items && projectsRes.items.length > 0) {
          setProjectCount(projectsRes.total);
          const project = projectsRes.items[0];
          setActiveProject(project);

          // Fetch topics and articles for this active project
          const [topics, articles] = await Promise.all([
            api.topics.list(project.id).catch(() => []),
            api.articles.list(project.id).catch(() => [])
          ]);

          const mergedPipeline = [
            ...(topics || []).map((t: any) => ({
              id: t.id,
              title: t.title,
              status: t.status,
              color: t.status === "generating" ? "primary" : "tertiary",
              type: "topic",
              created_at: t.created_at
            })),
            ...(articles || []).map((a: any) => ({
              id: a.id,
              title: a.title || "Untitled Article",
              status: a.status,
              color: a.status === "published" ? "secondary" : "primary",
              type: "article",
              created_at: a.created_at
            }))
          ].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
           .slice(0, 5); // Take most recent 5

          setPipeline(mergedPipeline);
        } else {
          setProjectCount(0);
        }
      } catch (err) {
        console.error("Dashboard data load error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-10">
      <header>
        <h1 className="text-4xl font-display font-medium tracking-tight mb-2">Welcome back, {userName}.</h1>
        <p className="text-on-surface-variant text-lg">
          Your autonomous content engine is currently managing <span className="text-primary font-medium">{projectCount !== null ? projectCount : "..."} active projects</span>.
        </p>
      </header>

      {loading ? (
        <div className="flex justify-center p-12">
          <span className="material-symbols-outlined animate-spin text-primary text-4xl">refresh</span>
        </div>
      ) : activeProject ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <GlassCard className="flex flex-col">
              <div className="flex items-center text-on-surface-variant mb-4">
                <span className="material-symbols-outlined mr-2">psychology</span>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-on-surface">Strategic AI Context</h3>
              </div>
              <p className="text-sm text-on-surface-variant flex-1 leading-relaxed">
                {activeProject.description || "No strategic context provided. Run an analysis to generate it."}
              </p>
              <div className="mt-6 flex items-center justify-between border-t border-surface-container-high/30 pt-4">
                 <span className="text-xs text-on-surface-variant">Project: {activeProject.name}</span>
                 <button className="text-primary text-xs font-medium flex items-center hover:text-primary-container transition-colors">
                   Edit <span className="material-symbols-outlined ml-1 text-[14px]">arrow_forward</span>
                 </button>
              </div>
            </GlassCard>

            <GlassCard className="flex flex-col">
              <div className="flex items-center text-on-surface-variant mb-4">
                <span className="material-symbols-outlined mr-2">calendar_month</span>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-on-surface">Content Schedule</h3>
              </div>
              <div className="flex-1">
                <p className="text-2xl font-display text-on-surface mb-1">Daily</p>
                <p className="text-sm text-on-surface-variant">Active automation process</p>
              </div>
              <div className="mt-6 flex items-center border-t border-surface-container-high/30 pt-4">
                <span className="w-2 h-2 rounded-full bg-secondary mr-2 shadow-[0_0_8px_rgba(221,183,255,0.8)]" />
                <span className="text-sm text-secondary font-medium">Scheduler Online</span>
              </div>
            </GlassCard>

            <GlassCard glow className="bg-gradient-to-br from-surface-container-highest to-surface-container-high relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-10">
                <span className="material-symbols-outlined text-9xl text-primary">bolt</span>
              </div>
              <div className="relative z-10 flex flex-col h-full">
                <h3 className="text-lg font-display text-on-surface mb-2">Generate Next Article</h3>
                <p className="text-sm text-on-surface-variant mb-6 leading-relaxed flex-1">
                  Ready to generate for {activeProject.name} based on queued topics.
                </p>
                <button className="w-full py-3 px-4 bg-primary-container text-on-primary-container rounded-full font-bold text-sm hover:shadow-[0_0_20px_rgba(125,233,255,0.4)] transition-all">
                  Run Generation Now
                </button>
              </div>
            </GlassCard>
          </div>

          <section>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-display font-medium">Content Pipeline ({activeProject.name})</h2>
              <button className="text-sm text-primary font-medium hover:text-primary-container transition-colors">View All</button>
            </div>
            
            {pipeline.length === 0 ? (
               <GlassCard className="text-center py-10">
                 <span className="material-symbols-outlined text-4xl text-on-surface-variant mb-4">queue_play_next</span>
                 <p className="text-sm text-on-surface-variant">No topics or articles found in the pipeline for this project.</p>
               </GlassCard>
            ) : (
              <div className="space-y-4">
                {pipeline.map((item) => (
                  <Link href={`/projects/${activeProject.id}/${item.type}s/${item.id}`} key={item.id} className="block group">
                    <GlassCard className="flex items-center justify-between !p-4 group-hover:bg-surface-container transition-colors cursor-pointer border-none">
                      <div className="flex items-center space-x-4">
                        <div className={`w-10 h-10 rounded-full bg-surface-container flex items-center justify-center ${colorMap[item.color] || "text-on-surface"}`}>
                          <span className="material-symbols-outlined text-[20px]">
                            {item.type === "article" ? "article" : item.status === "generating" ? "memory" : "queue_play_next"}
                          </span>
                        </div>
                        <div>
                          <h4 className="font-medium text-on-surface mb-1 group-hover:text-primary transition-colors">{item.title}</h4>
                          <div className="flex items-center">
                            <span className={`uppercase text-[10px] tracking-wider font-bold px-2 py-0.5 rounded-sm mr-3 bg-surface-container/50 ${colorMap[item.color] || "text-on-surface-variant"}`}>
                              {item.status} ({item.type})
                            </span>
                            <span className="text-xs text-on-surface-variant">{new Date(item.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>
                      <button className="w-8 h-8 rounded-full hover:bg-surface-container-low flex items-center justify-center text-on-surface-variant transition-colors border-none group-hover:translate-x-1">
                        <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
                      </button>
                    </GlassCard>
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      ) : (
         <GlassCard className="text-center py-16">
           <span className="material-symbols-outlined text-4xl text-on-surface-variant mb-4">dashboard</span>
           <h3 className="text-lg font-medium text-on-surface mb-2">No projects active</h3>
           <p className="text-sm text-on-surface-variant mb-6">Create a new project to see your AI content pipeline.</p>
         </GlassCard>
      )}
    </div>
  );
}
