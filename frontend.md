# SkillBridge — Frontend Guide

A reference for everything that lives in the `frontend/` folder. The repo is split into `frontend/` (this Next.js app) and — eventually — `backend/` (the API), so paths in this doc are relative to `frontend/` unless stated otherwise. SkillBridge takes a resume + a job description and produces a skill-fit score, a matched/missing skill breakdown, and a personalized learning plan.

**Run from `frontend/`:**

```bash
cd frontend
npm install     # only first time
npm run dev
```

---

## Tech stack

| Layer | Choice |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript 5 |
| UI | React 18 |
| Styling | Tailwind CSS 3 + CSS variable tokens |
| Animation | `motion` (Framer Motion successor) |
| Icons | `lucide-react` |
| Fonts | Geist Sans + Geist Mono (`geist` package) |
| Class merging | `clsx` + `tailwind-merge` |

There is currently no backend. All data comes from typed mock files under `lib/mock-data/` so the UI can be built end-to-end before the API exists.

---

## Directory layout

```
<repo root>
  frontend.md               This doc
  frontend/                 Everything below lives in here
  backend/                  (reserved — to be added later)

frontend/
  app/                      Next.js App Router
  layout.tsx                Root layout — fonts, body bg, noise texture
  globals.css               All design tokens (CSS variables) + base layer
  (marketing)/              Public landing & content pages — has nav + footer
    layout.tsx              MarketingNav + Footer wrapper
    page.tsx                Landing page (Hero → Showcase → ... → FinalCTA)
    about/  contact/  pricing/  privacy/  terms/
    resources/skills/  resources/courses/
  (app)/                    Authenticated app — has AppNav, no footer
    layout.tsx              AppNav + centered max-w 1100 main
    analyze/                Resume + JD upload
    running/[id]/           Mock loading screen between analyze and plan
    plans/[id]/             The results page (matched, missing, courses, projects)
    saved/                  List of saved plans
    jobs/                   Top job matches ranked by overlap
    dashboard/              Editable skill profile by category
  (auth)/                   Sign-in flow — no nav, no footer
    layout.tsx              Centered viewport
    signin/
  dev/components/           Visual playground for the UI primitives

components/
  ui/                       Reusable design-system primitives
  app/                      Components used inside the (app) shell
  landing/                  Components used on the marketing pages

lib/
  utils.ts                  cn() — clsx + tailwind-merge with custom font groups
  motion.ts                 Shared easing curves + fadeUp / stagger helpers
  format.ts                 SSR-safe date formatter
  mock-data/                Typed in-memory stand-in for the future API
    skills.ts  courses.ts  jobs.ts  plans.ts  dashboard.ts

tailwind.config.ts          Tokens → utility class mapping
next.config.mjs             (default Next config)
tsconfig.json               Path alias: @/* → repo root
```

### Route groups

Three URL-invisible groupings give each section its own chrome:

- `(marketing)` — public pages with `MarketingNav` + `Footer`
- `(app)` — product pages with sticky `AppNav` and a 1100px centered shell
- `(auth)` — bare centered viewport, no nav

---

## Pages at a glance

### Marketing (`(marketing)`)

| Route | Composition |
|---|---|
| `/` | `Hero` → `Showcase` → `HowItWorks` → `Dimensions` → `Comparison` → `FAQ` → `Trust` → `FinalCTA` |
| `/pricing` `/about` `/contact` `/privacy` `/terms` | `StubPage` content slots |
| `/resources/skills` `/resources/courses` | Reference catalogues |

### App (`(app)`)

| Route | What it does |
|---|---|
| `/analyze` | Resume dropzone + JD textarea, "Analyze the gap" CTA |
| `/running/[id]` | 6-stage progress animation, auto-routes to `/plans/[id]` |
| `/plans/[id]` | **Results page**: matched/missing chips, recommended courses, recommended projects, sticky save bar |
| `/saved` | Saved plans list (`PlanRow`) |
| `/jobs` | Job match cards ranked by overlap |
| `/dashboard` | Skill profile, editable per category (`SkillCategorySection`) |

