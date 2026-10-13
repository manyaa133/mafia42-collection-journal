# Mafia42 Collection Journal — Asset & Catalogue Migration Report

Generated: 2026-10-11

## 1. Summary of Migrated Catalogue Records

| Category | Record Count | Images Extracted | Notes |
| :--- | :--- | :--- | :--- |
| **Skins** | 334 | 334 full + 334 logos | All 334 skins migrated with full images, logos, characters, and CP |
| **Icons** | 173 | 171 | Union of bundled (168) and backup (144) yielding 173 unique icons |
| **Cards** | 42 | 42 full + 42 logos | All 42 playable character cards preserved |
| **Frames** | 158 | 158 | All 158 collectible frames with CP and descriptions |
| **Nameplates (NP)** | 221 | 196 bundled + 221 extra | 196 bundled matched via PDF match report + 25 custom nameplates |
| **Wallets** | 0 | 0 (none in backup) | Architecture supports 1 logo + 3 detail images per wallet entry |
| **Total Items** | **928** | **1498** | Fully converted from Base64 into persistent static files |

## 2. Asset Integrity & Storage

- All Base64 data URLs extracted into optimized, permanent binary files:
  - Skins: `backend/static/assets/skins/` and `frontend/public/assets/skins/`
  - Icons: `backend/static/assets/icons/` and `frontend/public/assets/icons/`
  - Cards: `backend/static/assets/cards/` and `frontend/public/assets/cards/`
  - Frames: `backend/static/assets/frames/` and `frontend/public/assets/frames/`
  - Nameplates: `backend/static/assets/nameplates/` and `frontend/public/assets/nameplates/`
- Every image is referenced via permanent URL path `/assets/<category>/<filename>`.
- No temporary blob URLs or raw Base64 strings remain in catalogue persistence.
- Zero external placeholder images used; 100% genuine Mafia42 assets preserved.

## 3. Metadata Quality

- Nameplates: Reconciled with `NAMEPLATE_METADATA_MATCH_REPORT.csv` from official reference PDF.
- Skin CP: Preserved exact numeric values (ranging from 50 to 988+ CP).
- Icon order: Canonical default order retained with custom order recovery support.
- Card/Skin relationships: Intact foreign key mapping via `cardId` and character roles.
