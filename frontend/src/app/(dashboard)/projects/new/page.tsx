"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { GlassCard } from "@/components/GlassCard";
import { api } from "@/lib/api";

export default function NewProject() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    domain: "",
    language: "en",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await api.projects.create({
        ...formData,
        settings: {} // default empty settings
      });
      // Navigate to the newly created project's specialized view
      if (response && response.id) {
         router.push(`/projects/${response.id}`);
      } else {
         router.push("/projects");
      }
    } catch (err: any) {
      setError(err.message || "Failed to create project");
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="flex items-center space-x-2 text-sm text-on-surface-variant mb-4">
        <Link href="/projects" className="hover:text-primary transition-colors flex items-center">
          <span className="material-symbols-outlined text-[16px] mr-1">arrow_back</span>
          Projects
        </Link>
        <span>/</span>
        <span className="text-on-surface">New</span>
      </div>

      <header>
        <h1 className="text-4xl font-display font-medium tracking-tight mb-2">Create New Project</h1>
        <p className="text-on-surface-variant text-lg">Define a new strategic workspace for your autonomous content engine.</p>
      </header>

      <GlassCard className="p-8">
        {error && (
          <div className="mb-6 p-4 rounded bg-error/10 border border-error/50 text-error text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <label htmlFor="name" className="block text-sm font-medium text-on-surface uppercase tracking-wider">Project Name *</label>
            <input
              type="text"
              id="name"
              name="name"
              required
              maxLength={255}
              placeholder="e.g. Acme SaaS Blog"
              value={formData.name}
              onChange={handleChange}
              className="w-full bg-surface-container/50 border border-surface-container-high/50 rounded-lg py-3 px-4 text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="description" className="block text-sm font-medium text-on-surface uppercase tracking-wider">Strategic Context Description</label>
            <textarea
              id="description"
              name="description"
              rows={4}
              placeholder="Describe the company, product, tone of voice, and primary audience..."
              value={formData.description}
              onChange={handleChange}
              className="w-full bg-surface-container/50 border border-surface-container-high/50 rounded-lg py-3 px-4 text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label htmlFor="domain" className="block text-sm font-medium text-on-surface uppercase tracking-wider">Target Domain</label>
              <input
                type="text"
                id="domain"
                name="domain"
                maxLength={255}
                placeholder="e.g. acme.com"
                value={formData.domain}
                onChange={handleChange}
                className="w-full bg-surface-container/50 border border-surface-container-high/50 rounded-lg py-3 px-4 text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="language" className="block text-sm font-medium text-on-surface uppercase tracking-wider">Primary Language</label>
              <select
                id="language"
                name="language"
                value={formData.language}
                onChange={handleChange}
                className="w-full bg-surface-container/50 border border-surface-container-high/50 rounded-lg py-3 px-4 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all appearance-none"
              >
                <option value="en">English (en)</option>
                <option value="pl">Polish (pl)</option>
                <option value="es">Spanish (es)</option>
                <option value="fr">French (fr)</option>
                <option value="de">German (de)</option>
              </select>
            </div>
          </div>

          <div className="pt-6 border-t border-surface-container-high/30 flex items-center justify-end space-x-4">
            <Link href="/projects" className="text-on-surface-variant hover:text-on-surface text-sm font-medium transition-colors">
              Cancel
            </Link>
            <button
              type="submit"
              disabled={loading || !formData.name}
              className="py-3 px-8 bg-primary-container text-on-primary-container disabled:opacity-50 disabled:cursor-not-allowed rounded-full font-bold text-sm hover:shadow-[0_0_20px_rgba(125,233,255,0.4)] transition-all flex items-center"
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined animate-spin mr-2 text-[18px]">refresh</span>
                  Creating...
                </>
              ) : (
                "Create Project"
              )}
            </button>
          </div>
        </form>
      </GlassCard>
    </div>
  );
}
