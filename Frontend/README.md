# Frontend — Supply Chain Risk Intelligence Dashboard

React 19 + TypeScript + Vite 8 + Tailwind CSS v4 single-page dashboard for visualizing semiconductor supply chain risks.

## Tech Stack

- **React 19** with TypeScript
- **Vite 8** for dev server and bundling
- **Tailwind CSS v4** with `@tailwindcss/vite` plugin
- **shadcn/ui** (Radix primitives) for UI components
- **Framer Motion** for animations
- **react-globe.gl** + Three.js for 3D supply route visualization
- **TanStack React Query** for data fetching

## Prerequisites

- **Node.js** >= 18
- **npm** >= 9

## Setup

1. **Install dependencies:**

   ```bash
   cd Frontend
   npm install --legacy-peer-deps
   ```

   > `--legacy-peer-deps` is needed because `@tailwindcss/vite` hasn't published Vite 8 in its peer dependency range yet (support is merged but unreleased). This flag is safe to use here.

2. **Start the dev server:**

   ```bash
   npm run dev
   ```

   The app will be available at [http://localhost:5173](http://localhost:5173).

## Available Scripts

| Command             | Description                          |
| ------------------- | ------------------------------------ |
| `npm run dev`       | Start Vite dev server with HMR       |
| `npm run build`     | TypeScript check + production build   |
| `npm run lint`      | Run ESLint                           |
| `npm run preview`   | Preview the production build locally  |

## Project Structure

```
src/
├── components/
│   └── ui/          # shadcn/ui components (Toast, Tooltip, etc.)
├── data/
│   └── simulatedData.ts  # Hardcoded mock data (no live API yet)
├── hooks/           # Custom React hooks
├── lib/
│   └── utils.ts     # Utility functions (cn helper for Tailwind classes)
├── pages/
│   └── Index.tsx    # Main dashboard page composing all panels
├── App.tsx          # Root app component with routing
├── main.tsx         # Entry point
└── index.css        # Global styles + Tailwind imports
```

### Dashboard Panels

- **MetricsPanel** — Key risk metrics and KPIs
- **GlobeView** — 3D interactive globe showing supply routes
- **AgentWorkflow** — AI agent orchestration status
- **ScenariosPanel** — Risk scenario simulations
- **RiskTable** — Detailed risk data table

## Configuration

- Path alias `@` maps to `./src` (configured in `vite.config.ts` and `tsconfig.json`)
- Dark theme with IBM Plex fonts and risk-level color coding (red/amber/green)
- 12-column grid layout