### Auth (`(auth)`)

| Route | What it does |
|---|---|
| `/signin` | Single sign-in card, centered |

### Dev

| Route | What it does |
|---|---|
| `/dev/components` | Visual showcase of every UI primitive — quick QA surface |

---

## UI primitives — `components/ui/`

Stateless, design-system building blocks. Re-export through `components/ui/index.ts`.

| File | Notes |
|---|---|
| `Button.tsx` | `primary` / `secondary` / `ghost`, sizes `sm`/`md`/`lg`, optional `leftIcon`/`rightIcon`/`loading`. Primary uses an accent-blue glow shadow. |
| `ButtonLink.tsx` | Same look as Button, but renders a `next/link` `<Link>`. |
| `IconButton.tsx` | Round 32px button for toolbar-style actions. Tap-scale animation. |
| `Card.tsx` | `bg-bg-secondary` panel with border, 16/24px padding (`compact`), optional `interactive` hover. |
| `Chip.tsx` | Variants drive semantic color: `matched` (green), `missing` (red), `score` (cyan recommendation), `premium` (paid label, currently neutral white), `neutral`, `removable`. |
| `Input.tsx` / `Textarea.tsx` | Transparent border-only fields; focus shows accent ring. |
| `Divider.tsx` | 1px hairline with `none`/`sm`/`md`/`lg` vertical spacing. |

---

## App components — `components/app/`

Composed from `ui/` primitives, used inside `(app)` routes.

| File | Used by | Notes |
|---|---|---|
| `AppNav.tsx` | `(app)/layout` | Sticky top bar; tab underline animates with `motion.layoutId`; avatar dropdown. |
| `ResumeDropzone.tsx` | `analyze` | Drag-and-drop file picker with hover/drop counter. |
| `StageList.tsx` | `running` | Animated checklist with pulsing active indicator. |
| `SkillMatchPanel.tsx` | `plans/[id]` | Side-by-side matched (green) / missing (red) chip lists with staggered fade-in. |
| `CourseCard.tsx` | `plans/[id]` | Recommendation card with cyan left border (`border-l-score`); chips use the `score` variant since courses *fill* gaps, they don't represent success. |
| `ProjectCard.tsx` | `plans/[id]` | "Build with what you have" / "Build after Course 1" project; nested elevated panel for the README highlight. |
| `StickySaveBar.tsx` | `plans/[id]` | Fixed bottom-center save bar, lifts on `bg-elevated`. |
| `PlanRow.tsx` | `saved` | Single-line plan summary with matched/missing counts. |
| `JobCard.tsx` | `jobs` | Job posting with company logo tile, matched + missing chips, two CTAs. |
| `SkillCategorySection.tsx` | `dashboard` | Editable chip group with inline-add input; uses Framer's `AnimatePresence` `popLayout` mode. |

---

## Landing components — `components/landing/`

Visual, mostly decorative components for the marketing page. Heavier use of motion, gradients, and SVG.

