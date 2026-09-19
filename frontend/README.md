# unifAI Modular Brutalist Frontend

A responsive, high-density web interface built strictly according to the **RawBlock Brutalist Design System** using **React 18 + Vite + Tailwind CSS**.

Wired directly to the UnifAI FastAPI backend without requiring any modifications to existing backend code.

---

## Architecture & Component Hierarchy

```
frontend/
├── index.html                   # HTML entry point (Google Fonts: Archivo Black, Work Sans, Space Mono)
├── vite.config.js               # Vite config with React plugin and FastAPI /api proxy (:8000)
├── tailwind.config.js           # RawBlock color, typography, spacing, and border tokens
├── src/
│   ├── index.css                # RawBlock brutalist CSS resets, hover inversions, 0px radius enforcement
│   ├── App.jsx                  # Main coordinator with Header, Footer, and View Routing
│   ├── main.jsx                 # React root mount
│   ├── api/
│   │   ├── client.js            # Fetch wrapper with Bearer token injection, health check, and error handling
│   │   ├── auth.js              # Token management, persona configs, and JWT parsing
│   │   ├── materials.js         # Material master lookup & AI matching pipeline trigger (/materials/{id}/matches)
│   │   ├── governance.js        # Pending human review queue & decision recorder (/reviews/{id}/decision)
│   │   └── cnmc.js              # Common National Material Code (CNMC) catalog queries (/cnmc/)
│   ├── components/
│   │   ├── Header.jsx           # Brutalist corner logo (unifAI), live system status, and role switcher
│   │   ├── Footer.jsx           # Mandated footer: "© 2026 UNIFIED PLATFORM — ALL RIGHTS RESERVED. SYSTEM ONLINE."
│   │   ├── RawButton.jsx        # Buttons: Primary, Secondary, Ghost, Destructive with hover inversions
│   │   ├── RawCard.jsx          # Cards: Default (3px black border) and Elevated (5px black border)
│   │   ├── RawInput.jsx         # Inputs: Sunken #F0F0F0 fill, 3px/5px black border, Archivo Black labels
│   │   ├── StatusChip.jsx       # Chips: Active, Warning, Error, Default with 2px borders
│   │   ├── SectorGrid.jsx       # Target Sectors grid: Oil & Gas, Power, Steel, Mining, Heavy Engineering
│   │   └── RbacStatusModal.jsx  # Interactive RBAC security audit & permissions inspection dashboard
│   ├── context/
│   │   └── AuthContext.jsx      # React Context managing session, active role, and backend connectivity
│   └── views/
│       ├── LandingView.jsx      # Hero with problem statement line, target sectors, and workspace entrances
│       ├── UserView.jsx         # CPSE User: Material lookup, Lane 2/3 specs, AI match execution (Lanes 5–8)
│       ├── ReviewerView.jsx     # Technical Reviewer: Review queue, side-by-side technical diff, decisions
│       └── AdminView.jsx        # National Admin: Global CNMC master, cross-CPSE mapping lineage, audit logs
```

---

## Stakeholder Roles & Display

| Persona in Frontend | Backend DB Role | Responsibilities |
| :--- | :--- | :--- |
| **USER** | `CPSE_USER` | Look up native materials, inspect normalized descriptions and Lane 3 extracted parameters, execute real-time AI matching candidate generation. |
| **REVIEWER** | `TECHNICAL_REVIEWER` | Inspect candidate pairs flagged with technical conflicts, review side-by-side attribute comparisons, approve or reject linkages with technical rationale. |
| **ADMIN** | `NATIONAL_ADMIN` | Oversee Common National Material Catalog (CNMC) records, trace cross-CPSE convergence, and inspect live RBAC security status. |

---

## Quickstart

### 1. Run Development Server
```bash
cd frontend
npm run dev
```
The frontend starts on `http://localhost:3000` with automated proxying to the FastAPI backend on `http://localhost:8000`.

### 2. Build for Production
```bash
cd frontend
npm run build
npm run preview
```

---

## Design System Adherence
- **Colors**: Black (`#000000`), White (`#FFFFFF`), Blue (`#0000FF` reserved exclusively for hyperlinks).
- **Typography**: `Archivo Black` (headlines), `Work Sans` (body), `Space Mono` (code, inputs, chips).
- **Borders & Elevation**: 0px border radius everywhere (`radius-none`). Zero drop shadows (`shadow-none`). Visual hierarchy achieved exclusively through border thickness (`1px`, `3px`, `5px`).
- **Full Inversion**: Buttons invert black-to-white and white-to-black on hover and active states.

