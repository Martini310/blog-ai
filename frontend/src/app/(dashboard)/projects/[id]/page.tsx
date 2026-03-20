"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/GlassCard";
import { api } from "@/lib/api";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

const colorMap: Record<string, string> = {
  primary: "text-primary",
  secondary: "text-secondary",
  tertiary: "text-tertiary",
  error: "text-error",
};

export default function SingleProjectView() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  
  const [project, setProject] = useState<any>(null);
  const [pipeline, setPipeline] = useState<any[]>([]);
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  useEffect(() => {
    async function loadProjectData() {
      try {
        const projData = await api.projects.get(projectId);
        setProject(projData);

        const [topics, articles, analysisData] = await Promise.all([
          api.topics.list(projectId).catch(() => []),
          api.articles.list(projectId).catch(() => []),
          api.projects.getAnalysis(projectId).catch(() => null)
        ]);
        setAnalysis(analysisData);

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
        ].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

        setPipeline(mergedPipeline);
      } catch (err) {
        console.error("Single project load error:", err);
      } finally {
        setLoading(false);
      }
    }
    if (projectId) {
      loadProjectData();
    }
  }, [projectId]);

  if (loading) {
    return (
      <div className="flex justify-center p-12">
        <span className="material-symbols-outlined animate-spin text-primary text-4xl">refresh</span>
      </div>
    );
  }

  if (!project) {
    return (
      <GlassCard className="text-center py-16">
        <span className="material-symbols-outlined text-4xl text-error mb-4">error</span>
        <h3 className="text-lg font-medium text-on-surface mb-2">Project Not Found</h3>
        <p className="text-sm text-on-surface-variant mb-6">This project may have been deleted or you do not have permission to view it.</p>
        <Link href="/projects">
          <button className="py-2.5 px-6 bg-surface-container text-on-surface rounded-full font-bold text-sm hover:bg-surface-container-high transition-colors">
            Back to Projects
          </button>
        </Link>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-10">
      <header className="flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div>
          <div className="flex items-center space-x-2 text-sm text-on-surface-variant mb-4">
            <Link href="/projects" className="hover:text-primary transition-colors flex items-center">
              <span className="material-symbols-outlined text-[16px] mr-1">arrow_back</span>
              Projects
            </Link>
            <span>/</span>
            <span className="text-on-surface">{project.name}</span>
          </div>
          <h1 className="text-4xl font-display font-medium tracking-tight mb-2 flex items-center">
            {project.name}
            <span className={`uppercase text-[10px] tracking-wider font-bold px-2 py-0.5 rounded-sm ml-4 bg-surface-container/50 ${project.status === "active" ? "text-primary" : "text-on-surface-variant"}`}>
              {project.status || "Active"}
            </span>
          </h1>
          <p className="text-on-surface-variant text-lg max-w-2xl leading-relaxed">
            {project.description || "No description provided."}
          </p>
        </div>
        <div className="flex space-x-3">
          <button 
            type="button"
            onClick={(e) => {
              e.preventDefault();
              setShowDeleteModal(true);
            }}
            className="py-2.5 px-6 bg-error/10 text-error rounded-full font-bold text-sm hover:bg-error/20 transition-all flex items-center border-none"
          >
            <span className="material-symbols-outlined mr-2 text-[18px]">delete</span>
            Delete Project
          </button>
          <button className="py-2.5 px-6 bg-surface-container text-on-surface rounded-full font-bold text-sm hover:bg-surface-container-high transition-all flex items-center border-none">
            <span className="material-symbols-outlined mr-2 text-[18px]">settings</span>
            Settings
          </button>
          <button 
            onClick={async () => {
              try {
                // Note: Next version we might want to add a toast notification
                await api.projects.analyze(projectId);
                alert("Analysis initiated successfully. The strategic AI Context will be updated momentarily.");
              } catch (err) {
                alert("Failed to initiate analysis.");
                console.error(err);
              }
            }}
            className="py-2.5 px-6 bg-primary-container text-on-primary-container rounded-full font-bold text-sm hover:shadow-[0_0_20px_rgba(125,233,255,0.4)] transition-all flex items-center border-none"
          >
            <span className="material-symbols-outlined mr-2 text-[18px]">analytics</span>
            Analyze Context
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard className="flex flex-col">
          <div className="flex items-center text-on-surface-variant mb-4 border-b border-surface-container-high/30 pb-4">
            <span className="material-symbols-outlined mr-2">psychology</span>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-on-surface">Strategic AI Context</h3>
          </div>
          <p className="text-sm text-on-surface-variant flex-1 leading-relaxed">
            {analysis?.ai_context || project.settings?.ai_context || project.description || "No strategic context generated for this project yet."}
          </p>
          {analysis?.result && (
            <div className="mt-4 grid grid-cols-2 gap-4 border-t border-surface-container-high/30 pt-4">
               <div>
                  <p className="text-xs uppercase tracking-wider text-on-surface-variant mb-1">Target Audience</p>
                  <p className="text-sm text-on-surface leading-tight">{analysis.result.target_audience}</p>
               </div>
               <div>
                  <p className="text-xs uppercase tracking-wider text-on-surface-variant mb-1">Tone of Voice</p>
                  <p className="text-sm text-on-surface leading-tight">{analysis.result.tone_of_voice}</p>
               </div>
               <div className="col-span-2">
                  <p className="text-xs uppercase tracking-wider text-on-surface-variant mb-1">Core Topics</p>
                  <div className="flex flex-wrap gap-2 mt-1">
                     {analysis.result.core_topics?.map((t: string, i: number) => (
                        <span key={i} className="px-2 py-1 bg-surface-container rounded-sm text-xs text-on-surface">{t}</span>
                     ))}
                  </div>
               </div>
            </div>
          )}
          <div className="mt-6 flex justify-between items-center">
             <span className={`uppercase text-[10px] tracking-wider font-bold px-2 py-0.5 rounded-sm bg-surface-container/50 ${analysis?.status === 'completed' ? 'text-secondary' : analysis?.status === 'running' ? 'text-primary' : 'text-on-surface-variant'}`}>
                 Analysis: {analysis?.status || 'Pending'}
             </span>
             <button className="text-primary text-xs font-medium flex items-center hover:text-primary-container transition-colors border-none p-0 bg-transparent">
               Edit Context <span className="material-symbols-outlined ml-1 text-[14px]">arrow_forward</span>
             </button>
          </div>
        </GlassCard>

        <GlassCard className="flex flex-col">
          <div className="flex items-center text-on-surface-variant mb-4 border-b border-surface-container-high/30 pb-4">
            <span className="material-symbols-outlined mr-2">database</span>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-on-surface">Project Metadata</h3>
          </div>
          <div className="grid grid-cols-2 gap-4 flex-1">
            <div>
              <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Domain</p>
              <p className="text-on-surface font-medium">{project.domain || "Not provided"}</p>
            </div>
            <div>
              <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Language</p>
              <p className="text-on-surface font-medium">{project.language || "English"}</p>
            </div>
            <div>
              <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Total Items</p>
              <p className="text-on-surface font-medium">{pipeline.length}</p>
            </div>
            <div>
              <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Created</p>
              <p className="text-on-surface font-medium">{new Date(project.created_at).toLocaleDateString()}</p>
            </div>
          </div>
        </GlassCard>
      </div>

      <section>
        <div className="flex items-center justify-between mb-6 border-b border-surface-container-high/30 pb-4">
          <h2 className="text-xl font-display font-medium">Project Pipeline</h2>
          <Link href={`/projects/${projectId}/topics/new`}>
            <button className="py-2 px-4 bg-primary-container text-on-primary-container rounded-full font-bold text-xs hover:shadow-[0_0_20px_rgba(125,233,255,0.4)] transition-all flex items-center border-none">
              <span className="material-symbols-outlined mr-2 text-[16px]">add</span>
              New Topic
            </button>
          </Link>
        </div>
        
        {pipeline.length === 0 ? (
           <GlassCard className="text-center py-10">
             <span className="material-symbols-outlined text-4xl text-on-surface-variant mb-4">queue_play_next</span>
             <p className="text-sm text-on-surface-variant">No topics or articles found in this project's pipeline.</p>
           </GlassCard>
        ) : (
          <div className="space-y-4">
            {pipeline.map((item) => (
              <Link href={`/projects/${projectId}/${item.type}s/${item.id}`} key={item.id} className="block group">
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

      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
          <GlassCard className="max-w-md w-full p-8 text-center shadow-2xl border-error/50 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-error"></div>
            <span className="material-symbols-outlined text-error text-5xl mb-4 font-light">warning</span>
            <h3 className="text-2xl font-display font-medium mb-3 text-on-surface tracking-tight">Delete Project?</h3>
            <p className="text-on-surface-variant mb-8 leading-relaxed">
              Are you absolutely sure you want to delete <strong>{project.name}</strong>? This will permanently erase all queued topics, published articles, and analytical memory. This action cannot be undone.
            </p>
            <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4 justify-center">
              <button 
                type="button"
                onClick={() => setShowDeleteModal(false)}
                className="py-3 px-8 bg-surface-container text-on-surface rounded-full font-bold text-sm hover:bg-surface-container-high transition-all"
              >
                Cancel
              </button>
              <button 
                type="button"
                onClick={async () => {
                  try {
                    await api.projects.delete(projectId);
                    router.push("/projects");
                  } catch (err: any) {
                    alert("Failed to delete project: " + err.message);
                    console.error(err);
                    setShowDeleteModal(false);
                  }
                }}
                className="py-3 px-8 bg-error text-white rounded-full font-bold text-sm hover:shadow-[0_0_20px_rgba(255,180,171,0.4)] transition-all"
              >
                Yes, Delete It
              </button>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
