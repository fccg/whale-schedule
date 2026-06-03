const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let token: string | null = null;

export function setToken(t: string) {
  token = t;
  if (typeof window !== "undefined") {
    localStorage.setItem("token", t);
  }
}

export function getToken(): string | null {
  if (token) return token;
  if (typeof window !== "undefined") {
    token = localStorage.getItem("token");
  }
  return token;
}

export function clearToken() {
  token = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("token");
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };
  const t = getToken();
  if (t) {
    headers["Authorization"] = `Bearer ${t}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: "Network error" }));
    const detail = err?.detail;
    const message =
      err?.message ||
      detail?.message ||
      (typeof detail === "string" ? detail : null) ||
      `HTTP ${res.status}`;
    throw new Error(message);
  }
  return res.json();
}

export const api = {
  login: (username: string, password: string) =>
    request<{ token: string; user: { id: string; username: string } }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  register: (username: string, password: string) =>
    request<{ token: string; user: { id: string; username: string } }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  checkAuth: () => request<{ user_id: string; username: string }>("/api/auth/check"),

  getGPUs: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<MarketplaceResponse>(`/api/gpus${qs}`);
  },

  getGPUDetail: (id: string) => request<GPUOffering>(`/api/gpus/${id}`),

  getLaunchPayload: (id: string) => request<LaunchPayload>(`/api/gpus/${id}/launch`),

  createInstance: (data: { gpu_offering_id: string; template?: string; disk_gb?: number; duration_h?: number }) =>
    request<{ instance: Instance; estimated_cost: number; launch_summary: LaunchSummary }>("/api/instances", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  estimateCost: (gpu_offering_id: string, duration_h: number) =>
    request<{ price_per_hour: number; estimated_total: number; remaining_budget: number }>("/api/instances/estimate", {
      method: "POST",
      body: JSON.stringify({ gpu_offering_id, duration_h }),
    }),

  getInstances: () => request<{ instances: Instance[] }>("/api/instances"),

  getInstance: (id: string) => request<{ instance: Instance; metrics: Metric | null }>(`/api/instances/${id}`),

  getInstanceDashboard: (id: string) => request<InstanceDashboard>(`/api/instances/${id}/dashboard`),

  getInstanceMetrics: (id: string) =>
    request<{ latest: Metric | null; history: Metric[] }>(`/api/instances/${id}/metrics`),

  deleteInstance: (id: string) => request<{ status: string }>(`/api/instances/${id}`, { method: "DELETE" }),

  getBudget: () => request<{ total: number; spent: number; remaining: number }>("/api/budget"),

  triggerTest: (instanceId: string, type: string) =>
    request<{ test_run_id: string; status: string }>(`/api/instances/${instanceId}/tests`, {
      method: "POST",
      body: JSON.stringify({ type }),
    }),

  getTests: (instanceId: string) =>
    request<{ test_runs: TestRun[] }>(`/api/instances/${instanceId}/tests`),

  triggerConnectivityTest: (instanceId: string) =>
    request<{ status: string; targets_tested: number }>(`/api/instances/${instanceId}/connectivity`, {
      method: "POST",
    }),

  getConnectivity: (instanceId: string) =>
    request<{ connectivity_tests: ConnectivityTest[] }>(`/api/instances/${instanceId}/connectivity`),
};

export interface GPUOffering {
  id: string;
  provider: string;
  host_display_name: string;
  gpu_family: string;
  gpu_model: string;
  gpu_count: number;
  vram_gb: number;
  cpu_cores: number;
  memory_gb: number;
  disk_gb: number;
  disk_type: string;
  price_per_hour: number;
  currency: string;
  region: string;
  available: boolean;
  verified: boolean;
  reliability_score: number;
  network_up_mbps: number;
  network_down_mbps: number;
  secure_cloud: boolean;
  max_duration_days: number;
  badge_tags: string[];
}

export interface Instance {
  id: string;
  user_id: string;
  provider: string;
  provider_instance_id: string;
  gpu_offering_id: string;
  status: string;
  current_step: number;
  progress_percent: number;
  last_error: string | null;
  last_heartbeat_at: string | null;
  config_json: string;
  created_at: string;
  destroyed_at: string | null;
  offering?: GPUOffering | null;
}

export interface Metric {
  id: number;
  instance_id: string;
  timestamp: string;
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  gpu_util_percent: number;
  gpu_vram_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  net_up_mbps: number;
  net_down_mbps: number;
  gpu_json: string | null;
}

export interface TestRun {
  id: string;
  instance_id: string;
  type: string;
  status: string;
  started_at: string;
  finished_at: string;
  trigger: string;
  results: TestResult[];
}

export interface TestResult {
  id: number;
  test_run_id: string;
  metric_name: string;
  value: number;
  unit: string;
  passed: number;
}

export interface ConnectivityTest {
  id: number;
  instance_id: string;
  target: string;
  status_code: number;
  latency_ms: number;
  is_direct: number;
  error_message: string | null;
  timestamp: string;
}

export interface MarketplaceResponse {
  items: GPUOffering[];
  total: number;
  filters: {
    families: string[];
    providers: string[];
    regions: string[];
  };
}

export interface TemplateOption {
  id: string;
  label: string;
  image: string;
  description: string;
  highlights: string[];
  recommended: boolean;
}

export interface LaunchSummary {
  price_per_hour: number;
  estimated_total: number;
  remaining_budget: number;
}

export interface LaunchPayload {
  offering: GPUOffering;
  templates: TemplateOption[];
  defaults: {
    template_id: string;
    disk_gb: number;
    duration_h: number;
  };
  budget: LaunchSummary;
  recommended_config: {
    template: string;
    disk_gb: number;
    duration_h: number;
  };
}

export interface GpuRuntimeDetail {
  index: number;
  utilization: number;
  vram_percent: number;
  vram_used_gb: number;
  vram_total_gb: number;
  temp_c: number;
  power_w: number;
}

export interface RuntimeInfo {
  uptime_seconds: number;
  process_count: number;
  disk_used_gb: number;
  disk_total_gb: number;
  volume_used_gb: number | null;
  volume_total_gb: number | null;
  driver_version: string;
  cuda_version: string;
  pstate: string;
  gpus: GpuRuntimeDetail[];
}

export interface ConnectInfo {
  jupyter_url: string;
  ssh_host: string;
  ssh_port: number;
  docker_image: string;
  image_runtype: string;
  env: Record<string, string>;
  command_preview: string;
}

export interface InstanceDashboard {
  instance: Instance;
  offering: GPUOffering | null;
  runtime: RuntimeInfo;
  latest_metric: Metric | null;
  metric_history: Metric[];
  connect: ConnectInfo;
  connectivity_summary: ConnectivityTest[];
  tests_summary: TestRun[];
}
