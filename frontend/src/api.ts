// API Client for Mafia42 Collection Journal

const BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "") + "/api";

export interface User {
  id: string;
  email: string;
  username: string;
  role: "owner" | "user";
  is_active: boolean;
  created_at: string;
}

export interface UserProfile {
  user_id: string;
  display_name: string;
  initials: string;
  level: string;
  rank: string;
  role_title: string;
  favorite_character: string;
  joined_date: string;
  bio: string;
  avatar_image: string;
}

export interface CatalogueItem {
  id: string;
  category: string;
  name: string;
  character?: string;
  card_id?: string;
  rarity?: string;
  level?: number;
  cp: number;
  description?: string;
  condition?: string;
  how_to?: string;
  extra?: string;
  image?: string;
  logo_image?: string;
  wallet_images?: string[];
  display_order?: number;
}

export interface CPStats {
  total_cp: number;
  user_cp: number;
  completion_percentage: number;
  category_breakdown: Record<string, { total: number; owned: number; max_cp: number; user_cp: number }>;
  total_items: number;
  owned_items: number;
}

export interface UserCollectionData {
  user_id: string;
  owned_item_ids: string[];
  items: Record<string, { item_id: string; owned: boolean; date_obtained?: string; notes?: string }>;
}

export interface Goal {
  id: string;
  title: string;
  description: string;
  current_val: number;
  target_val: number;
  completed: boolean;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: string;
  user_id?: string;
  action: string;
  target_type: string;
  target_id: string;
  details: string;
  ip_address: string;
  timestamp: string;
}

