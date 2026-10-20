import React, { useState, useEffect, useMemo } from 'react';
import {
  Home, LayoutDashboard, User as UserIcon, Shirt, Sparkles, Layers,
  FolderHeart, Target, BarChart3, Trophy, Wallet as WalletIcon, Coins,
  Heart, Tag, StickyNote, Settings as SettingsIcon, Search, Bell,
  ChevronDown, Plus, X, Star, Check, Menu, TrendingUp, TrendingDown,
  Pin, Calendar, Filter, ArrowLeft, ArrowRight, ArrowUp, ArrowDown,
  Pencil, Trash2, Eye, Download, Upload, Shield, Lock, LogIn, LogOut,
  CheckCircle, AlertCircle, RefreshCw, ExternalLink, Flame, Users,
  Sun, Moon, Smile, MessageSquare
} from 'lucide-react';
import { api, User, CatalogueItem, CPStats, UserCollectionData, Goal, Note, AuditLog, AdminUser, GemItem, GemsResponse, GemLevelItem } from './api';
import { ImageReviewPage } from './components/ImageReviewPage';

const CATEGORY_CONFIG: Record<string, { title: string; singular: string; subtitle: string; isLogo: boolean }> = {
  skins: { title: "Skins", singular: "Skin", subtitle: "Collectible skins with CP values, character assignments, and logos.", isLogo: false },
  icons: { title: "Icons", singular: "Icon", subtitle: "Track every icon, unlock condition, and category.", isLogo: false },
  cards: { title: "Cards", singular: "Card", subtitle: "Character and role cards with level and playable attributes.", isLogo: false },
  wallets: { title: "Wallets", singular: "Wallet", subtitle: "Collectible wallets with logo and 3 associated detailed images.", isLogo: true },
  cp_wallets: { title: "CP Wallets", singular: "CP Wallet", subtitle: "Collection Point tier wallets with CP range requirements and 3 associated detailed images.", isLogo: true },
  nameplates: { title: "NP", singular: "Nameplate", subtitle: "Collectible nameplates with official CP and match metadata.", isLogo: false },
  frames: { title: "Frames", singular: "Frame", subtitle: "Collectible portrait frames with CP values.", isLogo: false },
  gems: { title: "Gems", singular: "Gem", subtitle: "Gems tracking refinement levels 1 through 16.", isLogo: false },
  stickers: { title: "Stickers", singular: "Sticker Pack", subtitle: "Collectible emoticon and sticker packs with unlimited-by-design stickers.", isLogo: false },
  speech_bubbles: { title: "Speech Bubbles", singular: "Speech Bubble", subtitle: "In-game chat and room dialogue balloons with collection CP.", isLogo: false },
  postcards: { title: "PC", singular: "Postcard", subtitle: "Collectible postcards and letters.", isLogo: false },
  refinements: { title: "Refinements", singular: "Refinement", subtitle: "Equipment refinements and enhancements.", isLogo: false },
};

function fmtNum(n: number = 0): string {
  return Number(n || 0).toLocaleString();
}

function getCPWalletIdForCp(cp: number): string {
  if (cp >= 250000) return "cp_wallet_08";
  if (cp >= 125000) return "cp_wallet_07";
  if (cp >= 25000) return "cp_wallet_06";
  if (cp >= 15000) return "cp_wallet_05";
  if (cp >= 7500) return "cp_wallet_04";
  if (cp >= 2500) return "cp_wallet_03";
  if (cp >= 500) return "cp_wallet_02";
  return "cp_wallet_01";
}

