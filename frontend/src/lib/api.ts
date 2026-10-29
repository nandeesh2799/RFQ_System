import type { User, DashboardStats, RFQListItem, RFQDetail, BidSubmissionForm } from "@/types";

const DEMO_USER_KEY = "rfq_demo_user_email";
const DEFAULT_USER_EMAIL = "buyer@acme.corp";

export function getStoredDemoUser(): string {
  if (typeof window === "undefined") return DEFAULT_USER_EMAIL;
  return localStorage.getItem(DEMO_USER_KEY) || DEFAULT_USER_EMAIL;
}

export function setStoredDemoUser(email: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(DEMO_USER_KEY, email);
    window.dispatchEvent(new Event("persona_changed"));
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const email = getStoredDemoUser();
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (email) {
    headers.set("X-Demo-User-Email", email);
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}`;
    try {
      const errData = await response.json();
      if (errData.detail) {
        errorMsg = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export const api = {
  getUsers: (): Promise<User[]> => request<User[]>("/api/v1/auth/users"),

  getDashboardStats: (): Promise<DashboardStats> => request<DashboardStats>("/api/v1/dashboard/stats"),

  listRFQs: (status?: string, query?: string): Promise<RFQListItem[]> => {
    const params = new URLSearchParams();
    if (status && status !== "ALL") params.append("status", status);
    if (query) params.append("search", query);
    const queryString = params.toString() ? `?${params.toString()}` : "";
    return request<RFQListItem[]>(`/api/v1/rfqs${queryString}`);
  },

  getRFQDetail: (rfqId: number): Promise<RFQDetail> => request<RFQDetail>(`/api/v1/rfqs/${rfqId}`),

  createRFQ: (payload: any): Promise<RFQDetail> =>
    request<RFQDetail>("/api/v1/rfqs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  submitBid: (rfqId: number, data: BidSubmissionForm | any): Promise<any> =>
    request<any>(`/api/v1/rfqs/${rfqId}/bids`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