export interface AdminUser {
  id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
  owned_items_count: number;
}

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem("m42_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export const api = {
  // Auth
  async register(data: { email: string; username: string; password: string }) {
    const res = await fetch(`${BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Registration failed");
    }
    const json = await res.json();
    if (json.access_token) {
      localStorage.setItem("m42_token", json.access_token);
    }
    return json;
  },

  async login(data: { username_or_email: string; password: string }) {
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Invalid credentials");
    }
    const json = await res.json();
    if (json.access_token) {
      localStorage.setItem("m42_token", json.access_token);
    }
    return json;
  },

  async logout() {
    localStorage.removeItem("m42_token");
    try {
      await fetch(`${BASE_URL}/auth/logout`, { method: "POST" });
    } catch {
      // ignore
    }
  },

  async getMe(): Promise<User | null> {
    const token = localStorage.getItem("m42_token");
    if (!token) return null;
    const res = await fetch(`${BASE_URL}/auth/me`, {
      headers: getAuthHeader(),
    });
    if (!res.ok) {
      localStorage.removeItem("m42_token");
      return null;
    }
    return res.json();
  },

  // Catalogue
  async getCatalogue(): Promise<Record<string, CatalogueItem[]>> {
    const res = await fetch(`${BASE_URL}/catalogue`);
    if (!res.ok) throw new Error("Failed to load catalogue");
    return res.json();
  },

  async getCategoryItems(category: string, search?: string): Promise<CatalogueItem[]> {
    let url = `${BASE_URL}/catalogue/${category}`;
    if (search) url += `?search=${encodeURIComponent(search)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to load ${category}`);
    return res.json();
  },

  // Collection
  async getCollection(): Promise<UserCollectionData> {
    const res = await fetch(`${BASE_URL}/collection`, {
      headers: getAuthHeader(),
    });
    if (!res.ok) throw new Error("Failed to load personal collection");
    return res.json();
  },

  async toggleOwned(itemId: string): Promise<{ item_id: string; owned: boolean }> {
    const res = await fetch(`${BASE_URL}/collection/toggle/${itemId}`, {
      method: "POST",
      headers: getAuthHeader(),
    });
    if (!res.ok) throw new Error("Failed to toggle owned status");
    return res.json();
  },

  async getStats(): Promise<CPStats> {
    const res = await fetch(`${BASE_URL}/collection/stats`, {
      headers: getAuthHeader(),
    });
    if (!res.ok) throw new Error("Failed to load CP statistics");
    return res.json();
  },

  // User Profile
  async getProfile(): Promise<UserProfile> {
    const res = await fetch(`${BASE_URL}/user/profile`, {
      headers: getAuthHeader(),
    });
    if (!res.ok) throw new Error("Failed to load profile");
    return res.json();
  },

  async updateProfile(data: Partial<UserProfile>): Promise<UserProfile> {
    const res = await fetch(`${BASE_URL}/user/profile`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update profile");
    return res.json();
  },

  // Goals
  async getGoals(): Promise<Goal[]> {
    const res = await fetch(`${BASE_URL}/user/goals`, { headers: getAuthHeader() });
    return res.ok ? res.json() : [];
  },

  async createGoal(data: { title: string; description?: string; current_val?: number; target_val?: number }) {
    const res = await fetch(`${BASE_URL}/user/goals`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  async updateGoal(id: string, data: Partial<Goal>) {
    const res = await fetch(`${BASE_URL}/user/goals/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  async deleteGoal(id: string) {
    await fetch(`${BASE_URL}/user/goals/${id}`, {
      method: "DELETE",
      headers: getAuthHeader(),
    });
  },

  // Notes
  async getNotes(): Promise<Note[]> {
    const res = await fetch(`${BASE_URL}/user/notes`, { headers: getAuthHeader() });
    return res.ok ? res.json() : [];
  },

  async createNote(data: { title: string; content: string }) {
    const res = await fetch(`${BASE_URL}/user/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify(data),
    });
    return res.json();
  },

  async deleteNote(id: string) {
    await fetch(`${BASE_URL}/user/notes/${id}`, {
      method: "DELETE",
      headers: getAuthHeader(),
    });
  },

  // Admin (Owner only)
  async createCatalogueItem(data: Partial<CatalogueItem>) {
    const res = await fetch(`${BASE_URL}/admin/catalogue`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to create catalogue item");
    }
    return res.json();
  },

  async updateCatalogueItem(id: string, data: Partial<CatalogueItem>) {
    const res = await fetch(`${BASE_URL}/admin/catalogue/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update catalogue item");
    }
    return res.json();
  },

  async deleteCatalogueItem(id: string) {
    const res = await fetch(`${BASE_URL}/admin/catalogue/${id}`, {
      method: "DELETE",
      headers: getAuthHeader(),
    });
    if (!res.ok) throw new Error("Failed to delete catalogue item");
    return res.json();
  },

  async uploadCatalogueImage(file: File, category: string) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("category", category);
    const res = await fetch(`${BASE_URL}/admin/upload-image`, {
      method: "POST",
      headers: getAuthHeader(),
      body: formData,
    });
    if (!res.ok) throw new Error("Failed to upload image");
    return res.json();
  },

  async getAdminUsers(): Promise<AdminUser[]> {
    const res = await fetch(`${BASE_URL}/admin/users`, { headers: getAuthHeader() });
    if (!res.ok) throw new Error("Failed to fetch user accounts");
    return res.json();
  },

  async updateAdminUserStatus(userId: string, isActive: boolean) {
    const res = await fetch(`${BASE_URL}/admin/users/${userId}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify({ is_active: isActive }),
    });
    return res.json();
  },

  async getAuditLogs(): Promise<AuditLog[]> {
    const res = await fetch(`${BASE_URL}/admin/audit-logs`, { headers: getAuthHeader() });
    if (!res.ok) throw new Error("Failed to fetch audit logs");
    return res.json();
  },

  async exportCatalogue() {
    const res = await fetch(`${BASE_URL}/admin/catalogue/export`, { headers: getAuthHeader() });
    return res.json();
  },

  async importCatalogue(data: any) {
    const res = await fetch(`${BASE_URL}/admin/catalogue/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify({ data }),
    });
    if (!res.ok) throw new Error("Failed to import catalogue");
    return res.json();
  },

  async moveCatalogueItem(params: { category: string; item_id: string; direction?: string; target_position?: number }) {
    const res = await fetch(`${BASE_URL}/admin/catalogue/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to move catalogue item");
    }
    return res.json();
  },

  async reorderCatalogue(category: string, item_ids: string[]) {
    const res = await fetch(`${BASE_URL}/admin/catalogue/reorder`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify({ category, item_ids }),
    });
    if (!res.ok) throw new Error("Failed to reorder catalogue");
    return res.json();
  },

  async getCardSkins(cardId: string): Promise<CatalogueItem[]> {
    const res = await fetch(`${BASE_URL}/catalogue/cards/${cardId}/skins`);
    if (!res.ok) return [];
    return res.json();
  },

  async getSkinCard(skinId: string): Promise<CatalogueItem | null> {
    const res = await fetch(`${BASE_URL}/catalogue/skins/${skinId}/card`);
    if (!res.ok) return null;
    return res.json();
  },

  // Gems API
  async getGems(): Promise<GemsResponse> {
    const res = await fetch(`${BASE_URL}/gems`, { headers: getAuthHeader() });
    if (!res.ok) throw new Error("Failed to load gems");
    return res.json();
  },

  async selectGemLevel(gemId: string, currentLevel: number): Promise<{ message: string; gem_id: string; current_level: number; cp: number; gem_points: number }> {
    const res = await fetch(`${BASE_URL}/gems/${gemId}/select-level`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify({ current_level: currentLevel }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update gem level");
    }
    return res.json();
  },

  async linkGemCard(gemId: string, cardId: string): Promise<{ message: string; gem_id: string; card_id: string; card_name: string }> {
    const res = await fetch(`${BASE_URL}/gems/admin/${gemId}/link-card`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify({ card_id: cardId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to link card to gem");
    }
    return res.json();
  },

  // Image Replacement Approval API
  async getImageProposals(category?: string, status?: string): Promise<{ proposals: ImageProposal[]; total: number }> {
    const params = new URLSearchParams();
    if (category) params.append("category", category);
    if (status) params.append("status_filter", status);
    const res = await fetch(`${BASE_URL}/admin/image-proposals?${params.toString()}`, {
      headers: getAuthHeader(),
    });
    if (!res.ok) throw new Error("Failed to load image proposals");
    return res.json();
  },

  async getImageProposalsSummary(): Promise<{ summary: Record<string, { total: number; pending: number; approved: number; rejected: number }> }> {
    const res = await fetch(`${BASE_URL}/admin/image-proposals/summary`, {
      headers: getAuthHeader(),
    });
    if (!res.ok) throw new Error("Failed to load image proposals summary");
    return res.json();
  },

  async reviewImageProposal(data: {
    item_id: string;
    action: "approve" | "reject" | "skip";
    category: string;
    proposed_url?: string;
    proposed_logo_url?: string;
    target_field?: "artwork" | "logo" | "both";
  }): Promise<{ message: string; status?: string }> {
    const res = await fetch(`${BASE_URL}/admin/image-proposals/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to submit review decision");
    }
    return res.json();
  },

  async getFrameBatchStatus(): Promise<{
    current_batch_number: number;
    current_batch: ImageCandidate[];
    pending_frames_count: number;
    total_approved_frames: number;
    presented_count: number;
  }> {
    const res = await fetch(`${BASE_URL}/admin/frames/batch-status`, {
      headers: getAuthHeader(),
    });
    if (!res.ok) return { current_batch_number: 1, current_batch: [], pending_frames_count: 0, total_approved_frames: 0, presented_count: 0 };
    return res.json();
  },

  async nextFrameBatch(): Promise<{
    message: string;
    current_batch_number: number;
    current_batch: ImageCandidate[];
    pending_frames_count: number;
  }> {
    const res = await fetch(`${BASE_URL}/admin/frames/next-batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to advance to next batch");
    }
    return res.json();
  },

  async getSkinBatchStatus(mode: string = "skin_main"): Promise<{
    mode: string;
    current_batch_number: number;
    current_batch: ImageCandidate[];
    pending_skins_count: number;
    total_approved_skins: number;
    presented_count: number;
    available_batches?: number[];
  }> {
    const res = await fetch(`${BASE_URL}/admin/skins/batch-status?mode=${encodeURIComponent(mode)}`, {
      headers: getAuthHeader(),
    });
    if (!res.ok) return { mode, current_batch_number: 1, current_batch: [], pending_skins_count: 0, total_approved_skins: 0, presented_count: 0, available_batches: [1] };
    return res.json();
  },

  async nextSkinBatch(mode: string = "skin_main"): Promise<{
    message: string;
    mode: string;
    current_batch_number: number;
    current_batch: ImageCandidate[];
    pending_skins_count: number;
    available_batches?: number[];
  }> {
    const res = await fetch(`${BASE_URL}/admin/skins/next-batch?mode=${encodeURIComponent(mode)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to advance to next batch");
    }
    return res.json();
  },

  async switchSkinBatch(mode: string = "skin_main", batchNumber: number): Promise<{
    message: string;
    mode: string;
    current_batch_number: number;
    current_batch: ImageCandidate[];
    pending_skins_count: number;
    available_batches?: number[];
  }> {
    const res = await fetch(`${BASE_URL}/admin/skins/switch-batch?mode=${encodeURIComponent(mode)}&batch_number=${batchNumber}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeader() },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to switch batch");
    }
    return res.json();
  },
};

export interface ImageCandidate {
  label: string;
  type: string;
  repo_path: string;
  url: string;
  filename?: string;
  dimensions?: string;
  is_unused?: boolean;
  already_used_by?: string | null;
  reason?: string;
}

export interface ImageProposal {
  id: string;
  name: string;
  category: string;
  character?: string;
  current_image: string;
  current_logo?: string;
  proposed_repo_path: string;
  proposed_url: string;
  proposed_logo_repo_path?: string;
  proposed_logo_url?: string;
  status: "pending" | "approved" | "rejected";
  decision_details?: any;
  candidates?: ImageCandidate[];
  level?: number;
  role_id?: string;
  skin_id?: string;
  card_id?: string;
}

export interface GemLevelItem {
  level: number;
  name: string;
  description: string;
  cp: number;
  gem_points: number;
  image: string;
}

export interface GemItem {
  id: string;
  category: "gems";
  team: "Mafia Team" | "Citizen Team" | "Cult Mode" | string;
  role_id: string;
  name: string;
  character: string;
  card_id: string;
  card_name: string;
  linked_card?: {
    id: string;
    name: string;
    character: string;
    image: string;
  } | null;
  image: string;
  badge_image: string;
  display_order: number;
  current_level: number;
  current_cp: number;
  current_gem_points: number;
  current_level_data?: GemLevelItem | null;
  levels: GemLevelItem[];
}

export interface GemsResponse {
  user_id: string;
  total_gem_cp: number;
  total_gem_points: number;
  teams: {
    "Mafia Team": GemItem[];
    "Citizen Team": GemItem[];
    "Cult Mode": GemItem[];
    [key: string]: GemItem[];
  };
  all_gems: GemItem[];
}