export default function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeNav, setActiveNav] = useState<string>("home");
  const [searchQuery, setSearchQuery] = useState<string>("");
  
  // Data State
  const [catalogue, setCatalogue] = useState<Record<string, CatalogueItem[]>>({});
  const [collection, setCollection] = useState<UserCollectionData>({ user_id: "", owned_item_ids: [], items: {} });
  const [stats, setStats] = useState<CPStats | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Modals
  const [focusedItem, setFocusedItem] = useState<{ item: CatalogueItem; category: string } | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authError, setAuthError] = useState<string>("");
  const [authForm, setAuthForm] = useState({ username: "", email: "", password: "" });

  // Admin State
  const [adminItemModal, setAdminItemModal] = useState<{ isOpen: boolean; mode: "create" | "edit"; item?: Partial<CatalogueItem>; category: string }>({
    isOpen: false, mode: "create", category: "skins"
  });
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [adminAuditLogs, setAdminAuditLogs] = useState<AuditLog[]>([]);
  const [adminTab, setAdminTab] = useState<"catalogue" | "users" | "audit">("catalogue");

  const [loadError, setLoadError] = useState<string | null>(null);

  // Theme State (Dark Mode default, persisted in localStorage)
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    return (localStorage.getItem("m42_theme") as "light" | "dark") || "dark";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    document.body.setAttribute("data-theme", theme);
    localStorage.setItem("m42_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === "dark" ? "light" : "dark"));
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  async function loadInitialData() {
    setLoading(true);
    setLoadError(null);
    try {
      // Parallelize auth check and catalogue load for immediate data availability
      const [user, catData] = await Promise.all([
        api.getMe().catch(() => null),
        api.getCatalogue(),
      ]);
      setCurrentUser(user);
      setCatalogue(catData || {});

      if (user) {
        await loadUserData();
      }
    } catch (err: any) {
      console.error("Error loading catalogue data:", err);
      setLoadError(err?.message || "Failed to load catalogue. Please check your connection.");
    } finally {
      setLoading(false);
    }
  }

  async function loadUserData() {
    try {
      const [colData, statsData, goalsData, notesData] = await Promise.all([
        api.getCollection(),
        api.getStats(),
        api.getGoals(),
        api.getNotes(),
      ]);
      setCollection(colData);
      setStats(statsData);
      setGoals(goalsData);
      setNotes(notesData);
    } catch (err) {
      console.error("Error loading user collection:", err);
    }
  }

  async function loadCatalogue() {
    try {
      const catData = await api.getCatalogue();
      setCatalogue(catData || {});
      if (currentUser) {
        const statsData = await api.getStats();
        setStats(statsData);
      }
    } catch (err: any) {
      console.error("Failed to load catalogue:", err);
    }
  }

  // Handle Ownership Toggle
  async function handleToggleOwned(itemId: string) {
    if (!currentUser) {
      setAuthModalOpen(true);
      return;
    }

    // CP Wallets cannot be manually toggled; they are automatically awarded by total CP
    if (itemId.startsWith("cp_wallet_")) {
      return;
    }

    // Find the item to determine its category and CP value
    const allCatalogueItems = [
      ...(catalogue.skins || []),
      ...(catalogue.icons || []),
      ...(catalogue.cards || []),
      ...(catalogue.wallets || []),
      ...(catalogue.cp_wallets || []),
      ...(catalogue.nameplates || []),
      ...(catalogue.frames || []),
      ...(catalogue.gems || []),
      ...(catalogue.stickers || []),
      ...(catalogue.speech_bubbles || []),
      ...(catalogue.postcards || []),
      ...(catalogue.refinements || []),
    ];
    const targetItem = allCatalogueItems.find(it => it.id === itemId);
    const itemCp = Number(targetItem?.cp || 0);
    const itemCat = targetItem?.category || "";
    const isCpEligible = ["skins", "gems", "frames", "nameplates", "wallets", "stickers", "speech_bubbles"].includes(itemCat);

    const isCurrentlyOwned = collection.owned_item_ids.includes(itemId);
    const cpDelta = isCpEligible ? (isCurrentlyOwned ? -itemCp : itemCp) : 0;
    const currentUserCp = (stats?.user_cp || 0) + cpDelta;
    const newUserCp = Math.max(0, currentUserCp);

    // Compute newly eligible CP wallet based on updated total CP
    const newCpWalletId = getCPWalletIdForCp(newUserCp);
    const cpWalletIds = ["cp_wallet_01", "cp_wallet_02", "cp_wallet_03", "cp_wallet_04", "cp_wallet_05", "cp_wallet_06", "cp_wallet_07", "cp_wallet_08"];

    // Update owned IDs: toggle itemId, ensure exactly the single active CP wallet is present
    let nextOwnedIds = isCurrentlyOwned
      ? collection.owned_item_ids.filter(id => id !== itemId)
      : [...collection.owned_item_ids, itemId];

    nextOwnedIds = nextOwnedIds.filter(id => !cpWalletIds.includes(id));
    nextOwnedIds.push(newCpWalletId);

    const nextItems = { ...collection.items };
    nextItems[itemId] = { item_id: itemId, owned: !isCurrentlyOwned };
    for (const cpId of cpWalletIds) {
      nextItems[cpId] = { item_id: cpId, owned: cpId === newCpWalletId };
    }

    setCollection(prev => ({
      ...prev,
      owned_item_ids: nextOwnedIds,
      items: nextItems,
    }));

    // Optimistically update stats
    if (stats) {
      const newCompletionPct = stats.total_cp > 0 ? (newUserCp / stats.total_cp) * 100 : 0;
      const updatedCatBreakdown = { ...stats.category_breakdown };
      if (itemCat && updatedCatBreakdown[itemCat]) {
        updatedCatBreakdown[itemCat] = {
          ...updatedCatBreakdown[itemCat],
          owned: updatedCatBreakdown[itemCat].owned + (isCurrentlyOwned ? -1 : 1),
          user_cp: updatedCatBreakdown[itemCat].user_cp + cpDelta,
        };
      }
      setStats({
        ...stats,
        user_cp: newUserCp,
        completion_percentage: Math.round(newCompletionPct * 100) / 100,
        owned_items: stats.owned_items + (isCurrentlyOwned ? -1 : 1),
        category_breakdown: updatedCatBreakdown,
      });
    }

    try {
      await api.toggleOwned(itemId);
      // Refresh authoritative stats and collection from server
      const [updatedStats, updatedCol] = await Promise.all([api.getStats(), api.getCollection()]);
      setStats(updatedStats);
      setCollection(updatedCol);
    } catch (err) {
      console.error("Failed to toggle item:", err);
      // Revert on error
      loadUserData();
    }
  }

  // Handle Auth
  async function handleAuthSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAuthError("");
    try {
      if (authMode === "login") {
        const res = await api.login({
          username_or_email: authForm.username || authForm.email,
          password: authForm.password,
        });
        setCurrentUser(res.user);
      } else {
        const res = await api.register({
          username: authForm.username,
          email: authForm.email,
          password: authForm.password,
        });
        setCurrentUser(res.user);
      }
      setAuthModalOpen(false);
      setAuthForm({ username: "", email: "", password: "" });
      const catData = await api.getCatalogue();
      setCatalogue(catData);
      await loadUserData();
    } catch (err: any) {
      setAuthError(err.message || "Authentication failed");
    }
  }

  async function handleLogout() {
    await api.logout();
    setCurrentUser(null);
    setCollection({ user_id: "", owned_item_ids: [], items: {} });
    setStats(null);
    try {
      const catData = await api.getCatalogue();
      setCatalogue(catData);
    } catch {}
    if (activeNav === "admin" || activeNav === "profile") {
      setActiveNav("home");
    }
  }

  // Admin Handlers
  async function loadAdminData() {
    if (currentUser?.role !== "owner") return;
    try {
      const [users, logs] = await Promise.all([
        api.getAdminUsers(),
        api.getAuditLogs(),
      ]);
      setAdminUsers(users);
      setAdminAuditLogs(logs);
    } catch (err) {
      console.error("Failed to load admin data:", err);
    }
  }

  useEffect(() => {
    if (activeNav === "admin" && currentUser?.role === "owner") {
      loadAdminData();
    }
  }, [activeNav, currentUser]);

  async function handleAdminSaveItem(itemData: Partial<CatalogueItem>) {
    try {
      if (adminItemModal.mode === "create") {
        await api.createCatalogueItem(itemData);
      } else if (itemData.id) {
        await api.updateCatalogueItem(itemData.id, itemData);
      }
      setAdminItemModal({ isOpen: false, mode: "create", category: "skins" });
      const catData = await api.getCatalogue();
      setCatalogue(catData);
      if (currentUser) {
        const statsData = await api.getStats();
        setStats(statsData);
      }
    } catch (err: any) {
      alert("Error saving item: " + err.message);
    }
  }

  async function handleAdminDeleteItem(itemId: string) {
    if (!confirm(`Are you sure you want to permanently delete catalogue item "${itemId}"?`)) return;
    try {
      await api.deleteCatalogueItem(itemId);
      const catData = await api.getCatalogue();
      setCatalogue(catData);
      if (currentUser) {
        const statsData = await api.getStats();
        setStats(statsData);
      }
    } catch (err: any) {
      alert("Error deleting item: " + err.message);
    }
  }

  async function handleMoveIcon(itemId: string, direction?: string, targetPos?: number) {
    try {
      await api.moveCatalogueItem({ category: "icons", item_id: itemId, direction, target_position: targetPos });
      const catData = await api.getCatalogue();
      setCatalogue(catData);
    } catch (err: any) {
      alert("Error moving icon: " + err.message);
    }
  }

  async function handleToggleUserStatus(userId: string, currentActive: boolean) {
    try {
      await api.updateAdminUserStatus(userId, !currentActive);
      loadAdminData();
    } catch (err: any) {
      alert("Failed to update user status: " + err.message);
    }
  }

  // Navigation Items
  const navSections = [
    {
      items: [
        { id: "home", label: "Home", icon: Home },
        { id: "whatihave", label: "What I Have", icon: FolderHeart },
        { id: "profile", label: "Profile", icon: UserIcon },
      ]
    },
    {
      label: "Collection",
      items: [
        { id: "collection", label: "Collection", icon: LayoutDashboard },
        { id: "skins", label: "Skins", icon: Shirt, count: catalogue.skins?.length },
        { id: "icons", label: "Icons", icon: Sparkles, count: catalogue.icons?.length },
        { id: "cards", label: "Cards", icon: Layers, count: catalogue.cards?.length },
        { id: "wallets", label: "Wallets", icon: WalletIcon, count: catalogue.wallets?.length },
        { id: "cp_wallets", label: "CP Wallets", icon: WalletIcon, count: catalogue.cp_wallets?.length },
        { id: "nameplates", label: "NP", icon: Tag, count: catalogue.nameplates?.length },
        { id: "frames", label: "Frames", icon: Pin, count: catalogue.frames?.length },
        { id: "gems", label: "Gems", icon: Coins, count: catalogue.gems?.length },
        { id: "stickers", label: "Stickers", icon: Smile, count: catalogue.stickers?.length },
        { id: "speech_bubbles", label: "Speech Bubbles", icon: MessageSquare, count: catalogue.speech_bubbles?.length },
      ]
    },
    {
      label: "Resources",
      items: [
        { id: "postcards", label: "PC", icon: StickyNote, count: catalogue.postcards?.length },
        { id: "refinements", label: "Refinements", icon: Filter, count: catalogue.refinements?.length },
      ]
    },
    {
      label: "Progress",
      items: [
        { id: "goals", label: "Goals", icon: Target },
        { id: "statistics", label: "Statistics", icon: BarChart3 },
        { id: "achievements", label: "Achievements", icon: Trophy },
      ]
    },
    {
      label: "More",
      items: [
        { id: "notes", label: "Notes", icon: StickyNote },
        { id: "settings", label: "Settings", icon: SettingsIcon },
      ]
    },
  ];

  if (currentUser?.role === "owner") {
    navSections.push({
      label: "Owner Administration",
      items: [
        { id: "admin", label: "Admin Dashboard", icon: Shield },
        { id: "image_review", label: "Image Approval", icon: Sparkles }
      ]
    });
  } else {
    navSections.push({
      label: "Approval System",
      items: [
        { id: "image_review", label: "Image Approval", icon: Sparkles }
      ]
    });
  }

  return (
    <div className="m42-app" data-theme={theme}>
      <div className="m42-bg" />

      {/* Sidebar */}
      <aside className="m42-sidebar">
        <div className="m42-brand">
          <div className="m42-brand-icon">
            <Trophy size={20} />
          </div>
          <div>
            <div className="m42-brand-title m42-serif">Mafia42 Journal</div>
            <div className="m42-brand-sub">Multi-User Edition</div>
          </div>
        </div>

        <nav style={{ paddingBottom: 24 }}>
          {navSections.map((sec, sIdx) => (
            <div key={sIdx} className="m42-nav-section">
              {sec.label && <div className="m42-nav-label">{sec.label}</div>}
              {sec.items.map(item => {
                const IconComponent = item.icon;
                const isActive = activeNav === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`m42-nav-item ${isActive ? "active" : ""}`}
                    onClick={() => setActiveNav(item.id)}
                  >
                    <IconComponent size={16} />
                    <span>{item.label}</span>
                    {item.count !== undefined && item.count > 0 && (
                      <span className="m42-nav-badge">{item.count}</span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
      </aside>

      {/* Main Container */}
      <div className="m42-main-container">
        {/* Top Header */}
        <header className="m42-header">
          <div className="m42-search-box">
            <Search size={15} color="var(--text-3)" />
            <input
              type="text"
              className="m42-search-input"
              placeholder="Search skins, icons, characters..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="m42-header-right">
            {/* Quick Theme Toggle Button */}
            <button
              type="button"
              className="m42-btn m42-btn-ghost"
              title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
              onClick={toggleTheme}
              style={{ padding: "6px 10px", display: "inline-flex", alignItems: "center", gap: 6 }}
            >
              {theme === "dark" ? <Sun size={15} style={{ color: "#FCD34D" }} /> : <Moon size={15} style={{ color: "var(--dark-teal)" }} />}
              <span style={{ fontSize: 11.5, fontWeight: 700 }}>{theme === "dark" ? "Light" : "Dark"}</span>
            </button>

            {currentUser && stats && (
              <div className="m42-cp-pill" title="Personal Collection Points">
                <span className="m42-cp-dot" />
                <span>{fmtNum(stats.user_cp)} / {fmtNum(stats.total_cp)} CP</span>
              </div>
            )}

            {currentUser ? (
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--cream)" }}>
                    {currentUser.username}
                  </div>
                  <div style={{ fontSize: 10, color: currentUser.role === "owner" ? "var(--peach)" : "var(--text-3)", textTransform: "uppercase", fontWeight: 700 }}>
                    {currentUser.role === "owner" ? "Owner / Curator" : "Collector"}
                  </div>
                </div>
                <button
                  type="button"
                  className="m42-btn m42-btn-ghost"
                  title="Sign Out"
                  onClick={handleLogout}
                  style={{ padding: "6px 10px" }}
                >
                  <LogOut size={16} />
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  className="m42-btn m42-btn-ghost"
                  onClick={() => { setAuthMode("login"); setAuthModalOpen(true); }}
                >
                  <LogIn size={14} /> Sign In
                </button>
                <button
                  type="button"
                  className="m42-btn m42-btn-primary"
                  onClick={() => { setAuthMode("register"); setAuthModalOpen(true); }}
                >
                  Register
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Dynamic Page Content */}
        <main className="m42-content">
          {loading && (!catalogue || Object.keys(catalogue).length === 0) ? (
            <div style={{ textAlign: "center", padding: "100px 20px" }}>
              <RefreshCw size={36} className="spin" color="var(--dark-teal)" style={{ margin: "0 auto 16px" }} />
              <h3 style={{ fontSize: 18, color: "var(--deep-teal)", fontWeight: 700, margin: "0 0 8px" }}>Loading Mafia42 Collection...</h3>
              <p style={{ fontSize: 13, color: "var(--text-muted)", margin: 0 }}>Fetching catalogue items and collection data.</p>
            </div>
          ) : loadError && (!catalogue || Object.keys(catalogue).length === 0) ? (
            <div style={{ textAlign: "center", padding: "60px 20px", background: "#FFFFFF", border: "1.5px solid #EF4444", borderRadius: 12, maxWidth: 520, margin: "60px auto", boxShadow: "0 1px 3px rgba(16, 43, 45, 0.05)" }}>
              <AlertCircle size={40} style={{ color: "#EF4444", margin: "0 auto 14px" }} />
              <h3 style={{ fontSize: 18, color: "var(--deep-teal)", fontWeight: 700, margin: "0 0 8px" }}>Unable to load catalogue</h3>
              <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 20 }}>{loadError}</p>
              <button type="button" className="m42-btn m42-btn-primary" onClick={loadInitialData}>
                <RefreshCw size={14} style={{ marginRight: 6 }} /> Retry Loading
              </button>
            </div>
          ) : (
            <>
              {activeNav === "home" && (
                <HomePage
              catalogue={catalogue}
              stats={stats}
              currentUser={currentUser}
              onNavigate={setActiveNav}
              onOpenAuth={() => setAuthModalOpen(true)}
              onOpenItem={(item, cat) => setFocusedItem({ item, category: cat })}
              collection={collection}
              onToggleOwned={handleToggleOwned}
            />
          )}

          {activeNav === "whatihave" && (
            <WhatIHavePage
              catalogue={catalogue}
              collection={collection}
              onOpenItem={(item, cat) => setFocusedItem({ item, category: cat })}
              onToggleOwned={handleToggleOwned}
              currentUser={currentUser}
              onOpenAuth={() => setAuthModalOpen(true)}
            />
          )}

          {activeNav === "profile" && (
            <ProfilePage
              currentUser={currentUser}
              stats={stats}
              onOpenAuth={() => setAuthModalOpen(true)}
            />
          )}

          {activeNav === "collection" && (
            <CollectionOverviewPage
              catalogue={catalogue}
              stats={stats}
              onNavigate={setActiveNav}
            />
          )}

          {activeNav === "gems" && (
            <GemsPage
              searchQuery={searchQuery}
              currentUser={currentUser}
              cards={catalogue.cards || []}
              onOpenAuth={() => setAuthModalOpen(true)}
              onRefreshStats={loadUserData}
            />
          )}

          {activeNav !== "gems" && Object.keys(CATEGORY_CONFIG).includes(activeNav) && (
            <CategoryItemsPage
              category={activeNav}
              items={catalogue[activeNav] || []}
              searchQuery={searchQuery}
              collection={collection}
              cards={catalogue.cards || []}
              currentUser={currentUser}
              onOpenItem={item => setFocusedItem({ item, category: activeNav })}
              onToggleOwned={handleToggleOwned}
              onAdminAdd={() => setAdminItemModal({ isOpen: true, mode: "create", category: activeNav, item: { category: activeNav } })}
              onAdminEdit={item => setAdminItemModal({ isOpen: true, mode: "edit", category: activeNav, item })}
              onAdminDelete={handleAdminDeleteItem}
              onMoveIcon={handleMoveIcon}
            />
          )}

          {activeNav === "statistics" && (
            <StatisticsPage stats={stats} catalogue={catalogue} collection={collection} />
          )}

          {activeNav === "goals" && (
            <GoalsPage
              goals={goals}
              currentUser={currentUser}
              onRefresh={loadUserData}
              onOpenAuth={() => setAuthModalOpen(true)}
            />
          )}

          {activeNav === "notes" && (
            <NotesPage
              notes={notes}
              currentUser={currentUser}
              onRefresh={loadUserData}
              onOpenAuth={() => setAuthModalOpen(true)}
            />
          )}

          {activeNav === "achievements" && (
            <AchievementsPage stats={stats} />
          )}

          {activeNav === "settings" && (
            <SettingsPage
              currentUser={currentUser}
              theme={theme}
              onToggleTheme={toggleTheme}
              onSetTheme={setTheme}
              onExport={() => api.exportCatalogue()}
            />
          )}

          {activeNav === "admin" && currentUser?.role === "owner" && (
            <AdminPage
              catalogue={catalogue}
              users={adminUsers}
              auditLogs={adminAuditLogs}
              activeTab={adminTab}
              onTabChange={setAdminTab}
              onAddItem={cat => setAdminItemModal({ isOpen: true, mode: "create", category: cat, item: { category: cat } })}
              onEditItem={(cat, item) => setAdminItemModal({ isOpen: true, mode: "edit", category: cat, item })}
              onDeleteItem={handleAdminDeleteItem}
              onToggleUserStatus={handleToggleUserStatus}
              onRefresh={loadAdminData}
            />
          )}

          {activeNav === "image_review" && (
            <ImageReviewPage
              currentUser={currentUser}
              onOpenAuth={() => setAuthModalOpen(true)}
            />
          )}
          </>
          )}

          {/* Unofficial Fan-Made Disclaimer Footer */}
          <AppFooter />
        </main>
      </div>

      {/* Focused Item View Modal */}
      {focusedItem && (
        <FocusedItemModal
          item={focusedItem.item}
          category={focusedItem.category}
          cards={catalogue.cards || []}
          skins={catalogue.skins || []}
          collection={collection}
          stats={stats}
          currentUser={currentUser}
          onRefreshCatalogue={loadCatalogue}
          isOwned={collection.owned_item_ids.includes(focusedItem.item.id)}
          onClose={() => setFocusedItem(null)}
          onToggleOwned={() => handleToggleOwned(focusedItem.item.id)}
          onSelectSkin={(skin: CatalogueItem) => setFocusedItem({ item: skin, category: "skins" })}
          onSelectCard={(card: CatalogueItem) => setFocusedItem({ item: card, category: "cards" })}
          onToggleSkinOwned={(skinId: string) => handleToggleOwned(skinId)}
        />
      )}

      {/* Auth Modal */}
      {authModalOpen && (
        <AuthModal
          mode={authMode}
          onModeChange={setAuthMode}
          form={authForm}
          onFormChange={setAuthForm}
          error={authError}
          onSubmit={handleAuthSubmit}
          onClose={() => setAuthModalOpen(false)}
        />
      )}

      {/* Admin Item Edit/Create Modal */}
      {adminItemModal.isOpen && (
        <AdminItemModal
          mode={adminItemModal.mode}
          category={adminItemModal.category}
          item={adminItemModal.item || {}}
          cards={catalogue.cards || []}
          onClose={() => setAdminItemModal({ isOpen: false, mode: "create", category: "skins" })}
          onSave={handleAdminSaveItem}
        />
      )}
    </div>
  );
}

/* =========================================================================
   COMPONENTS
   ========================================================================= */

function AppFooter() {
  return (
    <footer className="m42-footer">
      <div className="m42-footer-content">
        <h4 className="m42-footer-title m42-serif">About Mafia42 Collection Journal</h4>
        <p className="m42-footer-text">
          Mafia42 Collection Journal is an unofficial, fan-made collection tracking website created for players to organize and manage their collections.
        </p>
        <p className="m42-footer-text">
          This website is not affiliated with, endorsed by, sponsored by, or officially connected to the creators or publishers of Mafia42.
        </p>
        <p className="m42-footer-text">
          Mafia42-related names, logos, character artwork, skins, icons, and other game assets may belong to their respective rights holders. No ownership of third-party intellectual property is claimed.
        </p>
        <p className="m42-footer-text">
          Where practical, links to original sources or official reference pages may be provided for informational purposes. Attribution does not imply permission or ownership.
        </p>
        <p className="m42-footer-text">
          For copyright, attribution, or other intellectual property concerns, please contact the website administrator.
        </p>
        <div className="m42-footer-links">
          <span>Official Game Reference: </span>
          <a
            href="https://mafia42.com"
            target="_blank"
            rel="noopener noreferrer"
            className="m42-footer-link"
          >
            mafia42.com <ExternalLink size={12} style={{ display: 'inline', verticalAlign: 'middle', marginLeft: 2 }} />
          </a>
        </div>
      </div>
    </footer>
  );
}

function ProgressRing({ percent = 0, size = 110, stroke = 8 }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (Math.min(percent, 100) / 100) * c;
  return (
    <div className="m42-ring-wrap">
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={r} stroke="rgba(207,214,214,0.08)" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={r} stroke="var(--peach)" strokeWidth={stroke} fill="none"
          strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.8s cubic-bezier(.4,0,.2,1)" }}
        />
      </svg>
      <div className="m42-ring-inner">
        <div className="m42-ring-pct">{Math.round(percent)}%</div>
        <div className="m42-ring-label">Done</div>
      </div>
    </div>
  );
}

// 1. Home Page
function HomePage({ catalogue, stats, currentUser, onNavigate, onOpenAuth, onOpenItem, collection, onToggleOwned }: any) {
  const completionPct = stats ? stats.completion_percentage : 0;
  return (
    <div>
      <div className="m42-section-head">
        <div>
          <h1 className="m42-section-title m42-serif">Your Collection Journal</h1>
          <p className="m42-section-sub">
            {currentUser
              ? `Welcome back, ${currentUser.username}. Track your skins, icons, wallets, and nameplates with persistent personal data.`
              : "Browse the complete Mafia42 catalogue. Register or sign in to save your personal collection and CP."}
          </p>
        </div>
        {!currentUser && (
          <button type="button" className="m42-btn m42-btn-primary" onClick={onOpenAuth}>
            <LogIn size={15} /> Sign In to Save Collection
          </button>
        )}
      </div>

      {/* Top Overview Cards */}
      <div className="m42-stats-grid">
        <div className="m42-stat-card" style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <ProgressRing percent={completionPct} />
          <div>
            <div className="m42-stat-label" style={{ fontSize: 15, fontWeight: 700, color: "var(--deep-teal)", marginBottom: 4 }}>
              Collection Completion
            </div>
            <div className="m42-stat-sub">Across Skins, Gems, Frames &amp; NP</div>
          </div>
        </div>

        <div className="m42-stat-card">
          <div className="m42-stat-label">Total CP You Have</div>
          <div className="m42-stat-value">{stats ? fmtNum(stats.user_cp) : 0} CP</div>
          <div className="m42-stat-sub">Max Available: {stats ? fmtNum(stats.total_cp) : 0} CP</div>
        </div>

        <div className="m42-stat-card">
          <div className="m42-stat-label">Items Collected</div>
          <div className="m42-stat-value">{stats ? stats.owned_items : 0}</div>
          <div className="m42-stat-sub">Total Catalogue Items: {stats ? stats.total_items : 0}</div>
        </div>
      </div>

      {/* Category Cards */}
      <div style={{ marginTop: 32 }}>
        <h2 className="m42-section-title m42-serif" style={{ fontSize: 21, marginBottom: 16 }}>Collection Categories</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 16 }}>
          {Object.entries(CATEGORY_CONFIG).map(([catKey, cfg]) => {
            const items = catalogue[catKey] || [];
            const catStats = stats?.category_breakdown?.[catKey];
            const ownedCount = catStats ? catStats.owned : 0;
            const totalCount = items.length;
            const pct = totalCount > 0 ? (ownedCount / totalCount) * 100 : 0;

            return (
              <div
                key={catKey}
                className="m42-card"
                style={{ cursor: "pointer", transition: "transform 0.15s, border-color 0.15s" }}
                onClick={() => onNavigate(catKey)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 600, color: "var(--cream)" }}>{cfg.title}</div>
                    <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 2 }}>{cfg.subtitle}</div>
                  </div>
                  <span className="m42-nav-badge">{totalCount} items</span>
                </div>

                <div style={{ marginTop: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, color: "var(--text-2)", marginBottom: 6 }}>
                    <span>{ownedCount} Owned</span>
                    <span>{Math.round(pct)}%</span>
                  </div>
                  <div style={{ height: 6, background: "rgba(134,185,177,0.1)", borderRadius: 3, overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${pct}%`, background: "var(--peach)", borderRadius: 3, transition: "width 0.5s ease" }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// 2. What I Have Page
function WhatIHavePage({ catalogue, collection, onOpenItem, onToggleOwned, currentUser, onOpenAuth }: any) {
  const [selectedCat, setSelectedCat] = useState<string>("all");
  const [search, setSearch] = useState<string>("");

  if (!currentUser) {
    return (
      <div className="m42-card" style={{ textAlign: "center", padding: "64px 20px" }}>
        <FolderHeart size={48} color="var(--peach)" style={{ margin: "0 auto 16px" }} />
        <h2 className="m42-section-title m42-serif">Your Saved Collection</h2>
        <p className="m42-section-sub" style={{ maxWidth: 460, margin: "8px auto 24px" }}>
          Sign in to maintain your personal collection. Each user gets their own persistent database records that sync across devices.
        </p>
        <button type="button" className="m42-btn m42-btn-primary" onClick={onOpenAuth}>
          <LogIn size={15} /> Sign In or Register
        </button>
      </div>
    );
  }

  const ownedItems = useMemo(() => {
    const list: { item: CatalogueItem; category: string }[] = [];
    Object.entries(catalogue).forEach(([catKey, items]: any) => {
      if (selectedCat !== "all" && selectedCat !== catKey) return;
      items.forEach((item: CatalogueItem) => {
        if (collection.owned_item_ids.includes(item.id)) {
          if (!search || item.name.toLowerCase().includes(search.toLowerCase()) || (item.character && item.character.toLowerCase().includes(search.toLowerCase()))) {
            list.push({ item, category: catKey });
          }
        }
      });
    });
    return list;
  }, [catalogue, collection.owned_item_ids, selectedCat, search]);

  return (
    <div>
      <div className="m42-section-head">
        <div>
          <h1 className="m42-section-title m42-serif">What I Have</h1>
          <p className="m42-section-sub">Showing all {ownedItems.length} items in your personal collection.</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
        {["all", "skins", "icons", "wallets", "cp_wallets", "nameplates", "frames", "cards"].map(c => (
          <button
            key={c}
            type="button"
            className={`m42-btn ${selectedCat === c ? "m42-btn-primary" : "m42-btn-ghost"}`}
            onClick={() => setSelectedCat(c)}
            style={{ textTransform: "capitalize", fontSize: 12, padding: "6px 12px" }}
          >
            {c === "nameplates" ? "NP" : c === "cp_wallets" ? "CP Wallets" : c}
          </button>
        ))}
      </div>

      {ownedItems.length === 0 ? (
        <div className="m42-card" style={{ textAlign: "center", padding: "48px 20px" }}>
          <FolderHeart size={36} color="var(--text-3)" style={{ margin: "0 auto 12px" }} />
          <div style={{ fontSize: 15, color: "var(--cream)", fontWeight: 600 }}>No owned items matched</div>
          <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 4 }}>Browse catalogue categories and toggle "I Have" to track your items here.</div>
        </div>
      ) : (
        <div className="m42-items-grid">
          {ownedItems.map(({ item, category }) => {
            const isLogo = CATEGORY_CONFIG[category]?.isLogo;
            const imgSrc = isLogo ? (item.logo_image || item.image) : item.image;
            return (
              <div key={item.id} className="m42-logo-tile">
                <button type="button" className="m42-logo-button" onClick={() => onOpenItem(item, category)}>
                  {imgSrc ? <img src={imgSrc} alt="" loading="lazy" /> : <div className="m42-logo-placeholder">No image</div>}
                  <span className="m42-entry-status-badge">Owned</span>
                </button>
                <div className="m42-logo-name" title={item.name} onClick={() => onOpenItem(item, category)} style={{ cursor: "pointer" }}>{item.name}</div>
                <div className="m42-logo-meta">{category === "cp_wallets" ? (item.condition || "CP Wallet") : item.cp > 0 ? `${fmtNum(item.cp)} CP` : item.character || category}</div>
                <div className="m42-logo-actions">
                  {category === "cp_wallets" ? (
                    <span className="m42-owned-toggle checked" style={{ cursor: "default" }} title="Active CP Tier (automatically awarded based on total CP)">
                      <span>Active Tier</span>
                    </span>
                  ) : (
                    <label className="m42-owned-toggle checked" onClick={e => e.stopPropagation()}>
                      <input type="checkbox" checked={true} onChange={() => onToggleOwned(item.id)} />
                      <span>I Have</span>
                    </label>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// 3. Category Items Page (Skins, Icons, Wallets, NP, Frames, etc.)
function CategoryItemsPage({
  category, items, searchQuery, collection, cards, currentUser,
  onOpenItem, onToggleOwned, onAdminAdd, onAdminEdit, onAdminDelete, onMoveIcon
}: any) {
  const cfg = CATEGORY_CONFIG[category] || { title: category, singular: category, subtitle: "", isLogo: false };
  const isOwner = currentUser?.role === "owner";

  const filteredItems = useMemo(() => {
    return items.filter((item: CatalogueItem) => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return (
        item.name.toLowerCase().includes(q) ||
        (item.character && item.character.toLowerCase().includes(q)) ||
        (item.description && item.description.toLowerCase().includes(q))
      );
    });
  }, [items, searchQuery]);

  // Group skins by Card in Card catalogue order
  const skinGroups = useMemo(() => {
    if (category !== "skins") return null;

    const cardMap = new Map<string, CatalogueItem[]>();
    const uncategorized: CatalogueItem[] = [];

    // Ensure all known cards have a bucket in Card catalogue order
    for (const c of (cards || [])) {
      cardMap.set(c.id, []);
    }

    for (const skin of filteredItems) {
      if (skin.card_id && cardMap.has(skin.card_id)) {
        cardMap.get(skin.card_id)!.push(skin);
      } else {
        const matched = (cards || []).find((c: any) => c.character && c.character.toLowerCase() === (skin.character || "").toLowerCase());
        if (matched && cardMap.has(matched.id)) {
          cardMap.get(matched.id)!.push(skin);
        } else {
          uncategorized.push(skin);
        }
      }
    }

    const groups: { card: any; skins: CatalogueItem[] }[] = [];
    for (const c of (cards || [])) {
      const gSkins = cardMap.get(c.id) || [];
      if (gSkins.length > 0) {
        groups.push({ card: c, skins: gSkins });
      }
    }

    if (uncategorized.length > 0) {
      groups.push({
        card: { id: "uncategorized", name: "Uncategorized", logo_image: null, image: null },
        skins: uncategorized
      });
    }

    return groups;
  }, [category, filteredItems, cards]);

  const renderItemTile = (item: CatalogueItem, idx: number) => {
    const isOwned = collection.owned_item_ids.includes(item.id);
    const imgSrc = cfg.isLogo ? (item.logo_image || item.image) : item.image;
    const currentPosition = (items || []).findIndex((it: any) => it.id === item.id) + 1;
    const isSticker = category === "stickers";
    let stickerExtra: any = {};
    if (isSticker && item.extra) {
      try {
        stickerExtra = JSON.parse(item.extra);
      } catch (e) {}
    }

    return (
      <div key={item.id} className="m42-logo-tile">
        <button
          type="button"
          className="m42-logo-button"
          onClick={() => onOpenItem(item)}
          title={`View ${item.name}`}
        >
          {imgSrc ? (
            <img 
              src={imgSrc} 
              alt={item.name} 
              loading="lazy"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                if (category === "cards" && !target.src.includes('/assets/cards/card_')) {
                  target.src = `/assets/cards/card_${item.id}.jpg`;
                } else if (category === "skins" && !target.src.includes('/assets/skins/skin_')) {
                  target.src = `/assets/skins/skin_${item.id}.jpg`;
                } else {
                  target.style.display = 'none';
                  const fb = target.parentElement?.querySelector('.m42-logo-placeholder') as HTMLElement;
                  if (fb) fb.style.display = 'flex';
                }
              }}
            />
          ) : null}
          <div className="m42-logo-placeholder" style={{ display: imgSrc ? 'none' : 'flex' }}>
            {item.name ? item.name.slice(0, 3).toUpperCase() : "IMG"}
          </div>
          {(category === "cards" || category === "skins") && item.logo_image && (
            <span
              className="m42-card-logo-badge"
              title={`${item.name} Logo`}
            >
              <img
                src={item.logo_image}
                alt=""
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  if (category === "cards" && !target.src.includes('/assets/cards/card_logo_')) {
                    target.src = `/assets/cards/card_logo_${item.id}.jpg`;
                  } else if (category === "skins" && !target.src.includes('/assets/skins/skin_logo_')) {
                    target.src = `/assets/skins/skin_logo_${item.id}.jpg`;
                  }
                }}
              />
            </span>
          )}
          {isOwned && <span className="m42-entry-status-badge">Owned</span>}
          {category === "icons" && isOwner && (
            <span
              style={{
                position: "absolute",
                bottom: 4,
                left: 4,
                background: "rgba(16, 43, 45, 0.85)",
                color: "#FFFFFF",
                fontSize: 10,
                fontWeight: 700,
                padding: "1px 5px",
                borderRadius: 4,
                border: "1px solid rgba(227, 239, 235, 0.3)"
              }}
              title={`Position #${currentPosition}`}
            >
              #{currentPosition}
            </span>
          )}
        </button>

        <div className="m42-logo-name" title={item.name} onClick={() => onOpenItem(item)} style={{ cursor: "pointer" }}>{item.name || "Unnamed"}</div>
        <div className="m42-logo-meta">
          {category === "cp_wallets" ? (
            item.condition || ""
          ) : isSticker ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 3, alignItems: "center" }}>
              <span style={{
                fontSize: 10.5,
                fontWeight: 700,
                padding: "1px 6px",
                borderRadius: 4,
                background: stickerExtra.acquisition_method === "Shop" ? "rgba(224, 159, 62, 0.15)" : "rgba(23, 63, 67, 0.1)",
                color: stickerExtra.acquisition_method === "Shop" ? "#9c680c" : "var(--dark-teal)",
                border: stickerExtra.acquisition_method === "Shop" ? "1px solid rgba(224, 159, 62, 0.3)" : "1px solid rgba(23, 63, 67, 0.2)"
              }}>
                {stickerExtra.acquisition_method === "Shop"
                  ? `Shop (${stickerExtra.shop_price ? fmtNum(stickerExtra.shop_price) + " Lunas" : "Lunas"})`
                  : "Event"}
              </span>
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                {fmtNum(item.cp)} CP • {(stickerExtra.sticker_images || []).length} stickers
              </span>
            </div>
          ) : item.cp > 0 ? (
            `${fmtNum(item.cp)} CP`
          ) : (
            item.character || item.condition || ""
          )}
        </div>

        <div className="m42-logo-actions">
          {isOwner && (
            <>
              {category === "icons" && onMoveIcon && (
                <span style={{ display: "inline-flex", gap: 2, marginRight: 2 }}>
                  <button
                    type="button"
                    className="m42-btn m42-btn-ghost"
                    style={{ padding: "3px 4px" }}
                    title="Move Previous (Left)"
                    onClick={e => { e.stopPropagation(); onMoveIcon(item.id, "prev"); }}
                  >
                    <ArrowLeft size={11} />
                  </button>
                  <button
                    type="button"
                    className="m42-btn m42-btn-ghost"
                    style={{ padding: "3px 4px" }}
                    title="Move Next (Right)"
                    onClick={e => { e.stopPropagation(); onMoveIcon(item.id, "next"); }}
                  >
                    <ArrowRight size={11} />
                  </button>
                  <button
                    type="button"
                    className="m42-btn m42-btn-ghost"
                    style={{ padding: "3px 5px", fontSize: 10, fontWeight: 700, color: "var(--peach)" }}
                    title="Move to specific position"
                    onClick={e => {
                      e.stopPropagation();
                      const target = prompt(`Move icon "${item.name}" to position (1 - ${items.length}):`, String(currentPosition));
                      if (target) {
                        const pos = parseInt(target, 10);
                        if (!isNaN(pos) && pos >= 1 && pos <= items.length) {
                          onMoveIcon(item.id, undefined, pos);
                        } else {
                          alert(`Target position must be between 1 and ${items.length}`);
                        }
                      }
                    }}
                  >
                    #
                  </button>
                </span>
              )}
              <button
                type="button"
                className="m42-btn m42-btn-ghost"
                style={{ padding: "4px 5px" }}
                title="Edit Item"
                onClick={() => onAdminEdit(item)}
              >
                <Pencil size={11} />
              </button>
              <button
                type="button"
                className="m42-btn m42-btn-ghost"
                style={{ padding: "4px 5px", color: "#ff9999" }}
                title="Delete Item"
                onClick={() => onAdminDelete(item.id)}
              >
                <Trash2 size={11} />
              </button>
            </>
          )}
          {category === "cp_wallets" ? (
            <span
              className={`m42-owned-toggle ${isOwned ? "checked" : ""}`}
              style={{ cursor: "default", opacity: isOwned ? 1 : 0.6 }}
              title={isOwned ? "Active CP Tier (automatically awarded based on total CP)" : `Requires ${item.condition}`}
              onClick={e => e.stopPropagation()}
            >
              <span>{isOwned ? "Active Tier" : "Locked"}</span>
            </span>
          ) : (
            <label className={`m42-owned-toggle ${isOwned ? "checked" : ""}`} onClick={e => e.stopPropagation()}>
              <input
                type="checkbox"
                checked={isOwned}
                onChange={() => onToggleOwned(item.id)}
              />
              <span>I Have</span>
            </label>
          )}
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="m42-section-head">
        <div>
          <h1 className="m42-section-title m42-serif">{cfg.title}</h1>
          <p className="m42-section-sub">
            {cfg.subtitle} ({filteredItems.length} items)
            {category === "icons" && isOwner && " • Use ◄ ► or # to rearrange icons"}
          </p>
        </div>
        {isOwner && (
          <button type="button" className="m42-btn m42-btn-primary" onClick={onAdminAdd}>
            <Plus size={15} /> Add {cfg.singular}
          </button>
        )}
      </div>

      {filteredItems.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", background: "#FFFFFF", border: "1px solid var(--border-subtle)", borderRadius: 12, margin: "20px 0", boxShadow: "0 1px 3px rgba(16, 43, 45, 0.05)" }}>
          <FolderHeart size={40} style={{ color: "var(--dark-teal)", margin: "0 auto 12px" }} />
          <h3 style={{ fontSize: 18, color: "var(--deep-teal)", fontWeight: 700, margin: "0 0 6px" }}>
            {searchQuery ? `No ${cfg.title} match "${searchQuery}"` : `No items in ${cfg.title}`}
          </h3>
          <p style={{ fontSize: 13, color: "var(--text-muted)", margin: 0 }}>
            {searchQuery ? "Try searching for a different character or item name." : "Items will appear here once added to the catalogue."}
          </p>
        </div>
      ) : category === "skins" && skinGroups ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
          {skinGroups.map(grp => {
            const groupOwnedCount = grp.skins.filter(s => collection.owned_item_ids.includes(s.id)).length;
            const cardLogo = grp.card.logo_image || grp.card.image;
            return (
              <div key={grp.card.id} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 16px",
                  background: "var(--surf-white)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: 10,
                  boxShadow: "0 1px 3px rgba(16, 43, 45, 0.04)"
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    {cardLogo ? (
                      <img
                        src={cardLogo}
                        alt=""
                        style={{
                          width: 28,
                          height: 28,
                          borderRadius: 6,
                          objectFit: "contain",
                          background: "var(--tile-bg)",
                          border: "1px solid var(--border-subtle)",
                          padding: 2
                        }}
                      />
                    ) : null}
                    <h3 style={{ fontSize: 17, fontWeight: 700, color: "var(--deep-teal)", margin: 0 }}>
                      {grp.card.name}
                    </h3>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", background: "var(--tile-bg)", border: "1px solid var(--border-subtle)", padding: "3px 10px", borderRadius: 12 }}>
                      {grp.skins.length} {grp.skins.length === 1 ? "Skin" : "Skins"}
                    </span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: "var(--dark-teal)", background: "rgba(23, 63, 67, 0.1)", border: "1px solid rgba(23, 63, 67, 0.2)", padding: "3px 10px", borderRadius: 12 }}>
                      {groupOwnedCount} Owned
                    </span>
                  </div>
                </div>

                <div className="m42-items-grid m42-grid-skins">
                  {grp.skins.map((skin, idx) => renderItemTile(skin, idx))}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className={`m42-items-grid m42-grid-${category}`}>
          {filteredItems.map((item: CatalogueItem, idx: number) => renderItemTile(item, idx))}
        </div>
      )}
    </div>
  );
}

