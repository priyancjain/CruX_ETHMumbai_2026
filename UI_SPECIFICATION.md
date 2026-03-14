# AgentScore Frontend — UI Specification & Rebuild Guide

This document is a complete UI specification and rebuild guide for the **AgentScore** frontend. It provides all necessary architectural, design, and structural guidelines required for a developer (or an AI agent) to recreate the frontend perfectly from scratch.

---

## 1. Project Overview

**AgentScore** is a "CIBIL (Credit Bureau) for AI Agents" built to evaluate autonomous AI agents across various platforms (Virtuals, ElizaOS, Olas, Fetch.ai, ERC-8004). 
The frontend provides a sleek, dark-themed dashboard where users can:
- Search for agents by wallet address or ENS name.
- View a detailed credit scorecard, including a 22-signal radar chart, tier rating (S, A, B, C, D), and automated AI-driven rationale.
- Browse a global leaderboard of the highest-rated AI agents.
- Explore different AI platforms and their scoring methodologies.

The core user flow revolves around inputting a wallet address, queuing a real-time scoring job, waiting for the ML pipeline (via GPT-o3) to complete, and instantly viewing the resulting dashboard.

---

## 2. Tech Stack

The application is built on a modern, React-based Web3 stack:
- **Framework**: Next.js 14 (App Router, Server-Side Rendering)
- **Language**: TypeScript (Strict Mode)
- **Styling**: Tailwind CSS v3, Tailwind Typography
- **UI Primitives**: Radix UI (Headless components like Dialog, Progress, Tooltip, Select)
- **Icons**: Lucide React
- **Animations**: Framer Motion (used for score ring reveals and smooth transitions)
- **Charts**: Recharts (Radar charts for signals, Line charts for history)
- **Web3 / Blockchain**: Wagmi v2, Viem v2, RainbowKit v2
- **Data Fetching / State**: Axios + TanStack React Query v5
- **Realtime / Websockets**: Supabase Realtime (`@supabase/supabase-js`, `@supabase/ssr`)

---

## 3. Folder Structure

The project strictly follows the Next.js App Router paradigm:

```text
/frontend
 ├── /app                   # Next.js App Router (Pages & Layouts)
 │    ├── /agent/[wallet]   # Agent profile dashboard page
 │    ├── /leaderboard      # Global ranking table
 │    ├── /platforms        # Explanation of indexed platforms
 │    ├── globals.css       # Global CSS variables & Tailwind directives
 │    ├── layout.tsx        # Root HTML shell and Provider wrapping
 │    └── page.tsx          # Landing/Homepage
 ├── /components            # Reusable UI components
 │    ├── AgentTable.tsx    # Sortable data table for leaderboard
 │    ├── ConnectWallet.tsx # RainbowKit wrapper
 │    ├── FeatureRadar.tsx  # Recharts Radar for 22 signals
 │    ├── PlatformBadge.tsx # Colored pill indicators
 │    ├── providers.tsx     # Context providers (Wagmi, Query, etc)
 │    ├── ScoreCard.tsx     # Animated SVG ring & Tier display
 │    └── ScoreHistory.tsx  # Historical line chart
 ├── /lib                   # Utilities, Configs, API Clients
 │    ├── api.ts            # Axios endpoints and Types
 │    ├── supabase.ts       # Supabase client instantiation
 │    ├── utils.ts          # clsx + tailwind-merge helpers, date formatters
 │    └── wagmi.ts          # Chain configs for RainbowKit
 ├── public/                # Static assets
 ├── tailwind.config.ts     # Tailwind theme configuration
 └── package.json           # Dependencies and scripts
```

---

## 4. Pages

### 1. Homepage (`/app/page.tsx`)
- **Route**: `/`
- **Purpose**: Landing page introducing the protocol.
- **Layout**: Sticky top navbar, centered hero section with live stats pulse, search bar form, 3-column feature grid, stats strip, horizontal tier breakdown table, and a featured agents grid.
- **Key Functionality**: Pushing the routing state to `/agent/[wallet]` when the search form is submitted.

### 2. Agent Dashboard (`/app/agent/[wallet]/page.tsx`)
- **Route**: `/agent/[wallet_address]`
- **Purpose**: Displays the score, radar chart, and history for a specific agent.
- **Layout**: Top navbar with "Back" button and Wallet address copy button. The main content is a 3-column CSS Grid. The left column (1 span) holds the `ScoreCard`. The right column (2 spans) holds the `FeatureRadar`. Underneath, spanning all columns, is the `ScoreHistory`.
- **Key Functionality**: 
  - Subscribes to Supabase Realtime (`postgres_changes`) to listen for an `INSERT` event on the `scores` table for the specific wallet.
  - Handles the "Score Request" polling flow (hitting `/v1/score/request/{id}` every 3 seconds).

### 3. Leaderboard (`/app/leaderboard/page.tsx`)
- **Route**: `/leaderboard`
- **Purpose**: Ranks top agents across all platforms.
- **Layout**: Header with title, a filter row (Search input, Platform dropdown, Tier dropdown, Page Size), followed by the `AgentTable` component.
- **Key Functionality**: Fetches leaderboard from API. Features a fallback to hardcoded mock data if the API is offline. Client-side filtering and sorting.

### 4. Platforms Explorer (`/app/platforms/page.tsx`)
- **Route**: `/platforms`
- **Purpose**: Explains methodology and platform-specific attributes.
- **Layout**: List of broad cards detailing Virtuals, ElizaOS, Olas, Fetch.ai, and ERC-8004. Includes global aggregated stats fetched from the API.

---

## 5. Dashboard Layout (Agent Profile)

The main UI dashboard (`/agent/[wallet]`) is constructed using standard CSS Grid for responsive design:

