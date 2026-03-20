/**
 * API client to communicate with the FastAPI backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  let token = "";
  
  // Attempt to get token if we are in the browser context
  if (typeof window !== "undefined") {
    token = localStorage.getItem("auth_token") || "";
  }
  
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      // Clear token and redirect to login
      localStorage.removeItem("auth_token");
      window.location.href = "/login";
    }
    throw new Error(`API request failed: ${response.statusText}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
      return null;
  }
  return response.json();
}

export const api = {
  auth: {
    login: (data: Record<string, string>) => fetchWithAuth("/auth/login", { method: "POST", body: JSON.stringify(data) }),
    me: () => fetchWithAuth("/auth/me"),
  },
  projects: {
    list: () => fetchWithAuth("/projects"),
    get: (id: string) => fetchWithAuth(`/projects/${id}`),
    create: (data: Record<string, unknown>) => fetchWithAuth("/projects", { method: "POST", body: JSON.stringify(data) }),
    analyze: (id: string) => fetchWithAuth(`/projects/${id}/analyse`, { method: "POST" }),
    getAnalysis: (id: string) => fetchWithAuth(`/projects/${id}/analysis`),
    delete: (id: string) => fetchWithAuth(`/projects/${id}`, { method: "DELETE" }),
  },
  topics: {
    list: (projectId: string) => fetchWithAuth(`/projects/${projectId}/topics`),
    get: (projectId: string, topicId: string) => fetchWithAuth(`/projects/${projectId}/topics/${topicId}`),
    create: (projectId: string, data: Record<string, unknown>) => fetchWithAuth(`/projects/${projectId}/topics`, { method: "POST", body: JSON.stringify(data) }),
    generate: (projectId: string, topicId: string) => fetchWithAuth(`/projects/${projectId}/topics/${topicId}/generate`, { method: "POST" }),
  },
  articles: {
    list: (projectId: string) => fetchWithAuth(`/projects/${projectId}/articles`),
    get: (projectId: string, articleId: string) => fetchWithAuth(`/projects/${projectId}/articles/${articleId}`),
  }
};
