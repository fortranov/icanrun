/**
 * Axios API client with JWT auth interceptors.
 * Handles token refresh on 401 responses automatically.
 */
import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from "axios";

// Use relative URLs so Next.js proxy (/api/* rewrite in next.config.mjs)
// handles routing — avoids cross-origin requests from the browser entirely.
// NEXT_PUBLIC_API_URL is still consumed by next.config.mjs for the destination.
const API_BASE_URL = "";

// Token storage keys
const ACCESS_TOKEN_KEY = "icanrun_access_token";
const REFRESH_TOKEN_KEY = "icanrun_refresh_token";

// ---- Token helpers ----

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// ---- Axios instance ----

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

// Request interceptor — attach access token to every request
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Flag to prevent multiple simultaneous refresh attempts
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: string) => void;
  reject: (reason?: unknown) => void;
}> = [];

function processQueue(error: Error | null, token: string | null = null): void {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token!);
    }
  });
  failedQueue = [];
}

// Response interceptor — handle 401 with token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Queue requests while refresh is in progress
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return apiClient(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(
          `${API_BASE_URL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken }
        );
        const { access_token } = response.data;
        setTokens(access_token, refreshToken);
        processQueue(null, access_token);
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as Error, null);
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ---- API methods ----

// ---- Response types for Google OAuth ----

export interface GoogleCallbackResponse {
  access_token?: string | null;
  refresh_token?: string | null;
  token_type: string;
  requires_terms_acceptance: boolean;
  pending_token?: string | null;
  name?: string | null;
  email?: string | null;
}

export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post("/auth/login", { email, password }),

  register: (email: string, password: string, name: string, extra?: object) =>
    apiClient.post("/auth/register", { email, password, name, ...extra }),

  refresh: (refreshToken: string) =>
    apiClient.post("/auth/refresh", { refresh_token: refreshToken }),

  logout: () => {
    const refreshToken =
      typeof window !== "undefined"
        ? localStorage.getItem("icanrun_refresh_token")
        : null;
    return apiClient.post("/auth/logout", { refresh_token: refreshToken ?? "" });
  },

  me: () => apiClient.get("/users/me"),

  confirmEmail: (token: string) =>
    apiClient.post(`/auth/confirm-email?token=${encodeURIComponent(token)}`),

  resendConfirmation: (email: string) =>
    apiClient.post("/auth/resend-confirmation", { email }),

  // --- Public settings (no auth required) ---
  getAuthSettings: (): Promise<{ google_oauth_enabled: boolean }> =>
    apiClient.get<{ google_oauth_enabled: boolean }>("/auth/settings").then((r) => r.data),

  // --- Google OAuth ---
  getGoogleAuthUrl: (): Promise<{ auth_url: string }> =>
    apiClient.get<{ auth_url: string }>("/auth/google").then((r) => r.data),

  googleCallback: (code: string, redirect_uri: string): Promise<GoogleCallbackResponse> =>
    apiClient
      .post<GoogleCallbackResponse>("/auth/google/callback", { code, redirect_uri })
      .then((r) => r.data),

  googleComplete: (pending_token: string): Promise<{ access_token: string; refresh_token: string; token_type: string }> =>
    apiClient
      .post<{ access_token: string; refresh_token: string; token_type: string }>(
        "/auth/google/complete",
        { pending_token }
      )
      .then((r) => r.data),
};

export const workoutsApi = {
  list: (params?: object) =>
    apiClient.get("/workouts", { params }),

  get: (id: number) => apiClient.get(`/workouts/${id}`),

  create: (data: object) => apiClient.post("/workouts", data),

  update: (id: number, data: object) => apiClient.patch(`/workouts/${id}`, data),

  delete: (id: number) => apiClient.delete(`/workouts/${id}`),

  complete: (id: number, data?: object) =>
    apiClient.post(`/workouts/${id}/complete`, data ?? {}),

  move: (id: number, newDate: string) =>
    apiClient.patch(`/workouts/${id}/move`, { new_date: newDate }),

  toggleComplete: (id: number) =>
    apiClient.patch(`/workouts/${id}/toggle-complete`),
};

export const competitionsApi = {
  list: (params?: object) => apiClient.get("/competitions", { params }),

  get: (id: number) => apiClient.get(`/competitions/${id}`),

  create: (data: object) => apiClient.post("/competitions", data),

  update: (id: number, data: object) =>
    apiClient.patch(`/competitions/${id}`, data),

  delete: (id: number) => apiClient.delete(`/competitions/${id}`),

  addResult: (id: number, data: object) =>
    apiClient.post(`/competitions/${id}/result`, data),
};

export const plansApi = {
  list: () => apiClient.get("/plans"),

  generate: (data: object) => apiClient.post("/plans/generate", data),

  get: (id: number) => apiClient.get(`/plans/${id}`),

  updateSettings: (id: number, data: object) =>
    apiClient.patch(`/plans/${id}/settings`, data),

  delete: (id: number) => apiClient.delete(`/plans/${id}`),
};

export const analyticsApi = {
  monthly: (year: number, month: number, sport?: string) =>
    apiClient.get("/analytics/monthly", { params: { year, month, sport } }),

  daily: (year: number, month: number, sport?: string) =>
    apiClient.get("/analytics/daily", { params: { year, month, sport } }),
};

export const subscriptionsApi = {
  current: () => apiClient.get("/subscriptions/current"),

  createPayment: (plan: string) =>
    apiClient.post("/payments/create", { plan }),
};

export const garminApi = {
  status: () => apiClient.get("/garmin/status"),

  connect: (username: string, password: string) =>
    apiClient.post("/garmin/connect", { username, password }),

  disconnect: () => apiClient.post("/garmin/disconnect"),

  sync: () => apiClient.post("/garmin/sync"),
};

export const stravaApi = {
  status: (): Promise<{ connected: boolean; athlete_id: number | null; athlete_name: string | null }> =>
    apiClient.get("/strava/status").then((r) => r.data),

  getAuthUrl: (): Promise<{ auth_url: string }> =>
    apiClient.get("/strava/auth").then((r) => r.data),

  callback: (code: string): Promise<{ athlete_id: number; athlete_name: string }> =>
    apiClient.post("/strava/callback", { code }).then((r) => r.data),

  sync: (days = 30): Promise<{ synced: number; skipped: number }> =>
    apiClient.post(`/strava/sync?days=${days}`).then((r) => r.data),

  disconnect: () => apiClient.post("/strava/disconnect"),
};

export const adminApi = {
  users: (page = 1, perPage = 50) =>
    apiClient.get("/admin/users", { params: { page, per_page: perPage } }),

  updateUser: (id: number, data: object) =>
    apiClient.patch(`/admin/users/${id}`, data),

  deleteUser: (id: number) => apiClient.delete(`/admin/users/${id}`),

  settings: () => apiClient.get("/admin/settings"),

  updateSettings: (data: object) => apiClient.patch("/admin/settings", data),

  testEmail: (data: object) => apiClient.post("/admin/settings/test-email", data),
};
