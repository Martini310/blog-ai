"use client";

import { useEffect, useState } from "react";
import { GlassCard } from "@/components/GlassCard";
import { api } from "@/lib/api";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function SingleTopicView() {
  const params = useParams();
  const projectId = params.id as string;
  const topicId = params.topicId as string;
  
  const [topic, setTopic] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const topicData = await api.topics.get(projectId, topicId);
        setTopic(topicData);
      } catch (err) {
        console.error("Topic load error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [projectId, topicId]);

  if (loading) {
    return (
      <div className="flex justify-center p-12">
        <span className="material-symbols-outlined animate-spin text-primary text-4xl">refresh</span>
      </div>
    );
  }

  if (!topic) {
    return (
      <GlassCard className="text-center py-16">
        <span className="material-symbols-outlined text-4xl text-error mb-4">error</span>
        <h3 className="text-lg font-medium text-on-surface mb-2">Topic Not Found</h3>
        <p className="text-sm text-on-surface-variant mb-6">This topic may have been deleted.</p>
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
            <span className="text-on-surface">Topic</span>
          </div>
          <h1 className="text-4xl font-display font-medium tracking-tight mb-2 flex items-center">
            {topic.title}
          </h1>
          <div className="flex items-center mt-3">
             <span className={`uppercase text-[10px] tracking-wider font-bold px-2 py-0.5 rounded-sm bg-surface-container/50 ${topic.status === "in_progress" ? "text-primary" : "text-on-surface-variant"}`}>
               {topic.status?.replace("_", " ")}
             </span>
             <span className="text-sm text-on-surface-variant ml-4">
               Priority: {topic.priority} • Slug: /{topic.slug}
             </span>
          </div>
        </div>
        <div className="flex space-x-3">
          {topic.status !== "completed" && (
            <button 
              onClick={async () => {
                try {
                  await api.topics.generate(projectId, topicId);
                  alert("Article generation task successfully enqueued to the AI worker.");
                } catch (err: any) {
                  alert(err.message || "Failed to trigger article execution.");
                  console.error(err);
                }
              }}
              className="py-2.5 px-6 bg-primary-container text-on-primary-container rounded-full font-bold text-sm hover:shadow-[0_0_20px_rgba(125,233,255,0.4)] transition-all flex items-center border-none"
            >
              <span className="material-symbols-outlined mr-2 text-[18px]">bolt</span>
              Generate Article
            </button>
          )}
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard className="flex flex-col">
          <div className="flex items-center text-on-surface-variant mb-4 border-b border-surface-container-high/30 pb-4">
            <span className="material-symbols-outlined mr-2">database</span>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-on-surface">Topic Metadata</h3>
          </div>
          <p className="text-sm text-on-surface-variant flex-1 leading-relaxed">
             {topic.topic_metadata && Object.keys(topic.topic_metadata).length > 0 
                ? JSON.stringify(topic.topic_metadata, null, 2) 
                : "No granular metadata extracted for this topic yet."}
          </p>
        </GlassCard>

        <GlassCard className="flex flex-col">
          <div className="flex items-center text-on-surface-variant mb-4 border-b border-surface-container-high/30 pb-4">
            <span className="material-symbols-outlined mr-2">calendar_month</span>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-on-surface">Scheduling & Dates</h3>
          </div>
          <div className="grid grid-cols-2 gap-4 flex-1">
            <div>
              <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Created At</p>
              <p className="text-on-surface font-medium">{new Date(topic.created_at).toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Target Date</p>
              <p className="text-on-surface font-medium">{topic.scheduled_date ? new Date(topic.scheduled_date).toLocaleDateString() : "Unscheduled"}</p>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
