"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { GlassCard } from "@/components/GlassCard";
import { api } from "@/lib/api";

export default function Projects() {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchProjects() {
      try {
        const res = await api.projects.list();
        if (res?.items) {
          setProjects(res.items);
        }
      } catch (err) {
        console.error("Error fetching projects", err);
      } finally {
        setLoading(false);
      }
    }
    fetchProjects();
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-4xl font-display font-medium tracking-tight border-none">Projects</h1>
        <Link href="/projects/new">
          <button className="py-2.5 px-6 bg-primary-container text-on-primary-container rounded-full font-bold text-sm hover:shadow-[0_0_20px_rgba(125,233,255,0.4)] transition-all flex items-center border-none">
            <span className="material-symbols-outlined mr-2 text-[20px]">add</span>
            New Project
          </button>
        </Link>
      </div>
      
      {loading ? (
        <div className="flex justify-center p-12">
          <span className="material-symbols-outlined animate-spin text-primary text-4xl">refresh</span>
        </div>
      ) : projects.length === 0 ? (
        <GlassCard className="text-center py-16">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant mb-4">folder_open</span>
          <h3 className="text-lg font-medium text-on-surface mb-2">No projects yet</h3>
          <p className="text-sm text-on-surface-variant mb-6">Create your first project to start automating content.</p>
        </GlassCard>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project, i) => (
            <Link href={`/projects/${project.id}`} key={project.id || i} className="block group">
              <GlassCard className="flex flex-col h-full cursor-pointer hover:bg-surface-container transition-colors border-none">
                <div className="flex justify-between items-start mb-6 border-none">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-surface-container-high to-surface-container-highest flex items-center justify-center border-none shadow-inner group-hover:shadow-[0_0_15px_rgba(125,233,255,0.1)] transition-shadow">
                     <span className="material-symbols-outlined text-primary text-[24px]">folder_open</span>
                  </div>
                  <span className={`uppercase text-[10px] tracking-wider font-bold px-2 py-0.5 rounded-sm border-none bg-surface-container/50 ${project.status === "active" ? "text-primary" : "text-on-surface-variant"}`}>
                    {project.status || "Active"}
                  </span>
                </div>
                <h3 className="text-xl font-display text-on-surface mb-2 border-none group-hover:text-primary transition-colors">{project.name}</h3>
                <div className="text-sm text-on-surface-variant mb-6 flex-1 border-none line-clamp-2">
                  {project.description || "No description provided."}
                </div>
                <div className="text-xs text-on-surface-variant flex items-center p-3 rounded-lg bg-surface-container-low mt-auto border-none">
                  <span className="material-symbols-outlined mr-2 text-[14px]">calendar_today</span>
                  Created {new Date(project.created_at).toLocaleDateString()}
                </div>
              </GlassCard>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
