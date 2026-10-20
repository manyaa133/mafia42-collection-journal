import React, { useState, useEffect } from "react";
import { 
  Check, X, ChevronRight, Sparkles, ExternalLink, AlertCircle, 
  CheckCircle2, XCircle, RotateCcw, Filter, Eye, Layers, Shirt, Tag, Pin, Coins, Shield, RefreshCw, Search 
} from "lucide-react";
import { api, ImageProposal } from "../api";

interface ImageReviewPageProps {
  currentUser: any;
  onOpenAuth: () => void;
}

export function ImageReviewPage({ currentUser, onOpenAuth }: ImageReviewPageProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>("icons");
  const [statusFilter, setStatusFilter] = useState<string>("pending");
  const [proposals, setProposals] = useState<ImageProposal[]>([]);
  const [summary, setSummary] = useState<Record<string, { total: number; pending: number; approved: number; rejected: number }>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [failedImages, setFailedImages] = useState<Record<string, boolean>>({});
  const [selectedCandidateMap, setSelectedCandidateMap] = useState<Record<string, number>>({});
  const [batchStatus, setBatchStatus] = useState<{
    current_batch_number: number;
    current_batch: any[];
    pending_frames_count?: number;
    total_approved_frames?: number;
    pending_skins_count?: number;
    total_approved_skins?: number;
    presented_count: number;
    mode?: string;
    available_batches?: number[];
  } | null>(null);
  const [advancingBatch, setAdvancingBatch] = useState<boolean>(false);
  const [selectedJumpItem, setSelectedJumpItem] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const categories = [
    { id: "skin_main", label: "Skin Main Images", icon: Shirt },
    { id: "skin_logo", label: "Skin Logos", icon: Shield },
    { id: "gems", label: "Gems (608 Levels)", icon: Coins },
    { id: "frames", label: "Frames", icon: Pin },
    { id: "nameplates", label: "Nameplates", icon: Tag },
    { id: "icons", label: "Icons", icon: Sparkles },
    { id: "cards", label: "Cards", icon: Layers },
    { id: "card_logos", label: "Card Logos", icon: Shield },
  ];

  useEffect(() => {
    // Initial summary load to set active category
    api.getImageProposalsSummary().then(sumRes => {
      const sum = sumRes.summary || {};
      setSummary(sum);
      // Pick first category with pending items if possible
      const catWithPending = categories.find(c => (sum[c.id]?.pending || 0) > 0);
      if (catWithPending) {
        setSelectedCategory(catWithPending.id);
      }
    }).catch(console.error);
  }, []);

  useEffect(() => {
    loadData();
  }, [selectedCategory, statusFilter]);

  async function loadData() {
    setLoading(true);
    setLoadError(null);
    try {
      const [propsRes, sumRes] = await Promise.all([
        api.getImageProposals(selectedCategory, statusFilter),
        api.getImageProposalsSummary(),
      ]);
      setProposals(propsRes.proposals || []);
      setSummary(sumRes.summary || {});

      if (selectedCategory === "frames") {
        api.getFrameBatchStatus().then(setBatchStatus).catch(console.error);
      } else if (selectedCategory === "skin_main" || selectedCategory === "skin_logo") {
        api.getSkinBatchStatus(selectedCategory).then(setBatchStatus).catch(console.error);
      } else {
        setBatchStatus(null);
      }
    } catch (err: any) {
      console.error("Failed to load proposals:", err);
      setLoadError(err?.message || "Failed to load proposals. Please check connection.");
    } finally {
      setLoading(false);
    }
  }

  async function handleNextBatch() {
    if (!currentUser || currentUser.role !== "owner") {
      alert("Only an authenticated Owner can advance candidate batches.");
      onOpenAuth();
      return;
    }
    const isSkin = selectedCategory === "skin_main" || selectedCategory === "skin_logo";
    const batchSize = isSkin ? 20 : 5;
    const catLabel = selectedCategory === "skin_main" ? "Skin Main Images" : selectedCategory === "skin_logo" ? "Skin Logos" : "Frames";

    if (!confirm(`Advance to the NEXT ${batchSize} shared candidates for remaining pending ${catLabel}? The current ${batchSize} candidates will be archived as presented.`)) {
      return;
    }
    setAdvancingBatch(true);
    try {
      if (isSkin) {
        const res = await api.nextSkinBatch(selectedCategory);
        alert(`Batch advanced! Now on Batch #${res.current_batch_number} with ${res.current_batch.length} fresh unused candidates for ${catLabel}.`);
      } else {
        const res = await api.nextFrameBatch();
        alert(`Batch advanced! Now on Batch #${res.current_batch_number} with ${res.current_batch.length} fresh unused candidates.`);
      }
      await loadData();
    } catch (err: any) {
      alert("Failed to advance batch: " + (err?.message || "Unknown error"));
    } finally {
      setAdvancingBatch(false);
    }
  }

  async function handleSwitchBatch(targetBatch: number) {
    if (!currentUser || currentUser.role !== "owner") {
      alert("Only an authenticated Owner can switch candidate batches.");
      onOpenAuth();
      return;
    }
    const isSkin = selectedCategory === "skin_main" || selectedCategory === "skin_logo";
    if (!isSkin) return;

    setAdvancingBatch(true);
    try {
      await api.switchSkinBatch(selectedCategory, targetBatch);
      await loadData();
    } catch (err: any) {
      alert("Failed to switch batch: " + (err?.message || "Unknown error"));
    } finally {
      setAdvancingBatch(false);
    }
  }

  async function handleReview(
    proposal: ImageProposal, 
    action: "approve" | "reject" | "skip",
    candidateUrl?: string,
    targetField?: "artwork" | "logo" | "both"
  ) {
    if (!currentUser || currentUser.role !== "owner") {
      alert("Only an authenticated Owner can review and approve image proposals.");
      onOpenAuth();
      return;
    }

    if (action === "approve") {
      const activeUrl = candidateUrl || proposal.proposed_url;
      const proposedFail = failedImages[`cand_${activeUrl}`] || failedImages[`proposed_${proposal.id}`];
      if (proposedFail) {
        alert("Approval disabled: The proposed image failed to load.");
        return;
      }
    }

    setProcessingId(proposal.id);
    try {
      await api.reviewImageProposal({
        item_id: proposal.id,
        action,
        category: proposal.category,
        proposed_url: targetField === "logo" ? undefined : (candidateUrl || proposal.proposed_url),
        proposed_logo_url: targetField === "logo" ? (candidateUrl || proposal.proposed_logo_url) : proposal.proposed_logo_url,
        target_field: targetField,
      });

      // Reload summary and proposals
      const [propsRes, sumRes] = await Promise.all([
        api.getImageProposals(selectedCategory, statusFilter),
        api.getImageProposalsSummary(),
      ]);
      setProposals(propsRes.proposals || []);
      setSummary(sumRes.summary || {});
    } catch (err: any) {
      alert("Error submitting review: " + err.message);
    } finally {
      setProcessingId(null);
    }
  }

  const handleImageError = (key: string) => {
    setFailedImages(prev => ({ ...prev, [key]: true }));
  };

  const handleImageLoad = (key: string) => {
    setFailedImages(prev => ({ ...prev, [key]: false }));
  };

  const currentCatSummary = summary[selectedCategory] || { total: 0, pending: 0, approved: 0, rejected: 0 };
  
  const filteredProposals = proposals.filter(p => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase().trim();
    const nameMatch = p.name?.toLowerCase().includes(q);
    const idMatch = p.id?.toLowerCase().includes(q);
    const charMatch = p.character?.toLowerCase().includes(q);
    const skinIdMatch = p.skin_id?.toLowerCase().includes(q);
    return Boolean(nameMatch || idMatch || charMatch || skinIdMatch);
  });
  const isBanner = selectedCategory === "nameplates";
  const isSquareIcon = selectedCategory === "icons" || selectedCategory === "card_logos" || selectedCategory === "skin_logo" || selectedCategory === "gems";
  const previewBoxHeight = isBanner ? 100 : isSquareIcon ? 150 : 220;
  const imgMaxHeight = isBanner ? 80 : isSquareIcon ? 110 : 200;

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: 60 }}>
      {/* Header */}
      <div style={{ 
        display: "flex", 
        justifyContent: "space-between", 
        alignItems: "flex-start", 
        marginBottom: 20, 
        flexWrap: "wrap", 
        gap: 12,
        background: "var(--surf-white)",
        border: "1px solid var(--border-subtle)",
        borderRadius: 14,
        padding: "20px 24px",
        boxShadow: "0 1px 3px rgba(16, 43, 45, 0.05)"
      }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--deep-teal)", display: "flex", alignItems: "center", gap: 10, margin: "0 0 6px" }}>
            <Sparkles size={24} style={{ color: "var(--dark-teal)" }} />
            Manual Image Replacement Approval
          </h1>
          <p style={{ margin: 0, fontSize: 13, color: "var(--text-muted)" }}>
            Side-by-side inspection for replacing catalogue assets with originals from <code style={{ color: "var(--dark-teal)", background: "var(--tile-bg)", padding: "2px 6px", borderRadius: 4, fontWeight: 600 }}>m42garine-source/Assets</code>.
            No image reference is modified without explicit approval.
          </p>
        </div>

        {!currentUser && (
          <button 
            type="button" 
            className="m42-btn m42-btn-primary" 
            onClick={onOpenAuth}
            style={{ padding: "8px 16px", fontSize: 13, fontWeight: 700 }}
          >
            Log in as Owner to Review
          </button>
        )}
      </div>

      {/* Category Navigation Pills */}
      <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 12, marginBottom: 16 }}>
        {categories.map(cat => {
          const Icon = cat.icon;
          const stat = summary[cat.id] || { total: 0, pending: 0, approved: 0, rejected: 0 };
          const isActive = selectedCategory === cat.id;
          return (
            <button
              key={cat.id}
              type="button"
              onClick={() => setSelectedCategory(cat.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 16px",
                borderRadius: 20,
                border: isActive ? "1.5px solid var(--deep-teal)" : "1px solid var(--border-subtle)",
                background: isActive ? "var(--dark-teal)" : "var(--surf-white)",
                color: isActive ? "#FFFFFF" : "var(--text-dark)",
                fontWeight: 700,
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "all 0.15s ease",
              }}
            >
              <Icon size={16} />
              <span>{cat.label}</span>
              <span style={{
                fontSize: 11,
                padding: "2px 7px",
                borderRadius: 10,
                background: isActive ? "rgba(255, 255, 255, 0.2)" : "var(--tile-bg)",
                color: isActive ? "#FFFFFF" : "var(--dark-teal)",
                fontWeight: 700,
              }}>
                {stat.pending > 0 ? `${stat.pending} pending` : `${stat.total}`}
              </span>
            </button>
          );
        })}
      </div>

      {/* Filter Bar & Category Stats */}
      <div style={{ 
        display: "flex", 
        justifyContent: "space-between", 
        alignItems: "center", 
        background: "var(--surf-white)", 
        border: "1px solid var(--border-subtle)", 
        borderRadius: 10, 
        padding: "12px 18px", 
        marginBottom: 20,
        flexWrap: "wrap",
        gap: 12
      }}>
        {/* Status Filters and Search */}
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", flex: 1 }}>
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ fontSize: 12, color: "var(--text-muted)", marginRight: 4, fontWeight: 700 }}>Filter:</span>
            {[
              { id: "unresolved", label: "Unresolved", count: (currentCatSummary.pending || 0) + (currentCatSummary.rejected || 0) },
              { id: "pending", label: "Pending", count: currentCatSummary.pending },
              { id: "rejected", label: "Rejected", count: currentCatSummary.rejected },
              { id: "approved", label: "Approved", count: currentCatSummary.approved },
              { id: "all", label: "All Items", count: currentCatSummary.total },
            ].map(f => (
              <button
                key={f.id}
                type="button"
                onClick={() => setStatusFilter(f.id)}
                className={`m42-btn ${statusFilter === f.id ? "m42-btn-primary" : "m42-btn-ghost"}`}
                style={{ padding: "4px 10px", fontSize: 12, borderRadius: 6, fontWeight: 700 }}
              >
                {f.label} ({f.count})
              </button>
            ))}
          </div>

          {/* Real-time Search Box */}
          <div style={{ 
            display: "flex", 
            alignItems: "center", 
            gap: 6, 
            background: "var(--tile-bg)", 
            border: "1px solid var(--border-subtle)", 
            borderRadius: 6, 
            padding: "4px 10px",
            minWidth: 220,
            maxWidth: 320,
            flex: 1
          }}>
            <Search size={14} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
            <input
              type="text"
              placeholder="Search skin name, character, ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                border: "none",
                background: "transparent",
                outline: "none",
                fontSize: 12,
                color: "var(--text-dark)",
                width: "100%",
              }}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                style={{ border: "none", background: "none", cursor: "pointer", padding: 0, color: "var(--text-muted)" }}
                title="Clear search"
              >
                <X size={13} />
              </button>
            )}
          </div>
        </div>

        {/* Info Note */}
        <div style={{ fontSize: 11, color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 6, fontWeight: 600 }}>
          <AlertCircle size={14} style={{ color: "var(--dark-teal)" }} />
          <span>Local wallet and CP wallet assets are strictly excluded.</span>
        </div>
      </div>

      {/* Rejection Notification Banner */}
      {statusFilter === "pending" && (currentCatSummary.rejected || 0) > 0 && (
        <div style={{
          background: "#FEF2F2",
          border: "1px solid #FCA5A5",
          borderRadius: 8,
          padding: "10px 16px",
          marginBottom: 16,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          fontSize: 12.5,
          color: "#991B1B",
          fontWeight: 600
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <AlertCircle size={16} style={{ color: "#DC2626", flexShrink: 0 }} />
            <span>
              Notice: There is <strong>{currentCatSummary.rejected} rejected item</strong> awaiting re-verification in this category.
            </span>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              type="button"
              className="m42-btn m42-btn-secondary"
              onClick={() => setStatusFilter("rejected")}
              style={{ padding: "4px 10px", fontSize: 11.5, fontWeight: 700, borderColor: "#FCA5A5", color: "#991B1B" }}
            >
              View Rejected ({currentCatSummary.rejected})
            </button>
            <button
              type="button"
              className="m42-btn m42-btn-peach"
              onClick={() => setStatusFilter("unresolved")}
              style={{ padding: "4px 10px", fontSize: 11.5, fontWeight: 700 }}
            >
              View All Unresolved ({(currentCatSummary.pending || 0) + (currentCatSummary.rejected || 0)})
            </button>
          </div>
        </div>
      )}

      {/* Proposals List */}
      {loading ? (
        <div style={{ padding: 60, textAlign: "center" }}>
          <RefreshCw size={32} className="spin" color="var(--peach)" style={{ margin: "0 auto 12px" }} />
          <div style={{ fontSize: 15, color: "var(--text-dark)", fontWeight: 700 }}>Loading proposals...</div>
        </div>
      ) : loadError ? (
        <div style={{ 
          padding: 50, 
          textAlign: "center", 
          background: "var(--card-bg)", 
          border: "1.5px solid #EF4444", 
          borderRadius: 12 
        }}>
          <AlertCircle size={36} style={{ color: "#EF4444", margin: "0 auto 12px" }} />
          <h3 style={{ fontSize: 18, color: "var(--text-dark)", fontWeight: 700, margin: "0 0 6px" }}>Error Loading Proposals</h3>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16 }}>{loadError}</p>
          <button type="button" className="m42-btn m42-btn-peach" onClick={loadData}>
            <RefreshCw size={14} style={{ marginRight: 6 }} /> Retry Loading
          </button>
        </div>
      ) : proposals.length === 0 ? (
        <div style={{ 
          padding: 50, 
          textAlign: "center", 
          background: "var(--card-bg)", 
          border: "1.5px solid var(--card-border)", 
          borderRadius: 12 
        }}>
          <CheckCircle2 size={40} style={{ color: "#22c55e", margin: "0 auto 12px" }} />
          <h3 style={{ fontSize: 18, color: "var(--text-dark)", fontWeight: 700, margin: "0 0 6px" }}>No items matching filter</h3>
          <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 16px" }}>
            {statusFilter === "pending" 
              ? `All proposals in ${categories.find(c => c.id === selectedCategory)?.label || selectedCategory} have been reviewed!` 
              : `No items found under status "${statusFilter}".`}
          </p>
          <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
            {statusFilter !== "all" && (
              <button
                type="button"
                className="m42-btn m42-btn-secondary"
                onClick={() => setStatusFilter("all")}
                style={{ padding: "6px 14px" }}
              >
                View All {currentCatSummary.total} Items
              </button>
            )}
            {categories.filter(c => (summary[c.id]?.pending || 0) > 0 && c.id !== selectedCategory).map(cat => (
              <button
                key={cat.id}
                type="button"
                className="m42-btn m42-btn-peach"
                onClick={() => { setSelectedCategory(cat.id); setStatusFilter("pending"); }}
                style={{ padding: "6px 14px" }}
              >
                Switch to {cat.label} ({summary[cat.id]?.pending} pending)
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Shared Batch Header Banner for Frames, Skin Main Images, and Skin Logos */}
          {(selectedCategory === "frames" || selectedCategory === "skin_main" || selectedCategory === "skin_logo") && (statusFilter === "pending" || statusFilter === "unresolved" || statusFilter === "rejected") && (
            <div style={{ 
              background: "var(--surf-white)", 
              border: "2px solid var(--dark-teal)", 
              borderRadius: 12, 
              padding: 16,
              boxShadow: "0 2px 8px rgba(23, 63, 67, 0.08)",
              display: "flex",
              flexDirection: "column",
              gap: 12
            }}>
              {/* Header row */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 800, color: "#FFFFFF", background: "var(--dark-teal)", padding: "3px 10px", borderRadius: 6 }}>
                      SHARED BATCH #{batchStatus?.current_batch_number || 1}
                    </span>
                    <span style={{ fontSize: 14, fontWeight: 800, color: "var(--deep-teal)" }}>
                      {selectedCategory === "frames" ? 5 : 20} Shared Candidate Images Across All {proposals.length} Pending {selectedCategory === "frames" ? "Frames" : selectedCategory === "skin_main" ? "Skins (Main Artwork)" : "Skins (Logos)"}
                    </span>
                  </div>
                  <p style={{ margin: "4px 0 0", fontSize: 11.5, color: "var(--text-muted)" }}>
                    The exact same {selectedCategory === "frames" ? "5" : "20"} candidate images below are shared across every pending {selectedCategory === "frames" ? "frame" : "skin"} in this batch. Select any pending entry to inspect its original image against these candidates, and approve matches manually.
                  </p>
                </div>

                <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  {batchStatus?.available_batches && batchStatus.available_batches.length > 1 && (
                    <div style={{ display: "flex", alignItems: "center", gap: 6, background: "var(--tile-bg)", padding: "3px 8px", borderRadius: 6, border: "1px solid var(--border-subtle)" }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: "var(--dark-teal)" }}>Switch Batch:</span>
                      <select
                        value={batchStatus.current_batch_number}
                        onChange={(e) => handleSwitchBatch(Number(e.target.value))}
                        disabled={advancingBatch}
                        style={{
                          padding: "3px 8px",
                          fontSize: 11.5,
                          fontWeight: 700,
                          borderRadius: 4,
                          border: "1px solid var(--border-subtle)",
                          background: "var(--surf-white)",
                          color: "var(--deep-teal)",
                          cursor: "pointer"
                        }}
                      >
                        {batchStatus.available_batches.map(bNum => (
                          <option key={bNum} value={bNum}>
                            Batch #{bNum} {bNum === batchStatus.current_batch_number ? "(Active)" : ""}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {batchStatus && (batchStatus.current_batch_number || 1) > 1 && (
                    <button
                      type="button"
                      className="m42-btn m42-btn-ghost"
                      onClick={() => handleSwitchBatch((batchStatus.current_batch_number || 2) - 1)}
                      disabled={advancingBatch}
                      style={{ padding: "5px 12px", fontSize: 11.5, fontWeight: 700 }}
                      title="Go back to previous batch"
                    >
                      ← Prev Batch (#{(batchStatus.current_batch_number || 2) - 1})
                    </button>
                  )}

                  <button
                    type="button"
                    className="m42-btn m42-btn-secondary"
                    onClick={handleNextBatch}
                    disabled={advancingBatch}
                    style={{ padding: "6px 14px", fontSize: 12, fontWeight: 700 }}
                  >
                    <RefreshCw size={13} style={{ marginRight: 6 }} className={advancingBatch ? "spin" : ""} />
                    Load Next {selectedCategory === "frames" ? 5 : 20} Batch
                  </button>
                </div>
              </div>

              {/* Shared Candidates Visual Overview Strip */}
              {proposals[0]?.candidates && proposals[0].candidates.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-dark)", marginBottom: 6 }}>
                    Current Batch #{batchStatus?.current_batch_number || 1} Candidates ({proposals[0].candidates.length} Distinct Unused Assets):
                  </div>
                  <div style={{ 
                    display: "grid", 
                    gridTemplateColumns: selectedCategory === "frames" ? "repeat(5, 1fr)" : "repeat(auto-fill, minmax(130px, 1fr))", 
                    gap: 8 
                  }}>
                    {proposals[0].candidates.map((c, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: "var(--tile-bg)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: 6,
                          padding: 6,
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                          gap: 4
                        }}
                      >
                        <div style={{ fontSize: 10, fontWeight: 800, color: "var(--dark-teal)" }}>
                          {c.label}
                        </div>
                        <div style={{ 
                          width: "100%", 
                          height: selectedCategory === "skin_main" ? 80 : 60, 
                          display: "flex", 
                          alignItems: "center", 
                          justifyContent: "center", 
                          background: "var(--surf-white)", 
                          borderRadius: 4, 
                          overflow: "hidden" 
                        }}>
                          <img src={c.url} alt={c.label} style={{ maxWidth: "100%", maxHeight: selectedCategory === "skin_main" ? 76 : 54, objectFit: "contain" }} />
                        </div>
                        <div style={{ fontSize: 9, fontFamily: "monospace", color: "var(--deep-teal)", fontWeight: 700 }}>
                          {c.dimensions || (selectedCategory === "skin_main" ? "1000 × 1200" : "400 × 400")}
                        </div>
                        <div style={{ fontSize: 9, color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", width: "100%", textAlign: "center" }} title={c.filename || c.repo_path}>
                          <code>{c.filename || c.repo_path.split('/').pop()}</code>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Quick Jump Selector for Entries */}
              <div style={{ display: "flex", alignItems: "center", gap: 10, paddingTop: 4, borderTop: "1px solid var(--border-subtle)" }}>
                <span style={{ fontSize: 11.5, fontWeight: 700, color: "var(--text-dark)", whiteSpace: "nowrap" }}>
                  Jump to {selectedCategory === "frames" ? "Frame" : "Skin"} ({filteredProposals.length} shown):
                </span>
                <select
                  value={selectedJumpItem}
                  onChange={(e) => {
                    const fid = e.target.value;
                    setSelectedJumpItem(fid);
                    if (fid) {
                      const el = document.getElementById('item_card_' + fid) || document.getElementById('frame_card_' + fid);
                      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                  }}
                  style={{
                    flex: 1,
                    padding: "5px 10px",
                    fontSize: 12,
                    fontWeight: 600,
                    borderRadius: 6,
                    border: "1px solid var(--border-subtle)",
                    background: "var(--surf-white)",
                    color: "var(--text-dark)"
                  }}
                >
                  <option value="">-- Choose an item ({filteredProposals.length} available) --</option>
                  {filteredProposals.map((p, pIdx) => (
                    <option key={p.id} value={p.id}>
                      {pIdx + 1}. [{p.status ? p.status.toUpperCase() : "PENDING"}] {p.name} (ID: {p.id})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {filteredProposals.length === 0 && searchQuery ? (
            <div style={{
              padding: 40,
              textAlign: "center",
              background: "var(--surf-white)",
              border: "1px solid var(--border-subtle)",
              borderRadius: 12
            }}>
              <p style={{ margin: 0, fontSize: 14, color: "var(--text-dark)", fontWeight: 700 }}>
                No items match your search "{searchQuery}"
              </p>
              <p style={{ margin: "4px 0 14px", fontSize: 12, color: "var(--text-muted)" }}>
                Try searching with a different keyword or clear the search input.
              </p>
              <button
                type="button"
                className="m42-btn m42-btn-secondary"
                onClick={() => setSearchQuery("")}
                style={{ padding: "5px 14px", fontSize: 12, fontWeight: 700 }}
              >
                Clear Search
              </button>
            </div>
          ) : (
            filteredProposals.map(proposal => {
            const isProcessing = processingId === proposal.id;
            const hasCandidates = Boolean(proposal.candidates && proposal.candidates.length > 0);
            const activeCandIdx = selectedCandidateMap[proposal.id] || 0;
            const activeCand = hasCandidates ? proposal.candidates![activeCandIdx] : null;
            const activeCandUrl = activeCand ? activeCand.url : proposal.proposed_url;
            const activeCandRepo = activeCand ? activeCand.repo_path : proposal.proposed_repo_path;
            const activeCandType = activeCand ? activeCand.type : (selectedCategory === "card_logos" ? "logo" : "artwork");

            const currentImgKey = `current_${proposal.id}`;
            const proposedImgKey = `cand_${activeCandUrl}`;
            const currentFailed = failedImages[currentImgKey];
            const proposedFailed = failedImages[proposedImgKey];
            const canApprove = !currentFailed && !proposedFailed && !isProcessing && Boolean(activeCandUrl);

            return (
              <div 
                key={proposal.id}
                id={`item_card_${proposal.id}`}
                data-frame-id={`frame_card_${proposal.id}`}
                style={{
                  background: "var(--surf-white)",
                  border: proposal.status === "approved" 
                    ? "1.5px solid #16A34A" 
                    : proposal.status === "rejected" 
                    ? "1.5px solid #DC2626" 
                    : "1px solid var(--border-subtle)",
                  borderRadius: 12,
                  padding: 18,
                  display: "flex",
                  flexDirection: "column",
                  gap: 14,
                  boxShadow: "0 1px 3px rgba(16, 43, 45, 0.05)",
                  transition: "all 0.2s ease"
                }}
              >
                {/* Proposal Item Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--border-subtle)", paddingBottom: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 16, fontWeight: 700, color: "var(--deep-teal)" }}>
                      {proposal.name}
                    </span>
                    <span style={{ 
                      fontSize: 10, 
                      padding: "2px 6px", 
                      borderRadius: 4, 
                      background: "var(--tile-bg)", 
                      color: "var(--dark-teal)",
                      fontWeight: 700,
                      fontFamily: "monospace" 
                    }}>
                      ID: {proposal.id}
                    </span>
                    {proposal.character && (
                      <span style={{ fontSize: 11, color: "var(--text-dark)", background: "var(--tile-bg)", padding: "2px 8px", borderRadius: 4, border: "1px solid var(--border-subtle)", fontWeight: 600 }}>
                        {proposal.character}
                      </span>
                    )}
                    {selectedCategory === "skin_logo" && (
                      <span style={{ fontSize: 10, color: "#1D4ED8", background: "#DBEAFE", padding: "2px 8px", borderRadius: 4, border: "1px solid #93C5FD", fontWeight: 800 }}>
                        SKIN LOGO (SECTION B)
                      </span>
                    )}
                    {selectedCategory === "skin_main" && (
                      <span style={{ fontSize: 10, color: "#047857", background: "#D1FAE5", padding: "2px 8px", borderRadius: 4, border: "1px solid #6EE7B7", fontWeight: 800 }}>
                        SKIN MAIN ARTWORK (SECTION A)
                      </span>
                    )}
                    {selectedCategory === "gems" && proposal.level && (
                      <span style={{ fontSize: 10, color: "#B45309", background: "#FEF3C7", padding: "2px 8px", borderRadius: 4, border: "1px solid #FCD34D", fontWeight: 800 }}>
                        LEVEL {proposal.level} / 16
                      </span>
                    )}
                  </div>

                  {/* Status Badge */}
                  <div>
                    {proposal.status === "approved" && (
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 700, color: "#166534", background: "#DCFCE7", padding: "3px 8px", borderRadius: 6, border: "1px solid #86EFAC" }}>
                          <CheckCircle2 size={13} style={{ color: "#16A34A" }} /> Approved
                        </span>
                        {(selectedCategory === "skin_main" || selectedCategory === "skin_logo") && (
                          <button
                            type="button"
                            className="m42-btn m42-btn-ghost"
                            onClick={() => {
                              if (confirm(`Reject approval for "${proposal.name}" and re-open it with the 20 batch options?`)) {
                                handleReview(
                                  proposal, 
                                  "reject", 
                                  proposal.current_image, 
                                  selectedCategory === "skin_logo" ? "logo" : "artwork"
                                );
                              }
                            }}
                            disabled={isProcessing}
                            style={{ 
                              padding: "2px 8px", 
                              fontSize: 10.5, 
                              fontWeight: 700, 
                              color: "#DC2626", 
                              border: "1px solid #FCA5A5", 
                              borderRadius: 4,
                              background: "#FEF2F2",
                              cursor: "pointer"
                            }}
                            title="Reject approval and load the 20 candidate batch matching layout"
                          >
                            <X size={11} style={{ marginRight: 2 }} /> Reject & Load 20 Batch
                          </button>
                        )}
                      </div>
                    )}
                    {proposal.status === "rejected" && (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 700, color: "#991B1B", background: "#FEE2E2", padding: "3px 8px", borderRadius: 6, border: "1px solid #FCA5A5" }}>
                        <XCircle size={13} style={{ color: "#DC2626" }} /> Rejected
                      </span>
                    )}
                    {proposal.status === "pending" && (
                      <span style={{ fontSize: 11, fontWeight: 700, color: "#92400E", background: "#FEF3C7", padding: "3px 8px", borderRadius: 6, border: "1px solid #FCD34D" }}>
                        Pending Review
                      </span>
                    )}
                  </div>
                </div>

                {(selectedCategory === "frames" || selectedCategory === "skin_main" || selectedCategory === "skin_logo") && hasCandidates ? (
                  /* Dedicated Candidate Manual Matching Layout */
                  (() => {
                    const isSkinMain = selectedCategory === "skin_main";
                    const isSkinLogo = selectedCategory === "skin_logo";
                    const itemTypeLabel = isSkinMain ? "Skin Artwork" : isSkinLogo ? "Skin Logo" : "Frame";
                    const targetFieldParam = isSkinLogo ? "logo" : "artwork";

                    return (
                      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                        {/* Top Row: Original Item vs Active Selected Candidate live comparison */}
                        <div style={{ display: "grid", gridTemplateColumns: isSkinMain ? "260px 1fr" : "240px 1fr", gap: 16 }}>
                          {/* Left: Original Item */}
                          <div style={{ 
                            background: "var(--surf-white)", 
                            border: "1.5px solid var(--border-subtle)", 
                            borderRadius: 8, 
                            padding: 12,
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center"
                          }}>
                            <div style={{ width: "100%", display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 11, fontWeight: 700, color: "var(--text-muted)" }}>
                              <span>Original Active {itemTypeLabel}</span>
                              {currentFailed && <span style={{ color: "#DC2626" }}>Load Failed</span>}
                            </div>

                            <div style={{ 
                              width: "100%", 
                              height: isSkinMain ? 240 : 160, 
                              display: "flex", 
                              alignItems: "center", 
                              justifyContent: "center", 
                              background: "var(--tile-bg)",
                              borderRadius: 6,
                              border: "1px solid var(--tile-border)",
                              overflow: "hidden"
                            }}>
                              {currentFailed ? (
                                <div style={{ textAlign: "center", padding: 10, color: "#DC2626" }}>
                                  <AlertCircle size={22} style={{ margin: "0 auto 4px" }} />
                                  <div style={{ fontSize: 10, fontWeight: 700 }}>Failed to load</div>
                                </div>
                              ) : proposal.current_image ? (
                                <img 
                                  src={proposal.current_image} 
                                  alt={`Original ${itemTypeLabel}`}
                                  style={{ maxWidth: "100%", maxHeight: isSkinMain ? 230 : 150, objectFit: "contain" }}
                                  onLoad={() => handleImageLoad(currentImgKey)}
                                  onError={() => handleImageError(currentImgKey)}
                                />
                              ) : (
                                <span style={{ fontSize: 11, color: "var(--text-muted)", fontStyle: "italic" }}>No image</span>
                              )}
                            </div>

                            <div style={{ width: "100%", marginTop: 6, fontSize: 10.5, color: "var(--text-muted)", wordBreak: "break-all" }}>
                              <span style={{ fontWeight: 700, color: "var(--text-dark)" }}>Current Path:</span> <code>{proposal.current_image || "none"}</code>
                            </div>
                          </div>

                          {/* Right: Selected Candidate Detailed Preview & Approval */}
                          <div style={{ 
                            background: "var(--surf-white)", 
                            border: "1.5px solid var(--dark-teal)", 
                            borderRadius: 8, 
                            padding: 12,
                            display: "flex",
                            flexDirection: "column",
                            justifyContent: "space-between"
                          }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
                              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                <span style={{ fontSize: 12, fontWeight: 800, color: "#FFFFFF", background: "var(--dark-teal)", padding: "3px 10px", borderRadius: 4 }}>
                                  {activeCand?.label || "Candidate 1"} (Selected)
                                </span>
                                <span style={{ fontSize: 11, fontWeight: 700, color: "#15803D", background: "#DCFCE7", padding: "2px 8px", borderRadius: 4, border: "1px solid #86EFAC" }}>
                                  ✓ Confirmed Unused
                                </span>
                                {activeCand?.dimensions && (
                                  <span style={{ fontSize: 11, fontFamily: "monospace", fontWeight: 700, color: "var(--deep-teal)", background: "var(--tile-bg)", padding: "2px 6px", borderRadius: 4 }}>
                                    {activeCand.dimensions}
                                  </span>
                                )}
                              </div>
                              <div style={{ display: "flex", gap: 8 }}>
                                <button
                                  type="button"
                                  className="m42-btn m42-btn-ghost"
                                  onClick={() => handleReview(proposal, "skip")}
                                  disabled={isProcessing}
                                  style={{ padding: "4px 10px", fontSize: 11, fontWeight: 700 }}
                                >
                                  Skip {isSkinMain || isSkinLogo ? "Skin" : "Frame"}
                                </button>
                                <button
                                  type="button"
                                  className="m42-btn m42-btn-ghost"
                                  onClick={() => handleReview(proposal, "reject", activeCandUrl, targetFieldParam)}
                                  disabled={!activeCandUrl || isProcessing}
                                  style={{ padding: "4px 10px", fontSize: 11, fontWeight: 700, color: "#DC2626" }}
                                  title="Reject this candidate from being proposed for this skin"
                                >
                                  <X size={12} style={{ marginRight: 3 }} /> Reject Candidate
                                </button>
                                <button
                                  type="button"
                                  className="m42-btn m42-btn-primary"
                                  onClick={() => handleReview(proposal, "approve", activeCandUrl, targetFieldParam)}
                                  disabled={!activeCandUrl || isProcessing}
                                  style={{ padding: "5px 14px", fontSize: 11.5, fontWeight: 700 }}
                                >
                                  <Check size={13} style={{ marginRight: 4 }} />
                                  Approve {activeCand?.label || "Candidate"}
                                </button>
                              </div>
                            </div>

                            <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
                              <div style={{ 
                                width: isSkinMain ? 170 : 140, 
                                height: isSkinMain ? 220 : 140, 
                                flexShrink: 0,
                                display: "flex", 
                                alignItems: "center", 
                                justifyContent: "center", 
                                background: "var(--tile-bg)",
                                borderRadius: 6,
                                border: "1px solid var(--tile-border)",
                                overflow: "hidden"
                              }}>
                                {activeCandUrl ? (
                                  <img 
                                    key={activeCandUrl}
                                    src={activeCandUrl} 
                                    alt={activeCand?.label}
                                    style={{ maxWidth: "100%", maxHeight: isSkinMain ? 210 : 130, objectFit: "contain" }}
                                    onLoad={() => handleImageLoad(proposedImgKey)}
                                    onError={() => handleImageError(proposedImgKey)}
                                  />
                                ) : (
                                  <span style={{ fontSize: 11, color: "var(--text-muted)" }}>No preview</span>
                                )}
                              </div>
                              <div style={{ flex: 1, fontSize: 11, color: "var(--text-dark)", display: "flex", flexDirection: "column", gap: 5 }}>
                                <div><span style={{ fontWeight: 700, color: "var(--dark-teal)" }}>Filename:</span> <code>{activeCand?.filename || "none"}</code></div>
                                <div><span style={{ fontWeight: 700, color: "var(--dark-teal)" }}>Repo Asset Path:</span> <code>{activeCand?.repo_path || "none"}</code></div>
                                {activeCand?.reason && (
                                  <div style={{ background: "var(--tile-bg)", padding: "4px 8px", borderRadius: 4, border: "1px solid var(--border-subtle)" }}>
                                    <span style={{ fontWeight: 700, color: "var(--dark-teal)" }}>Match Rationale:</span> {activeCand.reason}
                                  </div>
                                )}
                                {activeCandUrl && (
                                  <div style={{ marginTop: 2 }}>
                                    <a 
                                      href={activeCandUrl} 
                                      target="_blank" 
                                      rel="noreferrer"
                                      style={{ color: "var(--dark-teal)", display: "inline-flex", alignItems: "center", gap: 3, textDecoration: "underline", fontSize: 11, fontWeight: 700 }}
                                    >
                                      Open Raw Image Asset in New Tab <ExternalLink size={10} />
                                    </a>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Bottom Row: Candidate Cards Grid */}
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 800, color: "var(--deep-teal)", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                            <span>{proposal.candidates!.length} Candidate Options (Click card to select & preview above, or click individual button to approve):</span>
                          </div>
                          <div style={{ 
                            display: "grid", 
                            gridTemplateColumns: selectedCategory === "frames" ? "repeat(5, 1fr)" : "repeat(auto-fill, minmax(130px, 1fr))", 
                            gap: 10 
                          }}>
                            {proposal.candidates!.map((c, cIdx) => {
                              const isSelected = activeCandIdx === cIdx;
                              const cKey = `cand_${c.url}`;
                              const cFailed = failedImages[cKey];
                              return (
                                <div
                                  key={cIdx}
                                  onClick={() => setSelectedCandidateMap(prev => ({ ...prev, [proposal.id]: cIdx }))}
                                  style={{
                                    background: isSelected ? "var(--surf-white)" : "var(--tile-bg)",
                                    border: isSelected ? "2px solid var(--dark-teal)" : "1px solid var(--border-subtle)",
                                    borderRadius: 8,
                                    padding: 10,
                                    cursor: "pointer",
                                    display: "flex",
                                    flexDirection: "column",
                                    alignItems: "center",
                                    gap: 6,
                                    boxShadow: isSelected ? "0 2px 8px rgba(23, 63, 67, 0.15)" : "none",
                                    transition: "all 0.15s ease",
                                    position: "relative"
                                  }}
                                >
                                  <div style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                    <span style={{
                                      fontSize: 10.5,
                                      fontWeight: 800,
                                      color: isSelected ? "#FFFFFF" : "var(--dark-teal)",
                                      background: isSelected ? "var(--dark-teal)" : "var(--surf-white)",
                                      padding: "2px 6px",
                                      borderRadius: 4,
                                      border: "1px solid var(--border-subtle)"
                                    }}>
                                      {c.label}
                                    </span>
                                    {isSelected && (
                                      <span style={{ fontSize: 9.5, fontWeight: 800, color: "var(--dark-teal)" }}>
                                        ✓ Active
                                      </span>
                                    )}
                                  </div>

                                  <div style={{ 
                                    width: "100%", 
                                    height: isSkinMain ? 135 : 105, 
                                    display: "flex", 
                                    alignItems: "center", 
                                    justifyContent: "center", 
                                    background: "var(--surf-white)",
                                    borderRadius: 6,
                                    border: "1px solid var(--border-subtle)",
                                    overflow: "hidden"
                                  }}>
                                    {cFailed ? (
                                      <span style={{ fontSize: 9.5, color: "#DC2626" }}>Failed to load</span>
                                    ) : (
                                      <img 
                                        src={c.url} 
                                        alt={c.label}
                                        style={{ maxWidth: "100%", maxHeight: isSkinMain ? 125 : 95, objectFit: "contain" }}
                                        onError={() => handleImageError(cKey)}
                                      />
                                    )}
                                  </div>

                                  <div style={{ width: "100%", display: "flex", justifyContent: "space-between", fontSize: 9.5 }}>
                                    <span style={{ fontWeight: 700, fontFamily: "monospace", color: "var(--deep-teal)" }}>{c.dimensions || (isSkinMain ? "1000 × 1200" : "400 × 400")}</span>
                                    <span style={{ color: "#15803D", fontWeight: 700 }}>Unused</span>
                                  </div>

                                  <div style={{ width: "100%", fontSize: 9.5, color: "var(--text-muted)", textAlign: "center", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={c.filename || c.repo_path}>
                                    <code>{c.filename || c.repo_path.split('/').pop()}</code>
                                  </div>

                                  <button
                                    type="button"
                                    className="m42-btn m42-btn-primary"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleReview(proposal, "approve", c.url, targetFieldParam);
                                    }}
                                    disabled={isProcessing}
                                    style={{
                                      width: "100%",
                                      padding: "5px 6px",
                                      fontSize: 10.5,
                                      fontWeight: 700,
                                      marginTop: 2,
                                      borderRadius: 4
                                    }}
                                  >
                                    <Check size={12} style={{ marginRight: 3 }} />
                                    Approve {c.label}
                                  </button>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    );
                  })()
                ) : (
                  /* Standard Side-by-Side Comparison Grid for other categories */
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                    {/* Left: Current Image */}
                    <div style={{ 
                      background: "var(--surf-white)", 
                      border: "1px solid var(--border-subtle)", 
                      borderRadius: 8, 
                      padding: 12,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center"
                    }}>
                      <div style={{ width: "100%", display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: 11, fontWeight: 700, color: "var(--text-muted)" }}>
                        <span>Current Active Image</span>
                        {currentFailed && <span style={{ color: "#DC2626" }}>Load Failed</span>}
                      </div>

                      <div style={{ 
                        width: "100%", 
                        height: previewBoxHeight, 
                        display: "flex", 
                        alignItems: "center", 
                        justifyContent: "center", 
                        background: "var(--tile-bg)",
                        borderRadius: 6,
                        border: "1px solid var(--tile-border)",
                        overflow: "hidden",
                        position: "relative"
                      }}>
                        {currentFailed ? (
                          <div style={{ textAlign: "center", padding: 12, color: "#DC2626" }}>
                            <AlertCircle size={24} style={{ margin: "0 auto 4px" }} />
                            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-dark)" }}>Image failed to load</div>
                          </div>
                        ) : proposal.current_image ? (
                          <img 
                            src={proposal.current_image} 
                            alt="Current"
                            style={{ maxWidth: "100%", maxHeight: imgMaxHeight, objectFit: "contain" }}
                            onLoad={() => handleImageLoad(currentImgKey)}
                            onError={() => handleImageError(currentImgKey)}
                          />
                        ) : (
                          <span style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>No current image</span>
                        )}
                      </div>

                      <div style={{ width: "100%", marginTop: 8, fontSize: 11, color: "var(--text-muted)", wordBreak: "break-all" }}>
                        <span style={{ fontWeight: 700, color: "var(--text-dark)" }}>Path:</span> <code>{proposal.current_image || "none"}</code>
                      </div>
                    </div>

                    {/* Right: Proposed GitHub Image / Candidates */}
                    <div style={{ 
                      background: "var(--surf-white)", 
                      border: "1px solid var(--border-subtle)", 
                      borderRadius: 8, 
                      padding: 12,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center"
                    }}>
                      <div style={{ width: "100%", display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: 11, fontWeight: 700, color: "var(--text-muted)" }}>
                        <span>Proposed Asset {hasCandidates ? `(${proposal.candidates!.length} matches)` : ""}</span>
                        {proposedFailed && <span style={{ color: "#DC2626" }}>Load Failed</span>}
                      </div>

                      {/* Candidate Choice Tabs / Pills */}
                      {hasCandidates && (
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10, width: "100%" }}>
                          {proposal.candidates!.map((c, cIdx) => (
                            <button
                              key={cIdx}
                              type="button"
                              onClick={() => setSelectedCandidateMap(prev => ({ ...prev, [proposal.id]: cIdx }))}
                              style={{
                                padding: "4px 8px",
                                fontSize: 10.5,
                                fontWeight: 700,
                                borderRadius: 6,
                                border: activeCandIdx === cIdx ? "1.5px solid var(--dark-teal)" : "1px solid var(--border-subtle)",
                                background: activeCandIdx === cIdx ? "var(--dark-teal)" : "var(--tile-bg)",
                                color: activeCandIdx === cIdx ? "#FFFFFF" : "var(--text-dark)",
                                cursor: "pointer",
                                transition: "all 0.15s ease"
                              }}
                            >
                              {c.label}
                            </button>
                          ))}
                        </div>
                      )}

                      <div style={{ 
                        width: "100%", 
                        height: previewBoxHeight, 
                        display: "flex", 
                        alignItems: "center", 
                        justifyContent: "center", 
                        background: "var(--tile-bg)",
                        borderRadius: 6,
                        border: "1px solid var(--tile-border)",
                        overflow: "hidden",
                        position: "relative"
                      }}>
                        {proposedFailed ? (
                          <div style={{ textAlign: "center", padding: 12, color: "#DC2626" }}>
                            <AlertCircle size={24} style={{ margin: "0 auto 4px" }} />
                            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-dark)" }}>GitHub asset failed to load</div>
                          </div>
                        ) : activeCandUrl ? (
                          <img 
                            key={activeCandUrl}
                            src={activeCandUrl} 
                            alt="Proposed"
                            style={{ maxWidth: "100%", maxHeight: imgMaxHeight, objectFit: "contain" }}
                            onLoad={() => handleImageLoad(proposedImgKey)}
                            onError={() => handleImageError(proposedImgKey)}
                          />
                        ) : (
                          <span style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>No candidate available</span>
                        )}
                      </div>

                      <div style={{ width: "100%", marginTop: 8, fontSize: 11, color: "var(--text-muted)", wordBreak: "break-all" }}>
                        <div><span style={{ fontWeight: 700, color: "var(--text-dark)" }}>Repo Path:</span> <code>{activeCandRepo || "none"}</code></div>
                        {activeCand?.dimensions && (
                          <div style={{ marginTop: 3 }}>
                            <span style={{ fontWeight: 700, color: "var(--text-dark)" }}>Dimensions:</span>{" "}
                            <span style={{ background: "var(--tile-bg)", padding: "1px 6px", borderRadius: 4, fontFamily: "monospace", fontWeight: 700, fontSize: 11, color: "var(--deep-teal)" }}>{activeCand.dimensions}</span>
                          </div>
                        )}
                        {activeCandUrl && (
                          <div style={{ marginTop: 4 }}>
                            {activeCand?.already_used_by ? (
                              <div style={{ color: "#B45309", background: "#FEF3C7", padding: "3px 8px", borderRadius: 4, border: "1px solid #FCD34D", fontWeight: 700, fontSize: 10.5 }}>
                                ⚠️ Already assigned to: <strong>{activeCand.already_used_by}</strong>
                              </div>
                            ) : (
                              <div style={{ color: "#15803D", background: "#DCFCE7", padding: "3px 8px", borderRadius: 4, border: "1px solid #86EFAC", fontWeight: 700, fontSize: 10.5, display: "inline-block" }}>
                                ✓ Distinct Asset (Not used elsewhere)
                              </div>
                            )}
                          </div>
                        )}
                        {activeCand?.reason && (
                          <div style={{ marginTop: 4, fontSize: 11, color: "var(--text-dark)", background: "var(--tile-bg)", padding: "4px 8px", borderRadius: 4, border: "1px solid var(--border-subtle)" }}>
                            <span style={{ fontWeight: 700, color: "var(--dark-teal)" }}>Match Rationale:</span> {activeCand.reason}
                          </div>
                        )}
                        {activeCandUrl && (
                          <div style={{ marginTop: 4 }}>
                            <a 
                              href={activeCandUrl} 
                              target="_blank" 
                              rel="noreferrer"
                              style={{ color: "var(--dark-teal)", display: "inline-flex", alignItems: "center", gap: 3, textDecoration: "underline", fontSize: 11, fontWeight: 700 }}
                            >
                              Open Raw URL <ExternalLink size={10} />
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Validation Warnings */}
                {(currentFailed || proposedFailed) && (
                  <div style={{ 
                    display: "flex", 
                    alignItems: "center", 
                    gap: 8, 
                    background: "#FEE2E2", 
                    border: "1px solid #FCA5A5", 
                    padding: "6px 12px", 
                    borderRadius: 6,
                    fontSize: 12,
                    color: "#991B1B",
                    fontWeight: 700
                  }}>
                    <AlertCircle size={15} style={{ color: "#DC2626" }} />
                    <span>Approval disabled: One or both images failed to load.</span>
                  </div>
                )}

                {/* Action Buttons */}
                <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 10, paddingTop: 6 }}>
                  <button
                    type="button"
                    className="m42-btn m42-btn-ghost"
                    onClick={() => handleReview(proposal, "skip")}
                    disabled={isProcessing}
                    style={{ padding: "6px 14px", fontSize: 12, fontWeight: 700 }}
                  >
                    Skip
                  </button>

                  <button
                    type="button"
                    className="m42-btn m42-btn-danger"
                    onClick={() => handleReview(
                      proposal, 
                      "reject", 
                      activeCandUrl || proposal.current_image, 
                      selectedCategory === "skin_logo" ? "logo" : "artwork"
                    )}
                    disabled={isProcessing}
                    style={{ 
                      padding: "6px 14px", 
                      fontSize: 12, 
                      fontWeight: 700 
                    }}
                  >
                    <X size={14} style={{ marginRight: 4 }} />
                    {proposal.status === "approved" && (selectedCategory === "skin_main" || selectedCategory === "skin_logo") 
                      ? "Reject Approval & Load 20 Batch" 
                      : "Reject Candidate"}
                  </button>

                  <button
                    type="button"
                    className="m42-btn m42-btn-primary"
                    onClick={() => handleReview(proposal, "approve", activeCandUrl, activeCandType as any)}
                    disabled={!canApprove}
                    style={{ 
                      padding: "6px 18px", 
                      fontSize: 12, 
                      fontWeight: 700,
                      opacity: canApprove ? 1 : 0.5,
                      cursor: canApprove ? "pointer" : "not-allowed"
                    }}
                  >
                    <Check size={14} style={{ marginRight: 4 }} />
                    {activeCandType === "logo" ? "Approve as Logo" : activeCandType === "artwork" ? "Approve as Main Artwork" : "Approve Replacement"}
                  </button>
                </div>
              </div>
            );
          }))}
        </div>
      )}
    </div>
  );
}
