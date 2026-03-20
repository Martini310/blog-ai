"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { GlassCard } from "@/components/GlassCard";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await api.auth.login({ email, password });
      if (res.access_token) {
        localStorage.setItem("auth_token", res.access_token);
        // Force router flush to get the new session layout
        window.location.href = "/";
      }
    } catch (err: any) {
      setError(err.message || "Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-container-lowest p-4 bg-gradient-to-br from-[#060e20] to-[#0c1934]">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-[40%] -right-[10%] w-[70vw] h-[70vw] rounded-full bg-primary opacity-5 blur-[120px]"></div>
          <div className="absolute -bottom-[40%] -left-[10%] w-[70vw] h-[70vw] rounded-full bg-secondary opacity-5 blur-[120px]"></div>
      </div>
      
      <GlassCard className="w-full max-w-md relative z-10" glow>
        <div className="text-center mb-8">
          <h1 className="text-3xl font-display font-medium text-on-surface tracking-tight mb-2">
            Luminescent <span className="text-primary">AI</span>
          </h1>
          <p className="text-sm text-on-surface-variant">Sign in to your automation engine</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-error/10 border border-error/20 rounded-lg flex items-center text-error text-sm">
            <span className="material-symbols-outlined mr-2">error</span>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-xs font-medium text-on-surface-variant uppercase tracking-wider mb-2">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-surface-container-low border border-surface-container-high rounded-lg px-4 py-3 text-on-surface placeholder:text-surface-container-high focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              placeholder="architect@luminescent.ai"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-on-surface-variant uppercase tracking-wider mb-2">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-surface-container-low border border-surface-container-high rounded-lg px-4 py-3 text-on-surface placeholder:text-surface-container-high focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-primary-container text-on-primary-container rounded-lg font-bold hover:shadow-[0_0_20px_rgba(125,233,255,0.4)] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center"
          >
            {loading ? (
              <span className="material-symbols-outlined animate-spin">refresh</span>
            ) : (
              "Sign In"
            )}
          </button>
        </form>
      </GlassCard>
    </div>
  );
}
