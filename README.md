# Mafia42 Collection Journal — Multi-User Edition

> **Fan-Made Project** — This is an unofficial, fan-made collection tracker for Mafia42.
> It is not affiliated with, endorsed by, or associated with the official Mafia42 game or its developers.
> All game assets, characters, and content are the property of their respective owners.
> Visit the official game at [mafia42.com](https://mafia42.com).

---

A personal collection journal for **Mafia42** featuring authenticated user accounts, persistent personal collection data, server-side CP calculation, owner-only catalogue administration, skin–card relationships, and icon move controls.

---

## Key Highlights

- **Multi-User Architecture**: Every registered user maintains their own persistent database records. User A marking an item as owned never affects User B.
- **100% Genuine Asset Migration**: Reused and extracted all 334 skins, 173 icons, 42 character cards, 158 portrait frames, and 221 nameplates (including all 196 official bundled nameplates from the reference PDF), plus 2 wallets.
- **Zero Placeholders**: All base64 data URLs converted to permanent static binary image files (`.jpg`, `.webp`, `.png`) served directly.
- **Wallet Support**: Recreated wallet functionality with 1 main logo thumbnail + 3 associated detailed images in a 3-column grid layout with seamless navigation.
- **Skin–Card Relationship**: Cards display their associated skins; skins reference their character card. Ownership of a card and ownership of its skins remain fully independent.
- **Icon Move (Owner-Only)**: The owner can reorder icons using ◄ ► position controls, enforced server-side via RBAC.
- **Role-Based Access Control**:
  - `Visitor`: Browse shared catalogue, view items and unlock conditions.
  - `User`: Maintain personal collection ("I Have This"), track CP progress, manage profile, goals, notes, and achievements.
  - `Owner`: Exclusive administration authority to add, edit, reorder, delete catalogue entries, upload images, manage wallets, suspend abusive users, and view audit logs.
- **Authoritative CP Engine**: Collection CP combines Skins + Gems + Frames + Nameplates (Refinements and Postcards do not contribute, matching the original rules).

---

## Directory Structure

```
├── backend/
│   ├── app/
│   │   ├── config.py           # App settings & environment variables
│   │   ├── database.py         # SQLAlchemy engine & session maker
│   │   ├── models.py           # Relational schema (Users, Profiles, Catalogue, Collections, Audit)
│   │   ├── schemas.py          # Pydantic validation models (Pydantic V2)
│   │   ├── auth.py             # Bcrypt hashing, JWT issuance & RBAC dependencies
│   │   ├── seed.py             # Auto-seeder for catalogue & owner bootstrap
│   │   ├── routers/            # Auth, Catalogue, Collection, User, Admin
│   │   └── main.py             # FastAPI entrypoint & SPA static asset mount
│   ├── static/assets/          # Extracted binary image assets
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Complete responsive SPA UI
│   │   ├── api.ts              # Typed API client
│   │   ├── index.css           # Custom dark teal/aqua styling
│   │   └── main.tsx
│   ├── public/assets/          # Local static images for Vite dev server
│   ├── package.json
│   └── vite.config.ts
├── database/
│   └── seed_catalogue.json     # Migrated canonical catalogue records
├── scripts/
│   ├── migrate_assets_and_catalogue.py  # Idempotent migration script
│   └── bootstrap_owner.py               # Owner account CLI management
├── tests/
│   └── test_mafia42.py         # Automated test suite (15 test scenarios)
├── Dockerfile                  # Multi-stage production container build
├── docker-compose.yml          # App + PostgreSQL container stack
├── DEPLOYMENT.md               # Cloud & VPS deployment guide
├── MIGRATION_REPORT.md         # Detailed migration counts & report
└── .env.example                # Safe environment variables template
```

---

## Local Setup & Quickstart

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Install Backend Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Run Migration (If Seeding Assets Fresh)
```bash
python scripts/migrate_assets_and_catalogue.py
```

### 3. Build Frontend

> **Important**: If your project directory contains spaces in its name, `cd` into the `frontend` folder first before running `npm run build` to avoid Vite path errors.

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Start Server
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser at `http://127.0.0.1:8000`.

---

## Default Initial Owner Credentials

On initial startup, the backend automatically provisions the administrator account using environment variables (or defaults):
- **Email**: `owner@mafia42journal.com`
- **Username**: `Owner`
- **Password**: `OwnerJournal2026!Secure`

*(Change this password immediately after your first sign-in!)*

---

## Running Automated Tests

Run the full 15-scenario test suite verifying independence, persistence, security, CP calculations, card–skin relationships, and icon move security:

```bash
# Windows PowerShell
$env:PYTHONPATH="." ; pytest tests/test_mafia42.py -v

# Linux / macOS
PYTHONPATH=. pytest tests/test_mafia42.py -v
```

All 15 tests pass:

| # | Test | Coverage |
|---|------|----------|
| 1 | `test_1_independent_users` | User isolation |
| 2 | `test_2_persistence` | Data persistence |
| 3 | `test_3_cross_device_persistence` | Multi-session |
| 4 | `test_4_owner_permissions` | Owner RBAC |
| 5 | `test_5_ordinary_user_restrictions` | User restrictions |
| 6 | `test_6_direct_api_access` | Direct API access |
| 7 | `test_7_cross_user_attack_prevention` | Security |
| 8 | `test_8_image_migration_and_wallets` | Asset migration |
| 9 | `test_9_cp_calculations` | CP engine |
| 10 | `test_10_data_integrity` | Data integrity |
| 11 | `test_11_spa_production_serving` | SPA serving |
| 12 | `test_12_production_readiness` | Production config |
| 13 | `test_13_card_skin_relationship` | Skin–card links |
| 14 | `test_14_card_skin_independent_ownership` | Independent ownership |
| 15 | `test_15_icon_move_owner_security_and_persistence` | Icon move RBAC |

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for full instructions covering:
- Docker / docker-compose local deployment
- Render.com free-tier deployment (recommended)
- Railway and Fly.io alternatives
- PostgreSQL migration from SQLite
- Environment variable configuration

---

## Disclaimer

This is an **unofficial, fan-made** project. It is not affiliated with, endorsed by, or connected to the official Mafia42 game or its developers in any way. All Mafia42 game content, characters, and assets are the intellectual property of their respective owners. This project is intended purely as a personal collection tracking tool for fans of the game.
