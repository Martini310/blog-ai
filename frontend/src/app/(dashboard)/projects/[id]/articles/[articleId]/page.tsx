"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/GlassCard";
import { api } from "@/lib/api";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function SingleArticleView() {
  const params = useParams();
  const projectId = params.id as string;
  const articleId = params.articleId as string;
  
  const [article, setArticle] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const articleData = await api.articles.get(projectId, articleId);
        setArticle(articleData);
      } catch (err) {
        console.error("Article load error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [projectId, articleId]);

  if (loading) {
    return (
      <div className="flex justify-center p-12">
        <span className="material-symbols-outlined animate-spin text-primary text-4xl">refresh</span>
      </div>
    );
  }

  if (!article) {
    return (
      <GlassCard className="text-center py-16">
        <span className="material-symbols-outlined text-4xl text-error mb-4">error</span>
        <h3 className="text-lg font-medium text-on-surface mb-2">Article Not Found</h3>
        <p className="text-sm text-on-surface-variant mb-6">This article may have been deleted.</p>
        <Link href={`/projects/${projectId}`}>
          <button className="py-2.5 px-6 bg-surface-container text-on-surface rounded-full font-bold text-sm hover:bg-surface-container-high transition-colors">
            Back to Project
          </button>
        </Link>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-10">
      <header className="flex flex-col md:flex-row items-start justify-between gap-6">
        <div>
          <div className="flex items-center space-x-2 text-sm text-on-surface-variant mb-4">
            <Link href={`/projects/${projectId}`} className="hover:text-primary transition-colors flex items-center">
              <span className="material-symbols-outlined text-[16px] mr-1">arrow_back</span>
              Project
            </Link>
            <span>/</span>
            <span className="text-on-surface">Article</span>
          </div>
          <h1 className="text-4xl font-display font-medium tracking-tight mb-2 flex items-center">
             {article.title || "Untitled Article"}
          </h1>
          <div className="flex items-center mt-3">
             <span className={`uppercase text-[10px] tracking-wider font-bold px-2 py-0.5 rounded-sm bg-surface-container/50 ${article.status === "published" ? "text-secondary" : "text-on-surface-variant"}`}>
               {article.status?.replace("_", " ")}
             </span>
             <span className="text-sm text-on-surface-variant ml-4">
               {article.word_count || 0} Words • Model: {article.model_used || "Unknown"}
             </span>
          </div>
        </div>
        <div className="flex space-x-3">
          {article.status !== "published" && (
            <button className="py-2.5 px-6 bg-secondary text-secondary-container-highest rounded-full font-bold text-sm hover:shadow-[0_0_20px_rgba(221,183,255,0.4)] transition-all flex items-center border-none">
              <span className="material-symbols-outlined mr-2 text-[18px]">publish</span>
              Publish Now
            </button>
          )}
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <GlassCard className="lg:col-span-2 flex flex-col">
          <div className="flex items-center justify-between text-on-surface-variant mb-4 border-b border-surface-container-high/30 pb-4">
            <div className="flex items-center">
               <span className="material-symbols-outlined mr-2">description</span>
               <h3 className="text-sm font-semibold uppercase tracking-wider text-on-surface">Content Preview</h3>
            </div>
            <span className="text-xs">{article.total_tokens || 0} tokens</span>
          </div>
          <div className="prose prose-invert max-w-none text-sm text-on-surface-variant leading-relaxed">
             {/* Simple pre-wrap for JSON since the real content renderer isn't built yet */}
             <pre className="whitespace-pre-wrap bg-surface-container-low p-4 rounded-lg text-xs font-mono">
                {JSON.stringify(article.content_json, null, 2)}
             </pre>
          </div>
        </GlassCard>

        <div className="space-y-6">
          <GlassCard className="flex flex-col">
            <div className="flex items-center text-on-surface-variant mb-4 border-b border-surface-container-high/30 pb-4">
              <span className="material-symbols-outlined mr-2">monitoring</span>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-on-surface">SEO Data</h3>
            </div>
            <div className="text-xs text-on-surface-variant">
               <pre className="whitespace-pre-wrap font-mono">
                  {JSON.stringify(article.seo_data, null, 2)}
               </pre>
            </div>
          </GlassCard>

          <GlassCard className="flex flex-col">
            <div className="flex items-center text-on-surface-variant mb-4 border-b border-surface-container-high/30 pb-4">
              <span className="material-symbols-outlined mr-2">calendar_month</span>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-on-surface">Dates</h3>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Generated At</p>
                <p className="text-on-surface text-sm">{new Date(article.created_at).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Published At</p>
                <p className="text-on-surface text-sm">{article.published_at ? new Date(article.published_at).toLocaleString() : "Not Published"}</p>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