- **Navbar**: Sticky, backdrop-blur, containing Breadcrumbs, ENS/Wallet display, and Connect Wallet button.
- **Main Container**: `max-w-6xl mx-auto px-6 py-8`.
- **Grid Layout**: `grid grid-cols-1 lg:grid-cols-3 gap-6`.
  - **Widget 1 (Left - 1 col)**: `ScoreCard.tsx` (Current Tier, circular progress, loan logic, GPT-o3 rationales).
  - **Widget 2 (Right - 2 cols)**: `FeatureRadar.tsx` (Data visualization of 22 signals divided into 4 key quadrants).
  - **Widget 3 (Bottom - Full width)**: `ScoreHistory.tsx` (Time series line chart bridging the full width).
- **Footer**: Agent metadata (First seen, Platform, ENS).

---

## 6. UI Components

### `ScoreCard.tsx`
- **Props**: `score` (data object), `onRescore` (function callback), `rescoring` (boolean).
- **Functionality**: Uses `framer-motion` to animate an SVG circle representing the 0-1000 score. Displays Maximum Loan and Collateral Requirements. Lists GPT-o3 rationales, strengths, and risk flags.

### `FeatureRadar.tsx`
- **Props**: `features` (Record of 22 signals).
- **Functionality**: Normalizes the 22 signals into a 0-100 scale. Wraps a Recharts `<RadarChart>` representing 4 main categories (On-Chain, Token, Protocol, Behavioral). Underneath the radar, displays a neat grid of miniature progress bars for every single individual metric.

### `AgentTable.tsx`
- **Props**: `agents` (Array of data), `loading` (boolean).
- **Functionality**: Render a sortable HTML `<table>`. Uses a custom `SkeletonRow` with shimmer effects when `loading` is true. Colors the top 3 ranks dynamically (Gold, Silver, Bronze badges).

### `PlatformBadge.tsx`
- **Props**: `platform` (string), `size` ('sm' | 'md').
- **Functionality**: Returns a stylized rounded pill (`rounded-full`) with an icon and specific border/text colors based on the platform name (e.g., Virtuals = teal, ElizaOS = purple).

---

## 7. Design System

The application uses a custom Tailwind configuration extending a strict dark mode palette.

### Colors
Defined in `tailwind.config.ts` under `theme.extend.colors`:
- **Backgrounds**: `background: "#0D1117"`, `surface: "#161B22"`, `surface2: "#1C2330"`
- **Borders**: `border: "#30363D"`
- **Brand/Accent**: `accent: "#20808D"`, `"accent-light": "#4CB8C4"`
- **Text**: `"text-primary": "#E6EDF3"`, `muted: "#8B949E"`
- **Tiers**:
  - `tier-s`: "#A855F7" (Purple)
  - `tier-a`: "#20808D" (Teal/Accent)
  - `tier-b`: "#3FB950" (Green)
  - `tier-c`: "#D29922" (Yellow)
  - `tier-d`: "#D15F5F" (Red)

### Typography
- **Primary Font**: Inter (sans-serif)
- **Monospace Font**: JetBrains Mono (used for wallet addresses and code blocks)

### Shapes & Spacing
- Cards always use `rounded-xl` borders.
- Buttons and inputs use `rounded-xl` or `rounded-lg`.
- Inputs have `bg-surface2` with `border-border`, changing to `border-accent` on focus.
- Micro-interactions use Tailwind's `transition-colors`.

---

## 8. State Management and Data Flow

1. **Global State**: Minimal. Uses standard React Context via `<Providers>` strictly to hold instances for Wagmi (Wallet connection) and React Query.
2. **Data Fetching**: The `lib/api.ts` file acts as the single source of truth for API calls using `axios`.
3. **Local State**: Managed with standard `useState`.
4. **Realtime**: Supabase is initialized on the client side in the Agent Profile page. It uses `supabase.channel().on('postgres_changes').subscribe()` to patch the local React state (`setScore`) instantly when the backend completes ML scoring and writes to the DB. No Redux or Zustand is required.

---

## 9. Environment Setup

Required Environment Variables (`.env.local`):
```env
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID="your_reown_cloud_project_id"
NEXT_PUBLIC_API_URL="http://localhost:8000"
NEXT_PUBLIC_SUPABASE_URL="https://your-project.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="your-anon-key"
```

To run:
```bash
npm install
npm run dev
```

---

## 10. Rebuild Instructions

To recreate this frontend exactly:

1. **Initialize Framework**: Run `npx create-next-app@latest .` using App Router, TS, Tailwind.
2. **Install Core Deps**: `npm i axios @tanstack/react-query @supabase/supabase-js @supabase/ssr framer-motion recharts lucide-react`
3. **Install UI Primitives**: `npm i @radix-ui/react-dialog @radix-ui/react-progress ... clsx tailwind-merge`
4. **Install Web3**: `npm i wagmi viem @rainbow-me/rainbowkit`
5. **Config Tailwind**: Copy the exact theme extensions and keyframes from `tailwind.config.ts`. Set root background to `#0D1117`.
6. **API Layer**: Create `lib/api.ts` mapping Axios instances to Next.js ENV vars. Set up the Supabase Realtime client in `lib/supabase.ts`.
7. **Build Components**: Start bottom-up. Create `PlatformBadge`, `ScoreCard`, `FeatureRadar`, `AgentTable`. Apply Framer Motion to the `ScoreCard` SVG circle.
8. **Build Pages**: Implement `app/page.tsx` (search flow), `app/leaderboard/page.tsx` (data tables), and tie it together in `app/agent/[wallet]/page.tsx` integrating the data fetching and Supabase channel listeners.
9. **Wrap App**: Place the `<Providers>` holding the Wagmi & Query clients in `app/layout.tsx`.