| File | Role |
|---|---|
| `Wordmark.tsx` | Logo: cyan tile with a small suspension-bridge SVG (pylons, parabolic cable, deck, back-stays, suspenders). |
| `MarketingNav.tsx` | Sticky nav, blurred background, Cmd-K hint. |
| `Hero.tsx` | Headline with motion-traced underline, parallax orbs, mesh grid, mouse-tracked shifts. |
| `HeroBridge.tsx` | Decorative SVG suspension bridge fixed at the bottom of the hero (the visual the wordmark mark mirrors). |
| `HeroDocs.tsx` | Three fanned cards: **Resume** (current skills as green chips) → **Step** → **Job** (required = red chips, preferred classified vs the resume). |
| `Showcase.tsx` | Composite-score showcase block with animated trend chart and gauge. |
| `HowItWorks.tsx` | 3-step grid with custom mini-visuals per step. |
| `Dimensions.tsx` | Skill-depth dimensions panel. |
| `Comparison.tsx` | "Us vs ATS" comparison table. |
| `FAQ.tsx` | Accordion with cyan rotate-icon. |
| `Trust.tsx` | Logo strip / social proof. |
| `FinalCTA.tsx` | Closing call to action. |
| `Footer.tsx` | 4-column footer with wordmark + links. |
| `GlowSection.tsx` | Reusable section with radial accent glow. |
| `StubPage.tsx` | Generic placeholder used by pricing/about/contact/privacy/terms. |
| `screenshots/` | Static asset folder. |

---

## Design system

### Color tokens (`app/globals.css`)

All colors are CSS variables on `:root`, exposed as Tailwind utilities through `tailwind.config.ts`. The semantic rules are:

| Meaning | Token | Hex |
|---|---|---|
| Page bg | `--bg` | `#171F3D` |
| Card / panel bg | `--bg-secondary` | `#1E284D` |
| Elevated surface (sticky bar, dropdown, README panel) | `--bg-elevated` | `#25305A` |
| Hover surface | `--bg-elevated-hi` | `#2C3868` |
| Border | `--border` | `#2A3A5F` |
| Body text | `--text` | `#F8FAFC` |
| Secondary text | `--text-muted` | `#CBD5E1` |
| Subtle text | `--text-subtle` | `#94A3B8` |
| Primary action / link | `--accent` | `#3B82F6` |
| Score / analytics / recommendations | `--score` | `#22D3EE` |
| Soft analytics blue (section headings) | `--score-soft` | `#60A5FA` |
| Success / matched | `--matched-text` | `#34D399` (bg/border at 15/35% opacity) |
| Missing / gap | `--missing-text` | `#FCA5A5` (bg/border at 15/35% opacity) |
| Warning / medium-priority | `--warning-text` | `#FBBF24` |
| Paid / premium | `--premium` | `#F8FAFC` (purple removed; reads as neutral white) |

Light mode (`html.light`) overrides the same tokens with a warm-beige palette. `.noise` on `<body>` adds an ~1.2% radial dot texture so dark areas don't look flat.

**Glow utilities** (`tailwind.config.ts`):

```
shadow-glow         0 0 24px var(--accent-glow)
shadow-glow-soft    0 0 24px var(--accent-glow-soft)
shadow-glow-strong  0 0 48px var(--accent-glow)
```

**Color rule (enforced project-wide):**

- Green = matched / success only
- Cyan/blue = scores, recommendations, links, analytics
- Red = missing skills / gaps
- Amber = optional medium-priority warnings
- Purple = paid/premium *only*, used lightly (currently aliased to white)

### Typography

Defined in `tailwind.config.ts → fontSize`:

| Class | Size | Use |
|---|---|---|
| `text-h1` | 56 / 1.15 / 500 | Display |
| `text-h2` | 40 / 1.15 / 500 | Page hero |
| `text-h3` | 28 / 1.15 / 500 | Page title |
| `text-h4` | 22 / 1.15 / 500 | Section heading |
| `text-h5` | 18 / 1.15 / 500 | Card title |
| `text-body` | 16 / 1.6 / 400 | Body |
| `text-caption` | 13 / 1.6 / 400 | Caption / chip |

Font weights are restricted to `400 / 500 / 600 / 700`. Stack: Geist Sans (UI), Geist Mono (numbers, codes, tabular data).

### Radii

`rounded-btn` 8px · `rounded-card` 12px · `rounded-panel` 16px · `rounded-pill` 9999px

### Motion

Centralized in `lib/motion.ts`:

