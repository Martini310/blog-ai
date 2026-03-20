"use client";

import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { GlassCard } from "@/components/GlassCard";
import { api } from "@/lib/api";

export default function NewTopic() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.id as string;
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [formData, setFormData] = useState({
    title: "",
    slug: "",
    priority: 0,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    
    setFormData((prev) => {
      const nextData = { ...prev, [name]: value };
      // Auto-generate slug if typing title and slug is empty or matches previous auto-slug
      if (name === "title" && (!prev.slug || prev.slug === prev.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)+/g, ''))) {
         nextData.slug = value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)+/g, '');
      }
      return nextData;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await api.topics.create(projectId, {
        title: formData.title,
        slug: formData.slug || formData.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)+/g, ''),
        status: "queued",
        priority: Number(formData.priority),
        topic_metadata: {}
      });
      // Navigate to the newly created topic
      if (response && response.id) {
         router.push(`/projects/${projectId}/topics/${response.id}`);
      } else {
         router.push(`/projects/${projectId}`);
      }
    } catch (err: any) {
      setError(err.message || "Failed to create topic");
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="flex items-center space-x-2 text-sm text-on-surface-variant mb-4">
        <Link href={`/projects/${projectId}`} className="hover:text-primary transition-colors flex items-center">
          <span className="material-symbols-outlined text-[16px] mr-1">arrow_back</span>
          Project Pipeline
        </Link>
        <span>/</span>
        <span className="text-on-surface">New Topic</span>
      </div>

      <header>
        <h1 className="text-4xl font-display font-medium tracking-tight mb-2">Create New Topic</h1>
        <p className="text-on-surface-variant text-lg">Queue a new content piece for the autonomous engine to generate.</p>
      </header>

      <GlassCard className="p-8">
        {error && (
          <div className="mb-6 p-4 rounded bg-error/10 border border-error/50 text-error text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <label htmlFor="title" className="block text-sm font-medium text-on-surface uppercase tracking-wider">Topic Title *</label>
            <input
              type="text"
              id="title"
              name="title"
              required
              maxLength={500}
              placeholder="e.g. 10 Best Practices for SaaS Onboarding"
              value={formData.title}
              onChange={handleChange}
              className="w-full bg-surface-container/50 border border-surface-container-high/50 rounded-lg py-3 px-4 text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label htmlFor="slug" className="block text-sm font-medium text-on-surface uppercase tracking-wider">URL Slug *</label>
              <input
                type="text"
                id="slug"
                name="slug"
                required
                maxLength={500}
                placeholder="e.g. 10-best-practices-saas-onboarding"
                value={formData.slug}
                onChange={handleChange}
                className="w-full bg-surface-container/50 border border-surface-container-high/50 rounded-lg py-3 px-4 text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="priority" className="block text-sm font-medium text-on-surface uppercase tracking-wider">Priority (0-100)</label>
              <input
                type="number"
                id="priority"
                name="priority"
                min={0}
                max={100}
                value={formData.priority}
                onChange={handleChange}
                className="w-full bg-surface-container/50 border border-surface-container-high/50 rounded-lg py-3 px-4 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              />
            </div>
          </div>

          <div className="pt-6 border-t border-surface-container-high/30 flex items-center justify-end space-x-4">
            <Link href={`/projects/${projectId}`} className="text-on-surface-variant hover:text-on-surface text-sm font-medium transition-colors">
              Cancel
            </Link>
            <button
              type="submit"
              disabled={loading || !formData.title || !formData.slug}
              className="py-3 px-8 bg-primary-container text-on-primary-container disabled:opacity-50 disabled:cursor-not-allowed rounded-full font-bold text-sm hover:shadow-[0_0_20px_rgba(125,233,255,0.4)] transition-all flex items-center"
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined animate-spin mr-2 text-[18px]">refresh</span>
                  Creating...
                </>
              ) : (
                "Queue Topic"
              )}
            </button>
          </div>
        </form>
      </GlassCard>
    </div>
  );
}