// 4. Focused Item View Modal (Supports Wallets with 3 detail images and Card-Skin associations!)
function FocusedItemModal({
  item, category, cards, skins, collection, stats, isOwned, currentUser, onRefreshCatalogue,
  onClose, onToggleOwned, onSelectSkin, onSelectCard, onToggleSkinOwned
}: any) {
  const isWallet = category === "wallets" || category === "wallet" || category === "cp_wallets";
  const isCPWallet = category === "cp_wallets";
  const isSkin = category === "skins" || category === "skin";
  const isCard = category === "cards" || category === "card";
  const isSticker = category === "stickers" || category === "sticker";
  const parentCard = isSkin ? (cards || []).find((c: any) => c.id === item.card_id || (c.character && c.character === item.character)) : null;

  let initialStickerExtra: any = {};
  try {
    if (item.extra) initialStickerExtra = JSON.parse(item.extra);
  } catch (e) {}

  const [stickerExtra, setStickerExtra] = useState(initialStickerExtra);
  const [newStickerUrl, setNewStickerUrl] = useState("");
  const [uploadingSticker, setUploadingSticker] = useState(false);
  const isOwner = currentUser?.role === "owner";

  async function handleAddStickerImage(url: string) {
    if (!url.trim()) return;
    const currentImgs = stickerExtra.sticker_images || [];
    const nextImgs = [...currentImgs, url.trim()];
    const nextExtra = { ...stickerExtra, sticker_images: nextImgs };
    try {
      await api.updateCatalogueItem(item.id, { extra: JSON.stringify(nextExtra) });
      setStickerExtra(nextExtra);
      setNewStickerUrl("");
      if (onRefreshCatalogue) onRefreshCatalogue();
    } catch (err: any) {
      alert("Failed to add sticker: " + err.message);
    }
  }

  async function handleDeleteStickerImage(indexToDelete: number) {
    if (!confirm("Remove this sticker image from the pack?")) return;
    const currentImgs = stickerExtra.sticker_images || [];
    const nextImgs = currentImgs.filter((_: any, idx: number) => idx !== indexToDelete);
    const nextExtra = { ...stickerExtra, sticker_images: nextImgs };
    try {
      await api.updateCatalogueItem(item.id, { extra: JSON.stringify(nextExtra) });
      setStickerExtra(nextExtra);
      if (onRefreshCatalogue) onRefreshCatalogue();
    } catch (err: any) {
      alert("Failed to delete sticker: " + err.message);
    }
  }

  async function handleUploadStickerFile(file: File) {
    setUploadingSticker(true);
    try {
      const res = await api.uploadCatalogueImage(file, "stickers");
      await handleAddStickerImage(res.url);
    } catch (err: any) {
      alert("Failed to upload sticker: " + err.message);
    } finally {
      setUploadingSticker(false);
    }
  }

  const associatedSkins = useMemo(() => {
    if (!isCard) return [];
    return (skins || []).filter((s: any) =>
      s.card_id === item.id || (!s.card_id && item.character && s.character === item.character)
    );
  }, [isCard, item, skins]);

  const [selectedWalletImage, setSelectedWalletImage] = useState<string | null>(null);

  const mainImageSrc = isWallet && selectedWalletImage 
    ? selectedWalletImage 
    : (isWallet ? (item.logo_image || item.image) : (item.image || item.logo_image));

  return (
    <div className="m42-modal-overlay" onClick={onClose}>
      <div className="m42-focused-card" style={{ maxWidth: (isCard && associatedSkins.length > 0) || isSticker ? 820 : 700 }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <button type="button" className="m42-btn m42-btn-ghost" onClick={onClose}>
            <ArrowLeft size={15} /> Back
          </button>
          <button type="button" className="m42-btn m42-btn-ghost" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="m42-focused-layout">
          <div>
            <div className={`m42-focused-image ${isWallet && selectedWalletImage ? "wallet-expanded" : ""}`} style={{ position: "relative" }}>
              {mainImageSrc ? (
                <img 
                  src={mainImageSrc} 
                  alt={item.name} 
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    if (isCard && !target.src.includes('/assets/cards/card_')) {
                      target.src = `/assets/cards/card_${item.id}.jpg`;
                    } else if (isSkin && !target.src.includes('/assets/skins/skin_')) {
                      target.src = `/assets/skins/skin_${item.id}.jpg`;
                    } else {
                      target.style.display = 'none';
                      const fb = target.parentElement?.querySelector('.m42-image-placeholder') as HTMLElement;
                      if (fb) fb.style.display = 'flex';
                    }
                  }}
                />
              ) : null}
              <div className="m42-image-placeholder" style={{ display: mainImageSrc ? 'none' : 'flex' }}>
                No image available
              </div>
              {(isCard || isSkin) && item.logo_image && (
                <div
                  style={{
                    position: "absolute",
                    top: 10,
                    left: 10,
                    width: 44,
                    height: 44,
                    borderRadius: 8,
                    background: "var(--surf-white)",
                    border: "1px solid var(--border-subtle)",
                    overflow: "hidden",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.2)",
                    zIndex: 5
                  }}
                  title={`${item.name} Logo`}
                >
                  <img
                    src={item.logo_image}
                    alt=""
                    style={{ width: "100%", height: "100%", objectFit: "contain" }}
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      if (isCard && !target.src.includes('/assets/cards/card_logo_')) {
                        target.src = `/assets/cards/card_logo_${item.id}.jpg`;
                      } else if (isSkin && !target.src.includes('/assets/skins/skin_logo_')) {
                        target.src = `/assets/skins/skin_logo_${item.id}.jpg`;
                      }
                    }}
                  />
                </div>
              )}
            </div>

            {/* Wallet 3 Detailed Images with Interactive Tab Switcher */}
            {isWallet && item.wallet_images && item.wallet_images.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6, fontSize: 11, color: "var(--text-3)" }}>
                  <span>{selectedWalletImage ? "Expanded View" : "Click view to expand:"}</span>
                  {selectedWalletImage && (
                    <button
                      type="button"
                      className="m42-btn m42-btn-ghost"
                      style={{ padding: "1px 6px", fontSize: 10, color: "var(--peach)" }}
                      onClick={() => setSelectedWalletImage(null)}
                    >
                      Show Logo
                    </button>
                  )}
                </div>
                <div className="m42-wallet-detail-images">
                  {[0, 1, 2].map(i => {
                    const detailImg = item.wallet_images?.[i];
                    const tabLabels = ["Profile View", "Cards View", "Badges View"];
                    const isActive = selectedWalletImage === detailImg && !!detailImg;
                    return (
                      <div
                        key={i}
                        className={`m42-wallet-detail-image ${isActive ? "active" : ""}`}
                        onClick={() => detailImg && setSelectedWalletImage(isActive ? null : detailImg)}
                        title={detailImg ? `Click to view ${tabLabels[i]}` : `Detail ${i + 1}`}
                      >
                        {detailImg ? (
                          <>
                            <img src={detailImg} alt={tabLabels[i]} />
                            <span className="m42-wallet-tab-pill">{`Tab ${i + 1}`}</span>
                          </>
                        ) : (
                          <span>Image {i + 1}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {!isCPWallet && item.cp > 0 && (
              <div style={{ marginTop: 14, textAlign: "center", fontSize: 13, color: "var(--cream)", fontWeight: 600 }}>
                {fmtNum(item.cp)} CP
              </div>
            )}
          </div>

          <div>
            <div className="m42-focused-kicker" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {isCard && item.logo_image && (
                <img
                  src={item.logo_image}
                  alt=""
                  style={{ width: 20, height: 20, borderRadius: 4, objectFit: "contain", verticalAlign: "middle" }}
                />
              )}
              <span>{isSkin ? "Skin" : isCard ? "Card / Role" : isCPWallet ? "CP Wallet" : isWallet ? "Wallet" : isSticker ? "Sticker Pack" : category === "speech_bubbles" ? "Speech Bubble" : category}</span>
            </div>
            <h2 className="m42-focused-heading">{item.name}</h2>
            {isCPWallet && item.condition && (
              <div style={{ color: "var(--peach)", fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
                Required: {item.condition}
              </div>
            )}

            {isSkin && (
              <div style={{ marginBottom: 12, fontSize: 13, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span style={{ color: "var(--peach)" }}>
                  Character Card: {parentCard ? parentCard.name : (item.character || "Unassigned")}
                </span>
                {parentCard && (
                  <button
                    type="button"
                    className="m42-btn m42-btn-ghost"
                    style={{ padding: "2px 8px", fontSize: 11 }}
                    onClick={() => onSelectCard && onSelectCard(parentCard)}
                  >
                    View Card <ArrowRight size={12} />
                  </button>
                )}
              </div>
            )}

            <div className="m42-focused-pills">
              <span className="m42-focused-pill" style={{ background: isOwned ? "rgba(134,185,177,0.2)" : "var(--surf-2)" }}>
                {isCPWallet ? (isOwned ? "★ Active CP Tier" : "Locked Tier") : (isOwned ? "I Have This" : "Not Owned")}
              </span>
              {item.rarity && <span className="m42-focused-pill">Rarity: {item.rarity}</span>}
              {item.condition && <span className="m42-focused-pill">Condition: {item.condition}</span>}
              {isSticker && (
                <>
                  <span className="m42-focused-pill" style={{
                    background: stickerExtra.acquisition_method === "Shop" ? "rgba(224, 159, 62, 0.15)" : "rgba(23, 63, 67, 0.1)",
                    color: stickerExtra.acquisition_method === "Shop" ? "#9c680c" : "var(--dark-teal)",
                    border: stickerExtra.acquisition_method === "Shop" ? "1px solid rgba(224, 159, 62, 0.3)" : "1px solid rgba(23, 63, 67, 0.2)"
                  }}>
                    {stickerExtra.acquisition_method === "Shop"
                      ? `Obtained from Shop (${stickerExtra.shop_price ? fmtNum(stickerExtra.shop_price) + " Lunas" : "Lunas"})`
                      : "Obtained from Event"}
                  </span>
                  <span className="m42-focused-pill">
                    {(stickerExtra.sticker_images || []).length} Stickers
                  </span>
                </>
              )}
            </div>

            {item.description && (
              <div className="m42-focused-copy">{item.description}</div>
            )}

            <div style={{ marginTop: 24 }}>
              {isCPWallet ? (
                <div style={{
                  padding: "14px 18px",
                  borderRadius: 8,
                  background: isOwned ? "rgba(134,185,177,0.15)" : "var(--surf-2)",
                  border: `1px solid ${isOwned ? "var(--accent)" : "var(--line)"}`,
                  textAlign: "center"
                }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: isOwned ? "var(--accent)" : "var(--text-2)" }}>
                    {isOwned ? "★ Active Collection Point Tier" : "Locked CP Tier Wallet"}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--cream)", marginTop: 6 }}>
                    {isOwned
                      ? `Automatically unlocked for your account (${stats ? fmtNum(stats.user_cp) : 0} CP earned)`
                      : `Requires ${item.condition || "higher CP"}. Current total: ${stats ? fmtNum(stats.user_cp) : 0} CP`}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 4 }}>
                    CP Tier Wallets are awarded automatically and cannot be manually toggled.
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  className={`m42-btn ${isOwned ? "m42-btn-danger" : "m42-btn-primary"}`}
                  onClick={onToggleOwned}
                  style={{ width: "100%", justifyContent: "center", padding: "10px 16px" }}
                >
                  {isOwned ? "Remove from My Collection" : "Mark as Owned (I Have This)"}
                </button>
              )}
            </div>

            {/* Associated Skins Section for Cards */}
            {isCard && (
              <div style={{ marginTop: 22, borderTop: "1px solid var(--line)", paddingTop: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <h3 style={{ fontSize: 14, color: "var(--cream)", fontWeight: 600 }}>
                    Associated Skins ({associatedSkins.length})
                  </h3>
                  <span style={{ fontSize: 11, color: "var(--text-3)" }}>Independent ownership</span>
                </div>
                {associatedSkins.length === 0 ? (
                  <div style={{ fontSize: 12, color: "var(--text-3)", fontStyle: "italic" }}>
                    No skins currently linked to this character card.
                  </div>
                ) : (
                  <div style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
                    gap: 10,
                    maxHeight: 250,
                    overflowY: "auto",
                    paddingRight: 4
                  }}>
                    {associatedSkins.map((s: any) => {
                      const skinOwned = collection?.owned_item_ids?.includes(s.id);
                      const skinImg = s.logo_image || s.image;
                      return (
                        <div
                          key={s.id}
                          style={{
                            background: "var(--surf-2)",
                            border: skinOwned ? "1px solid var(--peach)" : "1px solid var(--line)",
                            borderRadius: 8,
                            padding: 8,
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            textAlign: "center"
                          }}
                        >
                          <button
                            type="button"
                            style={{
                              background: "none",
                              border: "none",
                              cursor: "pointer",
                              width: "100%",
                              display: "flex",
                              flexDirection: "column",
                              alignItems: "center",
                              padding: 0
                            }}
                            onClick={() => onSelectSkin && onSelectSkin(s)}
                            title={`View details for ${s.name}`}
                          >
                            <div style={{ width: 56, height: 56, borderRadius: 6, overflow: "hidden", background: "var(--tile-bg)", border: "1px solid var(--tile-border)", marginBottom: 6 }}>
                              {skinImg ? (
                                <img src={skinImg} alt={s.name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                              ) : (
                                <div style={{ fontSize: 10, color: "var(--text-3)", paddingTop: 20 }}>No img</div>
                              )}
                            </div>
                            <span style={{ fontSize: 11, color: "var(--cream)", fontWeight: 500, maxWidth: 115, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {s.name}
                            </span>
                            {s.cp > 0 && (
                              <span style={{ fontSize: 10, color: "var(--peach)", marginTop: 2 }}>
                                {fmtNum(s.cp)} CP
                              </span>
                            )}
                          </button>
                          <label
                            className={`m42-owned-toggle ${skinOwned ? "checked" : ""}`}
                            style={{ marginTop: 6, fontSize: 10, padding: "2px 6px" }}
                            onClick={e => e.stopPropagation()}
                          >
                            <input
                              type="checkbox"
                              checked={skinOwned}
                              onChange={() => onToggleSkinOwned && onToggleSkinOwned(s.id)}
                            />
                            <span>{skinOwned ? "Owned" : "I Have"}</span>
                          </label>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Sticker Pack Items Grid */}
            {isSticker && (
              <div style={{ marginTop: 22, borderTop: "1px solid var(--line)", paddingTop: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <h3 style={{ fontSize: 14, color: "var(--cream)", fontWeight: 600, margin: 0 }}>
                    Stickers in this Pack ({(stickerExtra.sticker_images || []).length})
                  </h3>
                  <span style={{ fontSize: 11, color: "var(--text-3)" }}>Unlimited by design</span>
                </div>

                {(stickerExtra.sticker_images || []).length === 0 ? (
                  <div style={{ fontSize: 12, color: "var(--text-3)", fontStyle: "italic", padding: "14px 0" }}>
                    No sticker images in this pack yet.
                  </div>
                ) : (
                  <div className="m42-sticker-grid">
                    {(stickerExtra.sticker_images || []).map((imgUrl: string, idx: number) => (
                      <div key={idx} className="m42-sticker-item">
                        <img src={imgUrl} alt={`Sticker ${idx + 1}`} loading="lazy" />
                        {isOwner && (
                          <button
                            type="button"
                            className="m42-sticker-delete-btn"
                            onClick={() => handleDeleteStickerImage(idx)}
                            title="Remove sticker image"
                          >
                            ×
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Owner controls to add more sticker images */}
                {isOwner && (
                  <div style={{ marginTop: 14, padding: "12px", background: "var(--surf-2)", border: "1px solid var(--line)", borderRadius: 8 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "var(--cream)", marginBottom: 8 }}>
                      Owner Controls: Add Sticker Image
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <input
                        type="text"
                        className="m42-input"
                        placeholder="Paste sticker image URL..."
                        value={newStickerUrl}
                        onChange={e => setNewStickerUrl(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            handleAddStickerImage(newStickerUrl);
                          }
                        }}
                        style={{ fontSize: 12 }}
                      />
                      <button
                        type="button"
                        className="m42-btn m42-btn-primary"
                        onClick={() => handleAddStickerImage(newStickerUrl)}
                        style={{ fontSize: 12, padding: "6px 12px", whiteSpace: "nowrap" }}
                      >
                        <Plus size={14} /> Add
                      </button>
                      <label className="m42-btn m42-btn-ghost" style={{ fontSize: 12, padding: "6px 10px", cursor: "pointer", whiteSpace: "nowrap" }}>
                        <Upload size={14} /> {uploadingSticker ? "..." : "Upload"}
                        <input
                          type="file"
                          accept="image/*"
                          style={{ display: "none" }}
                          onChange={e => e.target.files?.[0] && handleUploadStickerFile(e.target.files[0])}
                        />
                      </label>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// 5. Auth Modal
function AuthModal({ mode, onModeChange, form, onFormChange, error, onSubmit, onClose }: any) {
  return (
    <div className="m42-modal-overlay" onClick={onClose}>
      <div className="m42-card" style={{ width: "100%", maxWidth: 420 }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h2 className="m42-section-title m42-serif" style={{ fontSize: 22 }}>
            {mode === "login" ? "Sign In to Your Journal" : "Create Collector Account"}
          </h2>
          <button type="button" className="m42-btn m42-btn-ghost" onClick={onClose}><X size={18} /></button>
        </div>

        {error && (
          <div style={{ background: "rgba(220,80,80,0.15)", border: "1.5px solid #EF4444", borderRadius: 8, padding: "10px 14px", color: "#000000", fontWeight: 700, fontSize: 13, marginBottom: 16 }}>
            {error}
          </div>
        )}

        <form onSubmit={onSubmit}>
          <div className="m42-form-group">
            <label className="m42-label">{mode === "login" ? "Username or Email" : "Username"}</label>
            <input
              type="text"
              className="m42-input"
              required
              value={form.username}
              onChange={e => onFormChange({ ...form, username: e.target.value })}
            />
          </div>

          {mode === "register" && (
            <div className="m42-form-group">
              <label className="m42-label">Email Address</label>
              <input
                type="email"
                className="m42-input"
                required
                value={form.email}
                onChange={e => onFormChange({ ...form, email: e.target.value })}
              />
            </div>
          )}

          <div className="m42-form-group">
            <label className="m42-label">Password</label>
            <input
              type="password"
              className="m42-input"
              required
              value={form.password}
              onChange={e => onFormChange({ ...form, password: e.target.value })}
            />
          </div>

          <button type="submit" className="m42-btn m42-btn-primary" style={{ width: "100%", justifyContent: "center", padding: "10px 16px", marginTop: 8 }}>
            {mode === "login" ? "Sign In" : "Register Account"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: 18, fontSize: 12.5, color: "var(--text-3)" }}>
          {mode === "login" ? (
            <span>Don't have an account? <button type="button" style={{ background: "none", border: "none", color: "var(--peach)", cursor: "pointer", fontWeight: 600 }} onClick={() => onModeChange("register")}>Register</button></span>
          ) : (
            <span>Already registered? <button type="button" style={{ background: "none", border: "none", color: "var(--peach)", cursor: "pointer", fontWeight: 600 }} onClick={() => onModeChange("login")}>Sign In</button></span>
          )}
        </div>
      </div>
    </div>
  );
}

// 6. Admin Item Modal (Owner Only)
function AdminItemModal({ mode, category, item, cards, onClose, onSave }: any) {
  const [formData, setFormData] = useState<Partial<CatalogueItem>>({
    id: item.id || "",
    category: item.category || category,
    name: item.name || "",
    character: item.character || "",
    card_id: item.card_id || "",
    cp: item.cp || 0,
    description: item.description || "",
    condition: item.condition || "",
    image: item.image || "",
    logo_image: item.logo_image || "",
    wallet_images: item.wallet_images || ["", "", ""],
  });
  const [uploading, setUploading] = useState<boolean>(false);

  let initExtra: any = {};
  try {
    if (item.extra) initExtra = JSON.parse(item.extra);
  } catch (e) {}

  const [acquisitionMethod, setAcquisitionMethod] = useState<string>(initExtra.acquisition_method || "Event");
  const [shopPrice, setShopPrice] = useState<number | string>(initExtra.shop_price ?? 500);
  const [stickerImagesText, setStickerImagesText] = useState<string>(
    (initExtra.sticker_images || []).join("\n")
  );

  const isWallet = (formData.category || category) === "wallets";
  const isSticker = (formData.category || category) === "stickers";

  async function handleFileUpload(file: File, targetField: "image" | "logo_image" | number) {
    setUploading(true);
    try {
      const res = await api.uploadCatalogueImage(file, formData.category || category);
      if (typeof targetField === "number") {
        const next = [...(formData.wallet_images || ["", "", ""])];
        next[targetField] = res.url;
        setFormData(prev => ({ ...prev, wallet_images: next }));
      } else {
        setFormData(prev => ({ ...prev, [targetField]: res.url }));
      }
    } catch (err: any) {
      alert("Failed to upload image: " + err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleStickerUpload(file: File) {
    setUploading(true);
    try {
      const res = await api.uploadCatalogueImage(file, "stickers");
      setStickerImagesText(prev => (prev ? prev + "\n" + res.url : res.url));
      if (!formData.image) {
        setFormData(prev => ({ ...prev, image: res.url, logo_image: res.url }));
      }
    } catch (err: any) {
      alert("Failed to upload: " + err.message);
    } finally {
      setUploading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const finalData = { ...formData };
    if (isSticker) {
      const urls = stickerImagesText
        .split("\n")
        .map(s => s.trim())
        .filter(Boolean);
      finalData.extra = JSON.stringify({
        acquisition_method: acquisitionMethod,
        shop_price: acquisitionMethod === "Shop" ? Number(shopPrice) || 0 : null,
        sticker_images: urls,
      });
      if (!finalData.image && urls.length > 0) {
        finalData.image = urls[0];
      }
      if (!finalData.logo_image && urls.length > 0) {
        finalData.logo_image = urls[0];
      }
    }
    onSave(finalData);
  }

  return (
    <div className="m42-modal-overlay" onClick={onClose}>
      <div className="m42-card" style={{ width: "100%", maxWidth: 600, maxHeight: "90vh", overflowY: "auto" }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h2 className="m42-section-title m42-serif" style={{ fontSize: 21 }}>
            {mode === "create" ? `Add New ${formData.category}` : `Edit ${formData.name}`}
          </h2>
          <button type="button" className="m42-btn m42-btn-ghost" onClick={onClose}><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="m42-form-group">
            <label className="m42-label">Category</label>
            <select
              className="m42-select"
              value={formData.category}
              onChange={e => setFormData({ ...formData, category: e.target.value })}
            >
              {Object.keys(CATEGORY_CONFIG).map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          <div className="m42-form-group">
            <label className="m42-label">Item Name</label>
            <input
              type="text"
              className="m42-input"
              required
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div className="m42-form-group">
              <label className="m42-label">CP (Collection Points)</label>
              <input
                type="number"
                className="m42-input"
                value={formData.cp}
                onChange={e => setFormData({ ...formData, cp: parseInt(e.target.value) || 0 })}
              />
            </div>

            <div className="m42-form-group">
              <label className="m42-label">Character / Role</label>
              <input
                type="text"
                className="m42-input"
                value={formData.character}
                onChange={e => setFormData({ ...formData, character: e.target.value })}
              />
            </div>
          </div>

          {((formData.category || category) === "skins") && (
            <div className="m42-form-group">
              <label className="m42-label">Associated Character Card</label>
              <select
                className="m42-select"
                value={formData.card_id || ""}
                onChange={e => {
                  const selId = e.target.value;
                  const selCard = (cards || []).find((c: any) => c.id === selId);
                  setFormData(prev => ({
                    ...prev,
                    card_id: selId,
                    character: selCard ? selCard.name : prev.character,
                  }));
                }}
              >
                <option value="">-- No Card / Unassigned --</option>
                {(cards || []).map((c: any) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.id})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Sticker Pack Specific Settings */}
          {isSticker && (
            <div style={{ padding: 14, background: "var(--surf-2)", border: "1px solid var(--line)", borderRadius: 8, marginBottom: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "var(--cream)", marginBottom: 12 }}>
                Sticker Pack Settings
              </div>
              
              <div style={{ display: "grid", gridTemplateColumns: acquisitionMethod === "Shop" ? "1fr 1fr" : "1fr", gap: 14, marginBottom: 14 }}>
                <div className="m42-form-group" style={{ margin: 0 }}>
                  <label className="m42-label">Acquisition Method</label>
                  <select
                    className="m42-select"
                    value={acquisitionMethod}
                    onChange={e => setAcquisitionMethod(e.target.value)}
                  >
                    <option value="Event">Event (Obtained from Event)</option>
                    <option value="Shop">Shop (Obtained from Shop)</option>
                  </select>
                </div>

                {acquisitionMethod === "Shop" && (
                  <div className="m42-form-group" style={{ margin: 0 }}>
                    <label className="m42-label">Shop Purchase Price (Lunas)</label>
                    <input
                      type="number"
                      className="m42-input"
                      value={shopPrice}
                      onChange={e => setShopPrice(e.target.value)}
                      placeholder="e.g. 500"
                    />
                  </div>
                )}
              </div>

              <div className="m42-form-group" style={{ margin: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <label className="m42-label" style={{ margin: 0 }}>Sticker Images (one URL per line)</label>
                  <label className="m42-btn m42-btn-ghost" style={{ padding: "2px 8px", fontSize: 11, cursor: "pointer" }}>
                    <Upload size={12} /> Upload Sticker
                    <input
                      type="file"
                      accept="image/*"
                      style={{ display: "none" }}
                      onChange={e => e.target.files?.[0] && handleStickerUpload(e.target.files[0])}
                    />
                  </label>
                </div>
                <textarea
                  className="m42-textarea"
                  rows={4}
                  value={stickerImagesText}
                  onChange={e => setStickerImagesText(e.target.value)}
                  placeholder="https://.../emoticon_1.webp&#10;https://.../emoticon_2.webp"
                />
              </div>
            </div>
          )}

          <div className="m42-form-group">
            <label className="m42-label">Description</label>
            <textarea
              className="m42-textarea"
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
            />
          </div>

          {/* Main Image / Logo */}
          <div className="m42-form-group">
            <label className="m42-label">{isWallet ? "Wallet Main Logo Image" : isSticker ? "Pack Logo / Thumbnail URL" : "Main Image URL"}</label>
            <div style={{ display: "flex", gap: 10 }}>
              <input
                type="text"
                className="m42-input"
                value={isWallet ? formData.logo_image : (formData.image || formData.logo_image)}
                onChange={e => setFormData({ ...formData, image: e.target.value, logo_image: e.target.value })}
                placeholder="/assets/..."
              />
              <label className="m42-btn m42-btn-ghost" style={{ cursor: "pointer", whiteSpace: "nowrap" }}>
                <Upload size={14} /> Upload
                <input
                  type="file"
                  accept="image/*"
                  style={{ display: "none" }}
                  onChange={e => e.target.files?.[0] && handleFileUpload(e.target.files[0], isWallet ? "logo_image" : "image")}
                />
              </label>
            </div>
          </div>

          {/* Wallet 3 Detailed Images */}
          {isWallet && (
            <div className="m42-form-group">
              <label className="m42-label">Wallet 3 Detailed Images</label>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
                {[0, 1, 2].map(i => (
                  <div key={i} style={{ border: "1px solid var(--line)", borderRadius: 8, padding: 8, textAlign: "center" }}>
                    <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: 6 }}>Image {i + 1}</div>
                    <div style={{ width: "100%", height: 70, background: "var(--tile-bg)", border: "1px solid var(--tile-border)", borderRadius: 6, overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      {formData.wallet_images?.[i] ? (
                        <img src={formData.wallet_images[i]} alt="" style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }} />
                      ) : (
                        <span style={{ fontSize: 10, color: "var(--text-3)" }}>Empty</span>
                      )}
                    </div>
                    <label className="m42-btn m42-btn-ghost" style={{ marginTop: 6, fontSize: 10, padding: "3px 6px", cursor: "pointer", width: "100%", justifyContent: "center" }}>
                      Upload
                      <input
                        type="file"
                        accept="image/*"
                        style={{ display: "none" }}
                        onChange={e => e.target.files?.[0] && handleFileUpload(e.target.files[0], i)}
                      />
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 24 }}>
            <button type="button" className="m42-btn m42-btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="m42-btn m42-btn-primary" disabled={uploading}>
              {uploading ? "Uploading..." : "Save Catalogue Entry"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// 7. Profile Page
function ProfilePage({ currentUser, stats, onOpenAuth }: any) {
  if (!currentUser) {
    return (
      <div className="m42-card" style={{ textAlign: "center", padding: "64px 20px" }}>
        <UserIcon size={48} color="var(--peach)" style={{ margin: "0 auto 16px" }} />
        <h2 className="m42-section-title m42-serif">User Profile</h2>
        <p className="m42-section-sub" style={{ maxWidth: 440, margin: "8px auto 24px" }}>
          Sign in to view and customize your collector profile, title, favorite character, and personal records.
        </p>
        <button type="button" className="m42-btn m42-btn-primary" onClick={onOpenAuth}>
          <LogIn size={15} /> Sign In
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="m42-section-head">
        <div>
          <h1 className="m42-section-title m42-serif">Collector Profile</h1>
          <p className="m42-section-sub">Your Mafia42 collector status and personal achievements.</p>
        </div>
      </div>

      <div className="m42-card" style={{ maxWidth: 640 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 24 }}>
          <div style={{ width: 72, height: 72, borderRadius: "50%", background: "var(--rose)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 26, fontWeight: 700, color: "var(--cream)" }}>
            {currentUser.username[0].toUpperCase()}
          </div>
          <div>
            <div style={{ fontSize: 22, fontWeight: 700, color: "var(--cream)" }}>{currentUser.username}</div>
            <div style={{ fontSize: 13, color: "var(--peach)", marginTop: 2 }}>
              {currentUser.role === "owner" ? "Owner / Administrator" : "Verified Collector"}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 4 }}>
              Member since: {new Date(currentUser.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <div className="m42-stat-card">
            <div className="m42-stat-label">Total CP</div>
            <div className="m42-stat-value">{stats ? fmtNum(stats.user_cp) : 0}</div>
          </div>
          <div className="m42-stat-card">
            <div className="m42-stat-label">Items Owned</div>
            <div className="m42-stat-value">{stats ? stats.owned_items : 0}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// 8. Collection Overview
function CollectionOverviewPage({ catalogue, stats, onNavigate }: any) {
  return (
    <div>
      <div className="m42-section-head">
        <div>
          <h1 className="m42-section-title m42-serif">Collection Categories</h1>
          <p className="m42-section-sub">Select any category to browse entries and mark your collection.</p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
        {Object.entries(CATEGORY_CONFIG).map(([key, cfg]) => {
          const items = catalogue[key] || [];
          return (
            <div
              key={key}
              className="m42-card"
              style={{ cursor: "pointer" }}
              onClick={() => onNavigate(key)}
            >
              <div style={{ fontSize: 18, fontWeight: 600, color: "var(--cream)" }}>{cfg.title}</div>
              <div style={{ fontSize: 12.5, color: "var(--text-3)", marginTop: 4 }}>{cfg.subtitle}</div>
              <div style={{ marginTop: 14, fontSize: 13, color: "var(--peach)", fontWeight: 600 }}>
                {items.length} items available
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// 9. Statistics Page
function StatisticsPage({ stats, catalogue, collection }: any) {
  return (
    <div>
      <div className="m42-section-head">
        <div>
          <h1 className="m42-section-title m42-serif">Collection Statistics</h1>
          <p className="m42-section-sub">Collection CP combines Skins + Wallets + Gems + Frames + Nameplates. Cards and CP Wallets have 0 CP.</p>
        </div>
      </div>

      <div className="m42-stats-grid">
        <div className="m42-stat-card">
          <div className="m42-stat-label">Total CP</div>
          <div className="m42-stat-value">{stats ? fmtNum(stats.total_cp) : 0} CP</div>
          <div className="m42-stat-sub">Across Skins, Wallets, Gems, Frames &amp; Nameplates</div>
        </div>
        <div className="m42-stat-card">
          <div className="m42-stat-label">CP I Have</div>
          <div className="m42-stat-value">{stats ? fmtNum(stats.user_cp) : 0} CP</div>
          <div className="m42-stat-sub">{stats ? Math.round(stats.completion_percentage) : 0}% of Total CP</div>
        </div>
        <div className="m42-stat-card">
          <div className="m42-stat-label">Completion</div>
          <div className="m42-stat-value">{stats ? Math.round(stats.completion_percentage) : 0}%</div>
          <div className="m42-stat-sub">{stats ? fmtNum(stats.user_cp) : 0} / {stats ? fmtNum(stats.total_cp) : 0} CP</div>
        </div>
      </div>

      {/* Category breakdown table */}
      {stats && (
        <div className="m42-card" style={{ marginTop: 24 }}>
          <h3 className="m42-section-title m42-serif" style={{ fontSize: 18, marginBottom: 14 }}>Category Breakdown</h3>
          <div className="m42-table-wrap">
            <table className="m42-table">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Owned Items</th>
                  <th>Total Items</th>
                  <th>Your CP</th>
                  <th>Max CP</th>
                  <th>Completion</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(stats.category_breakdown || {}).map(([cat, cStats]: any) => {
                  const pct = cStats.total > 0 ? (cStats.owned / cStats.total) * 100 : 0;
                  return (
                    <tr key={cat}>
                      <td style={{ textTransform: "capitalize", fontWeight: 600 }}>{cat === "nameplates" ? "NP" : cat === "cp_wallets" ? "CP Wallets" : cat}</td>
                      <td>{cStats.owned}</td>
                      <td>{cStats.total}</td>
                      <td>{fmtNum(cStats.user_cp)}</td>
                      <td>{fmtNum(cStats.max_cp)}</td>
                      <td>{Math.round(pct)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// 10. Goals Page
function GoalsPage({ goals, currentUser, onRefresh, onOpenAuth }: any) {
  const [newTitle, setNewTitle] = useState("");
  if (!currentUser) {
    return (
      <div className="m42-card" style={{ textAlign: "center", padding: "64px 20px" }}>
        <Target size={48} color="var(--peach)" style={{ margin: "0 auto 16px" }} />
        <h2 className="m42-section-title m42-serif">Collection Goals</h2>
        <p className="m42-section-sub" style={{ maxWidth: 440, margin: "8px auto 24px" }}>
          Sign in to create milestones and track your collection goals.
        </p>
        <button type="button" className="m42-btn m42-btn-primary" onClick={onOpenAuth}>
          <LogIn size={15} /> Sign In
        </button>
      </div>
    );
  }

  async function handleAddGoal(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    await api.createGoal({ title: newTitle.trim() });
    setNewTitle("");
    onRefresh();
  }

  return (
    <div>
      <div className="m42-section-head">
        <div>
          <h1 className="m42-section-title m42-serif">Personal Goals</h1>
          <p className="m42-section-sub">Add personal targets for skins, icons, or CP milestones.</p>
        </div>
      </div>

      <form onSubmit={handleAddGoal} style={{ display: "flex", gap: 10, marginBottom: 24, maxWidth: 480 }}>
        <input
          type="text"
          className="m42-input"
          placeholder="New goal title (e.g. Collect 50 Skins)..."
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
        />
        <button type="submit" className="m42-btn m42-btn-primary" style={{ whiteSpace: "nowrap" }}>
          <Plus size={14} /> Add Goal
        </button>
      </form>

      <div style={{ display: "grid", gap: 12, maxWidth: 640 }}>
        {goals.map((g: Goal) => (
          <div key={g.id} className="m42-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 18px" }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--cream)" }}>{g.title}</div>
              <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 2 }}>{g.completed ? "Completed" : "In Progress"}</div>
            </div>
            <button
              type="button"
              className="m42-btn m42-btn-ghost"
              style={{ color: "#ff9999" }}
              onClick={async () => { await api.deleteGoal(g.id); onRefresh(); }}
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// 11. Notes Page
function NotesPage({ notes, currentUser, onRefresh, onOpenAuth }: any) {
  const [content, setContent] = useState("");
  if (!currentUser) {
    return (
      <div className="m42-card" style={{ textAlign: "center", padding: "64px 20px" }}>
        <StickyNote size={48} color="var(--peach)" style={{ margin: "0 auto 16px" }} />
        <h2 className="m42-section-title m42-serif">Collection Notes</h2>
        <p className="m42-section-sub" style={{ maxWidth: 440, margin: "8px auto 24px" }}>
          Sign in to save personal journal notes and reminders.
        </p>
        <button type="button" className="m42-btn m42-btn-primary" onClick={onOpenAuth}>
          <LogIn size={15} /> Sign In
        </button>
      </div>
    );
  }

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!content.trim()) return;
    await api.createNote({ title: "Note", content: content.trim() });
    setContent("");
    onRefresh();
  }

  return (
    <div>
      <div className="m42-section-head">
        <div>
          <h1 className="m42-section-title m42-serif">Personal Notes</h1>
          <p className="m42-section-sub">Jot down trade ideas, skin wishlists, or event reminders.</p>
        </div>
      </div>

      <form onSubmit={handleAddNote} style={{ marginBottom: 24, maxWidth: 540 }}>
        <textarea
          className="m42-textarea"
          placeholder="Write a note..."
          value={content}
          onChange={e => setContent(e.target.value)}
        />
        <button type="submit" className="m42-btn m42-btn-primary" style={{ marginTop: 8 }}>
          <Plus size={14} /> Save Note
        </button>
      </form>

      <div style={{ display: "grid", gap: 12, maxWidth: 540 }}>
        {notes.map((n: Note) => (
          <div key={n.id} className="m42-card" style={{ padding: 16 }}>
            <div style={{ fontSize: 13, color: "var(--cream)", whiteSpace: "pre-wrap" }}>{n.content}</div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
              <span style={{ fontSize: 11, color: "var(--text-3)" }}>{new Date(n.created_at).toLocaleDateString()}</span>
              <button
                type="button"
                className="m42-btn m42-btn-ghost"
                style={{ padding: "4px 8px", color: "#ff9999" }}
                onClick={async () => { await api.deleteNote(n.id); onRefresh(); }}
              >
                <Trash2 size={12} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// 12. Achievements Page
function AchievementsPage({ stats }: any) {
  const milestones = [
    { title: "First Step", desc: "Collect your first item", threshold: 1 },
    { title: "Growing Collection", desc: "Collect 25 items", threshold: 25 },
    { title: "Centurion", desc: "Collect 100 items", threshold: 100 },
    { title: "CP Initiate", desc: "Accumulate 1,000 CP", cpThreshold: 1000 },
    { title: "CP Master", desc: "Accumulate 5,000 CP", cpThreshold: 5000 },
  ];

  return (
    <div>
      <div className="m42-section-head">
        <div>
          <h1 className="m42-section-title m42-serif">Achievements</h1>
          <p className="m42-section-sub">Milestones unlocked automatically as you grow your collection.</p>
        </div>
      </div>

      <div style={{ display: "grid", gap: 12, maxWidth: 560 }}>
        {milestones.map((m, idx) => {
          const unlocked = m.threshold ? (stats?.owned_items || 0) >= m.threshold : (stats?.user_cp || 0) >= (m.cpThreshold || 0);
          return (
            <div key={idx} className="m42-card" style={{ display: "flex", alignItems: "center", gap: 16, padding: "14px 18px" }}>
              <div style={{ width: 40, height: 40, borderRadius: 8, background: unlocked ? "var(--rose-deep)" : "var(--surf-2)", display: "flex", alignItems: "center", justifyContent: "center", color: unlocked ? "var(--peach)" : "var(--text-3)" }}>
                <Trophy size={18} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: unlocked ? "var(--cream)" : "var(--text-3)" }}>{m.title}</div>
                <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 2 }}>{m.desc}</div>
              </div>
              <span className={`m42-nav-badge ${unlocked ? "" : ""}`} style={{ color: unlocked ? "var(--peach)" : "var(--text-3)" }}>
                {unlocked ? "Unlocked" : "Locked"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// 13. Settings Page
function SettingsPage({ currentUser, theme, onToggleTheme, onSetTheme, onExport }: any) {
  return (
    <div>
      <div className="m42-section-head">
        <div>
          <h1 className="m42-section-title m42-serif">Settings</h1>
          <p className="m42-section-sub">Preferences and collection data management.</p>
        </div>
      </div>

      <div className="m42-card" style={{ maxWidth: 580 }}>
        <h3 className="m42-section-title m42-serif" style={{ fontSize: 18, marginBottom: 8 }}>Theme &amp; Appearance</h3>
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 14 }}>
          Choose your interface theme. Selected theme is saved automatically and persists on page refresh.
        </p>

        <div style={{ display: "flex", gap: 12, marginBottom: 28, flexWrap: "wrap" }}>
          <button
            type="button"
            className={`m42-btn ${theme === "dark" ? "m42-btn-primary" : "m42-btn-ghost"}`}
            onClick={() => onSetTheme("dark")}
            style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "10px 18px", borderRadius: 8 }}
          >
            <Moon size={16} /> Dark Mode (Muted Deep Teal)
          </button>
          <button
            type="button"
            className={`m42-btn ${theme === "light" ? "m42-btn-primary" : "m42-btn-ghost"}`}
            onClick={() => onSetTheme("light")}
            style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "10px 18px", borderRadius: 8 }}
          >
            <Sun size={16} /> Light Mode (Soft Mint &amp; White)
          </button>
        </div>

        <h3 className="m42-section-title m42-serif" style={{ fontSize: 18, marginBottom: 8 }}>Backup &amp; Export</h3>
        <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginBottom: 14 }}>
          Download canonical JSON format version 2 containing all shared catalogue and collection items.
        </p>
        <button
          type="button"
          className="m42-btn m42-btn-primary"
          onClick={async () => {
            const data = await onExport();
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `mafia42-journal-export-${new Date().toISOString().slice(0, 10)}.json`;
            a.click();
          }}
        >
          <Download size={15} /> Export Catalogue Backup
        </button>
      </div>
    </div>
  );
}

// 14. Admin Page (Owner Only)
function AdminPage({ catalogue, users, auditLogs, activeTab, onTabChange, onAddItem, onEditItem, onDeleteItem, onToggleUserStatus, onRefresh }: any) {
  return (
    <div>
      <div className="m42-section-head">
        <div>
          <h1 className="m42-section-title m42-serif">Owner Administration</h1>
          <p className="m42-section-sub">Exclusive catalogue management, image persistence, and user security control.</p>
        </div>
        <button type="button" className="m42-btn m42-btn-ghost" onClick={onRefresh}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Admin Tabs */}
      <div style={{ display: "flex", gap: 10, borderBottom: "1px solid var(--line)", paddingBottom: 12, marginBottom: 20 }}>
        <button
          type="button"
          className={`m42-btn ${activeTab === "catalogue" ? "m42-btn-primary" : "m42-btn-ghost"}`}
          onClick={() => onTabChange("catalogue")}
        >
          Catalogue Entries
        </button>
        <button
          type="button"
          className={`m42-btn ${activeTab === "users" ? "m42-btn-primary" : "m42-btn-ghost"}`}
          onClick={() => onTabChange("users")}
        >
          Registered Users ({users.length})
        </button>
        <button
          type="button"
          className={`m42-btn ${activeTab === "audit" ? "m42-btn-primary" : "m42-btn-ghost"}`}
          onClick={() => onTabChange("audit")}
        >
          Audit Logs
        </button>
      </div>

      {activeTab === "catalogue" && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={{ fontSize: 14, color: "var(--cream)", fontWeight: 600 }}>Manage Catalogue Items</div>
            <div style={{ display: "flex", gap: 8 }}>
              {["skins", "wallets", "icons", "cards", "frames", "nameplates"].map(cat => (
                <button
                  key={cat}
                  type="button"
                  className="m42-btn m42-btn-primary"
                  style={{ fontSize: 11, padding: "5px 10px" }}
                  onClick={() => onAddItem(cat)}
                >
                  <Plus size={12} /> Add {cat === "nameplates" ? "NP" : cat}
                </button>
              ))}
            </div>
          </div>

          <div className="m42-card">
            <div className="m42-table-wrap">
              <table className="m42-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Name</th>
                    <th>CP</th>
                    <th>Image</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(catalogue).flatMap(([cat, items]: any) =>
                    items.slice(0, 15).map((item: CatalogueItem) => (
                      <tr key={item.id}>
                        <td style={{ textTransform: "capitalize", fontWeight: 600 }}>{cat}</td>
                        <td>{item.name}</td>
                        <td>{fmtNum(item.cp)}</td>
                        <td>
                          {item.image || item.logo_image ? (
                            <img src={item.logo_image || item.image} alt="" style={{ width: 28, height: 28, borderRadius: 4, objectFit: "contain" }} />
                          ) : (
                            <span style={{ fontSize: 11, color: "var(--text-3)" }}>None</span>
                          )}
                        </td>
                        <td>
                          <div style={{ display: "flex", gap: 6 }}>
                            <button
                              type="button"
                              className="m42-btn m42-btn-ghost"
                              style={{ padding: "4px 8px" }}
                              onClick={() => onEditItem(cat, item)}
                            >
                              <Pencil size={12} />
                            </button>
                            <button
                              type="button"
                              className="m42-btn m42-btn-ghost"
                              style={{ padding: "4px 8px", color: "#ff9999" }}
                              onClick={() => onDeleteItem(item.id)}
                            >
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === "users" && (
        <div className="m42-card">
          <div className="m42-table-wrap">
            <table className="m42-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Owned Items</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u: AdminUser) => (
                  <tr key={u.id}>
                    <td style={{ fontWeight: 600, color: "var(--cream)" }}>{u.username}</td>
                    <td>{u.email}</td>
                    <td>
                      <span className="m42-nav-badge">{u.role}</span>
                    </td>
                    <td>
                      <span style={{ color: u.is_active ? "var(--peach)" : "#ff9999", fontWeight: 600 }}>
                        {u.is_active ? "Active" : "Suspended"}
                      </span>
                    </td>
                    <td>{u.owned_items_count}</td>
                    <td>
                      {u.role !== "owner" && (
                        <button
                          type="button"
                          className={`m42-btn ${u.is_active ? "m42-btn-danger" : "m42-btn-primary"}`}
                          style={{ fontSize: 11, padding: "4px 10px" }}
                          onClick={() => onToggleUserStatus(u.id, u.is_active)}
                        >
                          {u.is_active ? "Suspend User" : "Activate User"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === "audit" && (
        <div className="m42-card">
          <div className="m42-table-wrap">
            <table className="m42-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>Target Type</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log: AuditLog) => (
                  <tr key={log.id}>
                    <td style={{ whiteSpace: "nowrap", fontSize: 12 }}>{new Date(log.timestamp).toLocaleString()}</td>
                    <td style={{ fontWeight: 600, color: "var(--peach)" }}>{log.action}</td>
                    <td>{log.target_type}</td>
                    <td style={{ fontSize: 12 }}>{log.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// GEMS COLLECTION PAGE COMPONENT
// ============================================================================
interface GemsPageProps {
  searchQuery: string;
  currentUser: User | null;
  cards: CatalogueItem[];
  onOpenAuth: () => void;
  onRefreshStats: () => Promise<void>;
}

function GemsPage({
  searchQuery,
  currentUser,
  cards,
  onOpenAuth,
  onRefreshStats,
}: GemsPageProps) {
  const [gemsData, setGemsData] = useState<GemsResponse | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<"Mafia Team" | "Citizen Team" | "Cult Mode">("Mafia Team");
  const [selectedRoleId, setSelectedRoleId] = useState<string>("all");
  const [loading, setLoading] = useState<boolean>(true);
  const [linkModalGem, setLinkModalGem] = useState<GemItem | null>(null);
  const [selectedCardIdForLink, setSelectedCardIdForLink] = useState<string>("");
  const [savingLink, setSavingLink] = useState<boolean>(false);

  const [gemsError, setGemsError] = useState<string | null>(null);

  useEffect(() => {
    loadGems();
  }, [currentUser]);

  async function loadGems() {
    setLoading(true);
    setGemsError(null);
    try {
      const data = await api.getGems();
      setGemsData(data);
    } catch (err: any) {
      console.error("Failed to load gems:", err);
      setGemsError(err?.message || "Failed to load gems catalogue.");
    } finally {
      setLoading(false);
    }
  }

  // Level Selection Handler (1–16 or 0 for No Gem)
  async function handleSelectLevel(gem: GemItem, targetLevel: number) {
    if (!currentUser) {
      onOpenAuth();
      return;
    }

    // If clicking already selected level, treat as re-selection or toggle to No Gem
    const newLevel = gem.current_level === targetLevel ? 0 : targetLevel;

    // Optimistic Update
    if (gemsData) {
      const updatedTeams = { ...gemsData.teams };
      let deltaCp = 0;
      let deltaPoints = 0;

      const updateList = (list: GemItem[]) =>
        list.map(g => {
          if (g.id === gem.id) {
            const oldCp = g.current_cp;
            const oldGp = g.current_gem_points;
            const newLvlData = newLevel > 0 ? g.levels[newLevel - 1] : null;
            const newCp = newLvlData ? newLvlData.cp : 0;
            const newGp = newLvlData ? newLvlData.gem_points : 0;

            deltaCp = newCp - oldCp;
            deltaPoints = newGp - oldGp;

            return {
              ...g,
              current_level: newLevel,
              current_cp: newCp,
              current_gem_points: newGp,
              current_level_data: newLvlData,
            };
          }
          return g;
        });

      updatedTeams["Mafia Team"] = updateList(updatedTeams["Mafia Team"] || []);
      updatedTeams["Citizen Team"] = updateList(updatedTeams["Citizen Team"] || []);
      updatedTeams["Cult Mode"] = updateList(updatedTeams["Cult Mode"] || []);

      setGemsData({
        ...gemsData,
        total_gem_cp: Math.max(0, gemsData.total_gem_cp + deltaCp),
        total_gem_points: Math.max(0, gemsData.total_gem_points + deltaPoints),
        teams: updatedTeams,
        all_gems: [
          ...(updatedTeams["Mafia Team"] || []),
          ...(updatedTeams["Citizen Team"] || []),
          ...(updatedTeams["Cult Mode"] || []),
        ],
      });
    }

    try {
      await api.selectGemLevel(gem.id, newLevel);
      await onRefreshStats();
    } catch (err) {
      console.error("Failed to persist gem level:", err);
      loadGems();
    }
  }

  // Owner Card Link Handler
  async function handleSaveCardLink() {
    if (!linkModalGem) return;
    setSavingLink(true);
    try {
      await api.linkGemCard(linkModalGem.id, selectedCardIdForLink);
      setLinkModalGem(null);
      await loadGems();
    } catch (err: any) {
      alert("Error linking card: " + err.message);
    } finally {
      setSavingLink(false);
    }
  }

  // Filter gems by Team, Role filter, and Search Query
  const currentTeamGems = gemsData ? gemsData.teams[selectedTeam] || [] : [];
  const filteredGems = useMemo(() => {
    return currentTeamGems.filter(g => {
      if (selectedRoleId !== "all" && g.role_id !== selectedRoleId) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = g.name.toLowerCase().includes(q);
        const matchChar = g.character.toLowerCase().includes(q);
        const matchLevels = g.levels.some(l => l.name.toLowerCase().includes(q));
        if (!matchName && !matchChar && !matchLevels) return false;
      }
      return true;
    });
  }, [currentTeamGems, selectedRoleId, searchQuery]);

  // Unique roles for the role filter pills
  const availableRoles = useMemo(() => {
    const seen = new Set<string>();
    const roles: { role_id: string; name: string }[] = [];
    currentTeamGems.forEach(g => {
      if (!seen.has(g.role_id)) {
        seen.add(g.role_id);
        roles.push({ role_id: g.role_id, name: g.character });
      }
    });
    return roles;
  }, [currentTeamGems]);

  if (loading && !gemsData) {
    return (
      <div style={{ textAlign: "center", padding: "80px 20px" }}>
        <RefreshCw size={32} className="spin" color="var(--peach)" style={{ margin: "0 auto 16px" }} />
        <div style={{ marginTop: 16, color: "#000000", fontWeight: 700, fontSize: 15 }}>Loading Gems catalogue...</div>
      </div>
    );
  }

  if (gemsError && !gemsData) {
    return (
      <div style={{ textAlign: "center", padding: "60px 20px", background: "var(--card-bg)", border: "1.5px solid #EF4444", borderRadius: 12, maxWidth: 500, margin: "40px auto" }}>
        <AlertCircle size={36} style={{ color: "#EF4444", margin: "0 auto 12px" }} />
        <h3 style={{ fontSize: 18, color: "#000000", fontWeight: 700, margin: "0 0 6px" }}>Failed to load Gems</h3>
        <p style={{ fontSize: 13, color: "#000000", marginBottom: 16 }}>{gemsError}</p>
        <button type="button" className="m42-btn m42-btn-peach" onClick={loadGems}>
          <RefreshCw size={14} style={{ marginRight: 6 }} /> Retry Loading Gems
        </button>
      </div>
    );
  }

  return (
    <div className="m42-gems-container">
      {/* Gems Header Banner */}
      <div className="m42-gems-header">
        <div className="m42-gems-header-left">
          <div className="m42-gems-badge-icon">
            <Coins size={28} />
          </div>
          <div>
            <h1 className="m42-serif" style={{ fontSize: 28, color: "var(--cream)", marginBottom: 4 }}>
              Gems Collection
            </h1>
            <p style={{ fontSize: 13, color: "var(--text-3)", margin: 0 }}>
              Refine and track gems for Mafia and Citizen roles across all 16 levels.
            </p>
          </div>
        </div>

        <div className="m42-gems-stats-panel">
          <div className="m42-gems-stat-chip">
            <span className="m42-gems-stat-label">Gem CP Total</span>
            <span className="m42-gems-stat-value highlight-cyan">
              {fmtNum(gemsData?.total_gem_cp || 0)} CP
            </span>
          </div>
          <div className="m42-gems-stat-chip">
            <span className="m42-gems-stat-label">Gem Points</span>
            <span className="m42-gems-stat-value" style={{ color: "#ffd700" }}>
              ⭐ {gemsData?.total_gem_points || 0}
            </span>
          </div>
        </div>
      </div>

      {/* Team Navigation Tabs */}
      <div className="m42-gems-team-nav">
        <div className="m42-gems-team-nav-label">Select Team:</div>
        <button
          type="button"
          className={`m42-gems-team-btn mafia-btn ${selectedTeam === "Mafia Team" ? "active" : ""}`}
          onClick={() => {
            setSelectedTeam("Mafia Team");
            setSelectedRoleId("all");
          }}
        >
          <Flame size={20} className="m42-gems-team-btn-icon" />
          <span className="m42-gems-team-title">Mafia Team</span>
          <span className="m42-gems-team-count">
            {gemsData?.teams["Mafia Team"]?.length || 10} Roles
          </span>
        </button>

        <button
          type="button"
          className={`m42-gems-team-btn citizen-btn ${selectedTeam === "Citizen Team" ? "active" : ""}`}
          onClick={() => {
            setSelectedTeam("Citizen Team");
            setSelectedRoleId("all");
          }}
        >
          <Shield size={20} className="m42-gems-team-btn-icon" />
          <span className="m42-gems-team-title">Citizen Team</span>
          <span className="m42-gems-team-count">
            {gemsData?.teams["Citizen Team"]?.length || 27} Roles
          </span>
        </button>

        <button
          type="button"
          className={`m42-gems-team-btn cult-btn ${selectedTeam === "Cult Mode" ? "active" : ""}`}
          onClick={() => {
            setSelectedTeam("Cult Mode");
            setSelectedRoleId("all");
          }}
        >
          <Sparkles size={20} className="m42-gems-team-btn-icon" />
          <span className="m42-gems-team-title">Cult Mode</span>
          <span className="m42-gems-team-count">
            {gemsData?.teams["Cult Mode"]?.length || 1} Role
          </span>
        </button>
      </div>

      {/* Role Filter Pills */}
      <div className="m42-gems-role-bar">
        <button
          type="button"
          className={`m42-gems-role-pill ${selectedRoleId === "all" ? "active" : ""}`}
          onClick={() => setSelectedRoleId("all")}
        >
          All Roles ({currentTeamGems.length})
        </button>
        {availableRoles.map(r => (
          <button
            key={r.role_id}
            type="button"
            className={`m42-gems-role-pill ${selectedRoleId === r.role_id ? "active" : ""}`}
            onClick={() => setSelectedRoleId(r.role_id)}
          >
            {r.name}
          </button>
        ))}
      </div>

      {/* Gems Items Grid */}
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {filteredGems.length === 0 ? (
          <div className="m42-card" style={{ textAlign: "center", padding: "40px" }}>
            <p style={{ color: "var(--text-3)", fontSize: 14 }}>No gems found matching your search filter.</p>
          </div>
        ) : (
          filteredGems.map(gem => (
            <GemCard
              key={gem.id}
              gem={gem}
              currentUser={currentUser}
              onSelectLevel={lvl => handleSelectLevel(gem, lvl)}
              onOpenLinkModal={() => {
                setLinkModalGem(gem);
                setSelectedCardIdForLink(gem.card_id || "");
              }}
            />
          ))
        )}
      </div>

      {/* Owner-Only Card Linking Modal */}
      {linkModalGem && (
        <div className="m42-modal-backdrop" onClick={() => setLinkModalGem(null)}>
          <div className="m42-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 480 }}>
            <div className="m42-modal-header">
              <h2 className="m42-serif" style={{ fontSize: 20, color: "var(--cream)" }}>
                Link Card to {linkModalGem.name}
              </h2>
              <button
                type="button"
                className="m42-btn m42-btn-ghost"
                onClick={() => setLinkModalGem(null)}
                style={{ padding: 4 }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: "16px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
              <p style={{ fontSize: 13, color: "var(--text-3)" }}>
                Associate a character card from your catalogue with this gem item. The linked card will be shown in the gem's card area.
              </p>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-2)", display: "block", marginBottom: 6 }}>
                  Select Linked Card:
                </label>
                <select
                  className="m42-input"
                  value={selectedCardIdForLink}
                  onChange={e => setSelectedCardIdForLink(e.target.value)}
                  style={{ width: "100%", padding: "10px 12px" }}
                >
                  <option value="">-- No Card Linked --</option>
                  {cards.map(card => (
                    <option key={card.id} value={card.id}>
                      {card.name} ({card.character}) [ID: {card.id}]
                    </option>
                  ))}
                </select>
              </div>

              {selectedCardIdForLink && (
                <div style={{ display: "flex", alignItems: "center", gap: 12, background: "rgba(4, 20, 32, 0.7)", padding: 12, borderRadius: 8, border: "1px solid var(--line)" }}>
                  {cards.find(c => c.id === selectedCardIdForLink)?.image && (
                    <img
                      src={cards.find(c => c.id === selectedCardIdForLink)?.image}
                      alt="Card Preview"
                      style={{ width: 44, height: 60, borderRadius: 4, objectFit: "cover", border: "1px solid #2F5B61" }}
                    />
                  )}
                  <div>
                    <div style={{ fontWeight: 700, color: "#000000", fontSize: 13 }}>
                      {cards.find(c => c.id === selectedCardIdForLink)?.name}
                    </div>
                    <div style={{ fontSize: 11, color: "#000000", fontWeight: 600 }}>
                      Card ID: {selectedCardIdForLink}
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="m42-modal-footer">
              <button
                type="button"
                className="m42-btn m42-btn-ghost"
                onClick={() => setLinkModalGem(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="m42-btn m42-btn-primary"
                onClick={handleSaveCardLink}
                disabled={savingLink}
              >
                {savingLink ? "Saving..." : "Save Link"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// INDIVIDUAL GEM CARD COMPONENT
// Follows Word Document Layout & Mafia42 Screenshots:
// - Role & Gem header with linked card
// - Current selection preview box (image, name, description, CP, Gem Points)
// - 16 level selector grid with 'No Gem' reset button
// - Owner-only edit/link controls
// ============================================================================
interface GemCardProps {
  gem: GemItem;
  currentUser: User | null;
  onSelectLevel: (lvl: number) => void;
  onOpenLinkModal: () => void;
}

function GemCard({ gem, currentUser, onSelectLevel, onOpenLinkModal }: GemCardProps) {
  const currentLvl = gem.current_level;
  const currentLvlData = gem.current_level_data;
  const isOwner = currentUser?.role === "owner";

  return (
    <div className={`m42-gem-card ${currentLvl > 0 ? "has-selection" : ""}`}>
      {/* Card Header: Role Info, Team Badge, Linked Card, Owner Controls */}
      <div className="m42-gem-card-header">
        <div className="m42-gem-header-info">
          {gem.badge_image && (
            <img
              src={gem.badge_image}
              alt={gem.character}
              className="m42-gem-role-badge"
              onError={e => { (e.target as HTMLElement).style.display = "none"; }}
            />
          )}
          <div>
            <div className="m42-gem-title">
              <span>{gem.name}</span>
              <span className="m42-gem-team-tag">{gem.team}</span>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 2 }}>
              Role: <strong style={{ color: "var(--cream)" }}>{gem.character}</strong>
            </div>
          </div>
        </div>

        <div className="m42-gem-header-right">
          {/* Linked Card Area */}
          {gem.linked_card ? (
            <div className="m42-gem-card-link-box" title={`Linked to card: ${gem.linked_card.name}`}>
              {gem.linked_card.image && (
                <img src={gem.linked_card.image} alt={gem.linked_card.name} className="m42-gem-card-thumb" />
              )}
              <span className="m42-gem-card-name">{gem.linked_card.name}</span>
            </div>
          ) : (
            <div className="m42-gem-card-link-box" style={{ opacity: 0.6 }}>
              <Layers size={14} color="var(--text-3)" />
              <span style={{ fontSize: 11, color: "var(--text-3)" }}>No Card Linked</span>
            </div>
          )}

          {/* Owner-Only Link / Edit Control */}
          {isOwner && (
            <button
              type="button"
              className="m42-btn m42-btn-ghost"
              style={{ fontSize: 11, padding: "5px 10px" }}
              title="Owner: Link or change associated Card"
              onClick={onOpenLinkModal}
            >
              <Pencil size={12} /> Link Card
            </button>
          )}
        </div>
      </div>

      {/* Selected Gem Display Box (as shown in Word document & NamuWiki screenshots) */}
      <div className="m42-gem-display-preview">
        <div className="m42-gem-current-img-wrap">
          {currentLvl > 0 && currentLvlData?.image ? (
            <img
              src={currentLvlData.image}
              alt={currentLvlData.name}
              className="m42-gem-current-img"
            />
          ) : (
            <div className="m42-gem-empty-icon">
              <div>No Gem</div>
              <div style={{ fontSize: 9 }}>Selected</div>
            </div>
          )}
        </div>

        <div className="m42-gem-preview-details">
          {currentLvl > 0 && currentLvlData ? (
            <>
              <div className="m42-gem-preview-title">
                Level {currentLvlData.level}: {currentLvlData.name}
              </div>
              <div className="m42-gem-preview-desc">
                {currentLvlData.description || "Increases job assignment probability and rewards."}
              </div>
              <div className="m42-gem-preview-badges">
                <span className="m42-gem-cp-badge">
                  +{fmtNum(currentLvlData.cp)} CP
                </span>
                {currentLvlData.gem_points > 0 && (
                  <span className="m42-gem-point-badge">
                    ⭐ +{currentLvlData.gem_points} Gem Point{currentLvlData.gem_points > 1 ? "s" : ""}
                  </span>
                )}
              </div>
            </>
          ) : (
            <>
              <div className="m42-gem-preview-title" style={{ color: "var(--text-3)" }}>
                No Gem Equipped
              </div>
              <div className="m42-gem-preview-desc" style={{ color: "var(--text-3)" }}>
                Select a level below (1–16) to register this gem in your collection and earn Collection Points.
              </div>
              <div className="m42-gem-preview-badges">
                <span style={{ fontSize: 11, color: "var(--text-3)" }}>0 CP contributed</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* 16 Levels Grid Selector */}
      <div className="m42-gem-level-selector">
        <div className="m42-gem-level-selector-header">
          <span className="m42-gem-selector-label">Select Level (1 – 16):</span>
          <button
            type="button"
            className={`m42-gem-no-gem-btn ${currentLvl === 0 ? "active" : ""}`}
            onClick={() => onSelectLevel(0)}
            title="Reset selection (0 CP)"
          >
            <X size={12} /> No Gem
          </button>
        </div>

        <div className="m42-gem-levels-grid">
          {gem.levels.map(lvl => {
            const isSelected = currentLvl === lvl.level;
            return (
              <div
                key={lvl.level}
                className={`m42-gem-level-box ${isSelected ? "selected" : ""}`}
                onClick={() => onSelectLevel(lvl.level)}
                title={`Level ${lvl.level}: ${lvl.name} (+${lvl.cp} CP)`}
              >
                {lvl.gem_points > 0 && (
                  <span className="m42-gem-point-pip" title={`+${lvl.gem_points} Gem Point`}>
                    +{lvl.gem_points}
                  </span>
                )}
                <span className="m42-gem-level-num">Lv {lvl.level}</span>
                <div className="m42-gem-level-img-wrap">
                  {lvl.image ? (
                    <img
                      src={lvl.image}
                      alt={lvl.name}
                      className="m42-gem-level-img"
                      loading="lazy"
                    />
                  ) : (
                    <span style={{ fontSize: 10, color: "var(--text-3)" }}>Lv{lvl.level}</span>
                  )}
                </div>
                <span className="m42-gem-level-cp">{lvl.cp} CP</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}


