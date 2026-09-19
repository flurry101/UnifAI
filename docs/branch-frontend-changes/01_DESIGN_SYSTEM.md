# 01. RawBlock Brutalist Design System

## 1. Philosophy & Aesthetic Vision
The user interface follows the **Anti-Design System** — an unapologetic, structural brutalist design language tailored for heavy-industry enterprise operations:
- **Zero Border Radius (`rounded-none` / `0px`)**: Rounded corners are banned across all cards, buttons, modals, chips, and inputs.
- **Zero Shadows / Gradients (`shadow-none`)**: No drop shadows, blur filters, or elevation gradients. Elevation is depicted purely via high-contrast borders (e.g., 2px, 3px, 5px borders).
- **High-Contrast Monochromatic Contrast**: Pure black (`#000000`) and pure white (`#FFFFFF`) dominate the visual hierarchy.
- **Immediate State Inversion (`transition-none`)**: Hover and active states immediately invert backgrounds and text without smooth fade animations, delivering an industrial machine-like responsiveness.

---

## 2. Color Tokens

| Token Name | Hex Code | Utility Class | Purpose & Application |
|------------|----------|---------------|-----------------------|
| **Black** | `#000000` | `bg-raw-black`, `text-raw-black`, `border-raw-black` | Primary structural borders, dark text, inverted backgrounds. |
| **White** | `#FFFFFF` | `bg-raw-white`, `text-raw-white`, `border-raw-white` | Primary application canvas, inverted text. |
| **Sunken Surface** | `#F5F5F5` | `bg-raw-sunken` | Secondary data containers, metric chips, code inspection wells. |
| **Hyperlink Blue** | `#0000FF` | `text-raw-blue` | Hyperlinks only. |
| **Success Green** | `#008000` | `bg-raw-success`, `text-raw-success` | Approved CNMC status, identical candidate matches, confirmed audits. |
| **Warning Orange** | `#FFA500` | `bg-raw-warning`, `text-raw-warning` | Reviewer arbitration required, proposed catalog items, variant relationships. |
| **Error Red** | `#FF0000` | `bg-raw-error`, `text-raw-error` | Technical physical conflicts (Lane 6), rejected proposals, authentication errors. |

---

## 3. Typography Hierarchy

Imported via Google Fonts in `frontend/index.html` and configured in `frontend/tailwind.config.js`:

```css
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Work+Sans:wght@400;500;600;700&display=swap');
```

1. **Headlines (`font-headline`) — `Archivo Black, sans-serif`**:
   - Used for main section headers, page titles, and action modal headers.
   - Always rendered uppercase (`uppercase`), tight letter-spacing (`tracking-tight`).
2. **Body Text (`font-body` / `font-sans`) — `Work Sans, sans-serif`**:
   - Used for explanatory text, role descriptions, and documentation summaries.
3. **System Specs & Metrics (`font-mono`) — `Space Mono, monospace`**:
   - Used for CNMC Codes, Material IDs, CPSE Tenant badges, JSON attributes, table headers, and timestamp metadata.

---

## 4. Reusable Brutalist UI Primitives

All UI primitives are componentized in `frontend/src/components/`:

- **[`RawButton.jsx`](file:///home/flux/hack/unifAI/frontend/src/components/RawButton.jsx)**:
  - Supports `primary` (solid black, inverts to white), `secondary` (white with thick border, inverts to black), and `destructive` (red border/text).
  - Sizes: `small`, `medium`, `large`.
  - Enforces `0px` radius and `transition-none`.
- **[`RawCard.jsx`](file:///home/flux/hack/unifAI/frontend/src/components/RawCard.jsx)**:
  - Standard container with 2px solid black border.
  - `elevated` prop activates 3px structural border.
- **[`RawInput.jsx`](file:///home/flux/hack/unifAI/frontend/src/components/RawInput.jsx)**:
  - Form input with sunken background (`#F5F5F5`), 3px border, uppercase labels, and Space Mono typed text.
- **[`StatusChip.jsx`](file:///home/flux/hack/unifAI/frontend/src/components/StatusChip.jsx)**:
  - Bordered status badge showing `IDENTICAL`, `EQUIVALENT`, `VARIANT_OF`, `APPROVED`, `PROPOSED`, or `REJECTED`.

---

## 5. Product Positioning & Content Refinements

1. **Enterprise Commercial Positioning**:
   - Stripped all hackathon identifiers, `SIH26099`, and problem statement numbers.
   - Reframed platform tagline:
     > **"ONE NATION — ONE MATERIAL CODE."**  
     > *AI-Powered Standardization & Harmonization across CPSEs.*
2. **Sector Grid Simplification (`SectorGrid.jsx`)**:
   - Retained clean sector headings, CPSE participation tags, and mandate status.