```ts
ease.out      [0.23, 1, 0.32, 1]
ease.inOut    [0.77, 0, 0.175, 1]
ease.drawer   [0.32, 0.72, 0, 1]   // iOS-like

fadeUp(delay, reduceMotion)        // standard entry animation
stagger(gap)                       // parent variant
```

Every component honors `useReducedMotion()` — when true, transforms collapse to opacity-only fades.

---

## Data layer

`lib/mock-data/` is a temporary, fully typed stand-in for `/api/*` endpoints. Each file exports its types alongside the data so consumers can swap to a real fetch later without touching call-sites.

| File | Exports |
|---|---|
| `skills.ts` | `Skill`, `SkillCategory`, `SKILLS`, `getSkillById`, `getSkillsByCategory` |
| `courses.ts` | `Course`, `COURSES`, `getCourseById`, `getCoursesBySkillId` |
| `jobs.ts` | Job postings + ranking helpers |
| `plans.ts` | `Plan`, `PlanProject`, `PlanCourse`, `PLANS`, `getPlanById`, `getRecentPlans` |
| `dashboard.ts` | `DASHBOARD` snapshot — `skills_by_category`, `last_updated_*` |

Skills follow a canonical `id` with optional `aliases`, grouped by `category` (`Languages`, `Frameworks`, `Tools`, `Cloud`, `Concepts`). Plans reference skills/courses *by id*, never by inlined data.

---

## Conventions

- **Path alias** — always import via `@/...` (configured in `tsconfig.json`).
- **Class composition** — use `cn(...)` from `lib/utils.ts`. It runs `clsx` then `tailwind-merge` with our custom `text-h1…h5/body/caption` group, so utilities collide correctly.
- **Color usage** — never hand-pick a hex. Use the semantic Tailwind utilities (`text-matched-text`, `bg-score-bg`, `border-missing-border`, etc.). New semantic categories should be added to `globals.css` *and* exposed in `tailwind.config.ts`.
- **Cards** — use `<Card>` rather than div+border combos so card surface stays one variable away from a global change.
- **Chips** — use `<Chip variant="...">` rather than custom pills. Add a new variant if the semantic doesn't exist.
- **Animations** — pull easing from `lib/motion.ts`; respect `useReducedMotion()`. Keep durations under ~300ms for UI, longer only for hero set-pieces.
- **Comments** — add only for non-obvious *why*. The codebase has short rationale comments where SSR, glow, or perceptual choices are subtle.
- **Dates** — never call `toLocaleDateString` (SSR/locale mismatch); use `formatDate(iso)` from `lib/format.ts`.
- **Mock data** — when adding a new screen, add the typed mock first, then the UI. The data shape is the contract.

---

## How to extend

| Goal | Where to start |
|---|---|
| Add a new app page | Make a folder under `app/(app)/<route>/`, create `page.tsx`. The `(app)` layout adds `AppNav` + the centered shell automatically. |
| Add a new marketing section | Create a component in `components/landing/`, then drop it into `app/(marketing)/page.tsx`. |
| Add a new chip color | Append a variant to `Chip.tsx`, add the matching `--<name>-bg/text/border` to `globals.css`, expose them in `tailwind.config.ts`. |
| Add a new card type | Compose with `<Card>`; respect `bg-bg-secondary` so it sits above the page bg, and lift any nested panel to `bg-elevated`. |
| Add a real API | Replace each `lib/mock-data/*.ts` consumer (`getPlanById`, etc.) with a fetch wrapper that returns the same types. The screens shouldn't notice. |

---

## Quick file index

```
app/layout.tsx                            Fonts + body + globals.css import
app/globals.css                           ALL design tokens + base layer + .noise
tailwind.config.ts                        Tokens → utilities, font sizes, radii, shadows
lib/utils.ts                              cn() helper
lib/motion.ts                             ease + fadeUp + stagger
lib/format.ts                             formatDate (SSR-safe)
components/ui/index.ts                    Re-exports for primitives
```

That's the whole frontend.
