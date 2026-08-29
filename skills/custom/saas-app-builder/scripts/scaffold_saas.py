#!/usr/bin/env python3
"""
SaaS App Monorepo Scaffolder CLI.
Deterministically generates a production-ready full-stack SaaS application
with React 19, Vite 6, Tailwind CSS v4, shadcn/ui primitives, Express on port 3031,
and an integrated 4-harness test suite (Vitest + Testing Library + Supertest + Zod).
"""

import sys
import os
import json
import argparse
from pathlib import Path

# ==============================================================================
# Centralized Package & Dependency Manifest (Easily Upgradable)
# ==============================================================================
PACKAGE_MANIFEST = {
    "name": "my-saas-app",
    "version": "1.0.0",
    "private": True,
    "type": "module",
    "scripts": {
        "dev": "tsx watch server/server.ts",
        "dev:client": "vite --config client/vite.config.ts client",
        "build": "vite build --config client/vite.config.ts client && tsc -p server/tsconfig.json",
        "start": "NODE_ENV=production tsx server/server.ts",
        "test": "vitest run",
        "test:watch": "vitest",
        "test:coverage": "vitest run --coverage",
        "typecheck": "tsc --noEmit -p client/tsconfig.json && tsc --noEmit -p server/tsconfig.json",
        "verify": "npm run typecheck && npm run test",
        "seed": "tsx server/seed/seedUsers.ts"
    },
    "dependencies": {
        "react": "^19.0.0",
        "react-dom": "^19.0.0",
        "react-router-dom": "^7.1.0",
        "@tanstack/react-query": "^5.62.0",
        "zustand": "^5.0.2",
        "lucide-react": "^0.468.0",
        "clsx": "^2.1.1",
        "tailwind-merge": "^2.5.5",
        "class-variance-authority": "^0.7.1",
        "@radix-ui/react-slot": "^1.1.1",
        "zod": "^3.24.1",
        "express": "^4.21.2",
        "cors": "^2.8.5"
    },
    "devDependencies": {
        "@tailwindcss/vite": "^4.0.0",
        "tailwindcss": "^4.0.0",
        "vite": "^6.0.3",
        "@vitejs/plugin-react": "^4.3.4",
        "typescript": "^5.7.2",
        "@types/react": "^19.0.1",
        "@types/react-dom": "^19.0.1",
        "@types/express": "^5.0.0",
        "@types/cors": "^2.8.17",
        "@types/node": "^22.10.1",
        "tsx": "^4.19.2",
        "vitest": "^2.1.8",
        "@testing-library/react": "^16.1.0",
        "@testing-library/jest-dom": "^6.6.3",
        "@testing-library/user-event": "^14.5.2",
        "jsdom": "^25.0.1",
        "supertest": "^7.0.0",
        "@types/supertest": "^6.0.2"
    }
}

# ==============================================================================
# File Templates
# ==============================================================================

ROOT_TSCONFIG = """{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": false,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["client/src/*"],
      "@shared/*": ["shared/*"]
    }
  },
  "include": ["client/src", "server", "shared"]
}
"""

VITEST_CONFIG = """import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./client/src/test/setup.ts'],
    include: [
      'client/src/**/*.{test,spec}.{ts,tsx}',
      'server/**/*.{test,spec}.ts'
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html']
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './client/src'),
      '@shared': path.resolve(__dirname, './shared')
    }
  }
});
"""

COMPONENTS_JSON = """{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "client/src/index.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils"
  }
}
"""

GITIGNORE = """node_modules/
dist/
build/
.env
.env.local
coverage/
.DS_Store
*.log
"""

ROOT_README_MD = """# 🚀 {app_name}

> A modern, full-stack, feature-driven SaaS platform built with React 19, Tailwind CSS v4, shadcn/ui, and Express single-port serving on port 3031.

---

## ⚡ Tech Stack

- **Frontend**: React 19, Vite 6, React Router v7, `@tanstack/react-query` v5, Zustand v5
- **Styling & UI**: Tailwind CSS v4 (`@tailwindcss/vite`), shadcn/ui primitives, Lucide Icons
- **Backend**: Express + TypeScript (TSX) on **Port 3031**
- **Test Suite**: Vitest, `@testing-library/react`, Supertest
- **Contracts**: Shared Zod schemas (`@shared/schemas`)
- **Database**: JSON File Storage with thread-safe file persistence (`data/`)

---

## 🛠️ Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Seed Demo Database
```bash
npm run seed
```

### 3. Start Development Server (Port 3031)
```bash
npm run dev
```
Open [http://localhost:3031](http://localhost:3031) in your browser.

---

## 🧪 Testing & Verification Suite

This project includes a **4-harness verification pipeline**:

| Command | Action | Description |
| :--- | :--- | :--- |
| `npm test` | **Vitest Run** | Runs all client component tests and backend API integration tests |
| `npm run test:watch` | **Interactive Vitest** | Runs tests in watch mode for active TDD development |
| `npm run test:coverage`| **Coverage Report** | Generates detailed line and branch coverage metrics |
| `npm run typecheck` | **TypeScript Compiler** | Verifies static types across client (`client/tsconfig.json`) and server (`server/tsconfig.json`) |
| `npm run verify` | **Full Verification** | Executes both `typecheck` and `test` in sequence |

---

## 📁 Monorepo Structure

```text
{app_name}/
├── client/                          # React 19 + Tailwind v4 + shadcn frontend
│   └── src/
│       ├── features/                # Feature-driven domain modules
│       ├── components/ui/           # shadcn/ui component primitives
│       ├── components/layout/       # AppLayout, Navbar, Sidebar, ThemeToggle
│       ├── pages/                   # Landing, Login, Signup, Dashboard
│       └── lib/                     # api.ts, state.ts, utils.ts
├── server/                          # Express + TypeScript backend
│   ├── routes/                      # API route handlers (/api/auth, /api/users, etc.)
│   ├── controllers/                 # Business logic controllers
│   ├── middleware/                  # authMiddleware.ts, validation
│   └── __tests__/                   # Supertest API endpoint tests
├── shared/                          # Shared between client & server
│   └── schemas/                     # Zod schemas (authSchema.ts, etc.)
├── data/                            # JSON file database (users.json, sessions.json)
├── docs/                            # PROJECT_STATUS.md, QUICKSTART.md, TECHNICAL.md
├── package.json                     # Scripts and dependencies
└── vitest.config.ts                 # Dual-environment test configuration
```

---

## 🌐 API Endpoints

- `GET /api/health` - Server health status
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Authenticated current user profile
- `GET /api/users` - List users (authenticated)
- `GET /api/users/:id` - Get user by ID (authenticated)

---

## 📄 License
Apache-2.0
"""


CLIENT_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%230070F3' stroke-width='2'><path d='M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5'/></svg>" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SaaS Platform</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  </head>
  <body class="min-h-screen bg-background font-sans antialiased text-foreground">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

CLIENT_VITE_CONFIG = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  root: path.resolve(__dirname),
  build: {
    outDir: path.resolve(__dirname, '../dist/client'),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:3031',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@shared': path.resolve(__dirname, '../shared'),
    },
  },
});
"""

CLIENT_TSCONFIG = """{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": false,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@shared/*": ["../shared/*"]
    }
  },
  "include": ["src", "../shared"]
}
"""

CLIENT_INDEX_CSS = """@import "tailwindcss";

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 217.2 91.2% 59.8%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 224.3 76.3% 48%;
  }

  * {
    border-color: hsl(var(--border));
  }

  body {
    background-color: hsl(var(--background));
    color: hsl(var(--foreground));
    font-family: 'Inter', sans-serif;
  }
}
"""

CLIENT_MAIN_TSX = """import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
"""

CLIENT_APP_TSX = """import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/lib/state';
import Landing from '@/pages/Landing';
import Login from '@/pages/Login';
import Signup from '@/pages/Signup';
import Dashboard from '@/pages/Dashboard';
import AppLayout from '@/components/layout/AppLayout';

export default function App() {
  const { theme } = useAuthStore();

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route element={<AppLayout />}>
        <Route path="/dashboard" element={<Dashboard />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
"""

CLIENT_UTILS_TS = """import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
"""

CLIENT_API_TS = """interface RequestOptions extends RequestInit {
  data?: any;
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { data, headers, ...customConfig } = options;
  const token = localStorage.getItem('saas_auth_token');

  const config: RequestInit = {
    method: data ? 'POST' : 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    ...customConfig,
  };

  if (data) {
    config.body = JSON.stringify(data);
  }

  const response = await fetch(endpoint, config);
  const responseData = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(
      response.status,
      responseData.error || responseData.message || 'API request failed',
      responseData
    );
  }

  return responseData as T;
}
"""

CLIENT_STATE_TS = """import { create } from 'zustand';

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  avatar?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  toggleTheme: () => void;
  toggleSidebar: () => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: {
    id: 'usr_demo_1',
    email: 'alex@example.com',
    name: 'Alex Rivera',
    role: 'admin',
    avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80',
  },
  token: 'mock_jwt_token_alex',
  theme: (typeof window !== 'undefined' && (localStorage.getItem('saas_theme') as 'light' | 'dark')) || 'light',
  sidebarOpen: true,
  setUser: (user) => set({ user }),
  setToken: (token) => {
    if (token) localStorage.setItem('saas_auth_token', token);
    else localStorage.removeItem('saas_auth_token');
    set({ token });
  },
  setTheme: (theme) => {
    localStorage.setItem('saas_theme', theme);
    set({ theme });
  },
  toggleTheme: () =>
    set((state) => {
      const nextTheme = state.theme === 'light' ? 'dark' : 'light';
      localStorage.setItem('saas_theme', nextTheme);
      return { theme: nextTheme };
    }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  logout: () => {
    localStorage.removeItem('saas_auth_token');
    set({ user: null, token: null });
  },
}));
"""

CLIENT_BUTTON_TSX = """import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

export const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background cursor-pointer select-none',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'underline-offset-4 hover:underline text-primary',
      },
      size: {
        default: 'h-10 py-2 px-4',
        sm: 'h-9 px-3 rounded-md text-xs',
        lg: 'h-11 px-8 rounded-md text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';
"""

CLIENT_CARD_TSX = """import * as React from 'react';
import { cn } from '@/lib/utils';

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('rounded-lg border bg-card text-card-foreground shadow-sm', className)}
      {...props}
    />
  )
);
Card.displayName = 'Card';

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />
  )
);
CardHeader.displayName = 'CardHeader';

export const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn('text-2xl font-semibold leading-none tracking-tight', className)} {...props} />
  )
);
CardTitle.displayName = 'CardTitle';

export const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('text-sm text-muted-foreground', className)} {...props} />
  )
);
CardDescription.displayName = 'CardDescription';

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
  )
);
CardContent.displayName = 'CardContent';

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center p-6 pt-0', className)} {...props} />
  )
);
CardFooter.displayName = 'CardFooter';
"""

CLIENT_INPUT_TSX = """import * as React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';
"""

CLIENT_BADGE_TSX = """import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

export const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
        secondary: 'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
        destructive: 'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80',
        outline: 'text-foreground',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
"""

CLIENT_THEME_TOGGLE_TSX = """import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useAuthStore } from '@/lib/state';
import { Button } from '@/components/ui/button';

export function ThemeToggle() {
  const { theme, toggleTheme } = useAuthStore();

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      className="text-muted-foreground hover:text-foreground"
    >
      {theme === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
}
"""

CLIENT_NAVBAR_TSX = """import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Layers, Menu, LogOut } from 'lucide-react';
import { useAuthStore } from '@/lib/state';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { Button } from '@/components/ui/button';

export function Navbar() {
  const { user, logout, toggleSidebar } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center px-4 md:px-6 justify-between">
        <div className="flex items-center gap-3">
          {user && (
            <Button variant="ghost" size="icon" onClick={toggleSidebar} className="md:hidden">
              <Menu className="h-5 w-5" />
            </Button>
          )}
          <Link to="/" className="flex items-center gap-2 font-bold text-lg text-primary tracking-tight">
            <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <Layers className="h-5 w-5" />
            </div>
            <span>SaaS Pilot</span>
          </Link>
        </div>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          {user ? (
            <div className="flex items-center gap-3">
              <div className="hidden md:flex flex-col text-right">
                <span className="text-sm font-medium leading-none">{user.name}</span>
                <span className="text-xs text-muted-foreground">{user.email}</span>
              </div>
              <Button variant="outline" size="sm" onClick={handleLogout} className="gap-1.5">
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Sign Out</span>
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" asChild>
                <Link to="/login">Sign In</Link>
              </Button>
              <Button size="sm" asChild>
                <Link to="/signup">Get Started</Link>
              </Button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
"""

CLIENT_SIDEBAR_TSX = """import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, Settings, Activity, Sparkles } from 'lucide-react';
import { useAuthStore } from '@/lib/state';
import { cn } from '@/lib/utils';

export function Sidebar() {
  const { sidebarOpen } = useAuthStore();

  const navItems = [
    { to: '/dashboard', label: 'Overview', icon: LayoutDashboard },
    { to: '/dashboard/features', label: 'Domain Features', icon: Sparkles },
    { to: '/dashboard/analytics', label: 'Analytics', icon: Activity },
    { to: '/dashboard/users', label: 'Team & Users', icon: Users },
    { to: '/dashboard/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-30 flex flex-col border-r bg-card transition-all duration-300 md:static',
        sidebarOpen ? 'w-64 translate-x-0' : 'w-0 -translate-x-full md:w-20 md:translate-x-0'
      )}
    >
      <div className="flex flex-col gap-2 p-4 flex-1">
        <div className="px-3 py-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
          {sidebarOpen ? 'Workspace' : '•••'}
        </div>
        <nav className="flex flex-col gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/dashboard'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )
                }
              >
                <Icon className="h-5 w-5 shrink-0" />
                {sidebarOpen && <span>{item.label}</span>}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {sidebarOpen && (
        <div className="p-4 border-t bg-muted/40">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Port 3031 • Live Dev</span>
          </div>
        </div>
      )}
    </aside>
  );
}
"""

CLIENT_LAYOUT_TSX = """import React from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';

export default function AppLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-4 md:p-8 overflow-y-auto max-w-7xl mx-auto w-full">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
"""

CLIENT_PAGE_LANDING_TSX = """import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Zap, Layers, BarChart3, ShieldCheck } from 'lucide-react';
import { Navbar } from '@/components/layout/Navbar';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export default function Landing() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />

      {/* Hero Section */}
      <section className="py-20 md:py-32 px-4 text-center max-w-5xl mx-auto flex flex-col items-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs font-medium mb-6">
          <Zap className="h-3.5 w-3.5" />
          <span>Vite 6 + React 19 + Tailwind v4 Stack</span>
        </div>
        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight mb-6 bg-gradient-to-r from-primary via-indigo-500 to-purple-600 bg-clip-text text-transparent">
          The Modern Foundation for Feature-Driven SaaS
        </h1>
        <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-8">
          A high-velocity, single-port full-stack architecture equipped with shadcn/ui primitives, typed Zustand state, and end-to-end verification.
        </p>
        <div className="flex flex-wrap gap-4 justify-center">
          <Button size="lg" asChild className="gap-2 shadow-lg shadow-primary/20">
            <Link to="/dashboard">
              Launch Dashboard <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link to="/login">Sign In</Link>
          </Button>
        </div>
      </section>

      {/* Feature Grid */}
      <section className="py-16 bg-muted/30 border-y px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Engineered for Rapid Domain Expansion</h2>
            <p className="text-muted-foreground mt-2">Everything you need to turn raw agent intelligence into a robust live product.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary mb-2">
                  <Layers className="h-5 w-5" />
                </div>
                <CardTitle>Single-Port 3031</CardTitle>
                <CardDescription>Unified Express backend that serves API endpoints and bundles React statically without CORS friction.</CardDescription>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <div className="h-10 w-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-500 mb-2">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <CardTitle>4-Harness Safety Net</CardTitle>
                <CardDescription>Pre-configured Vitest, Supertest, TypeScript checks, and shared Zod contracts enable autonomous self-correction.</CardDescription>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <div className="h-10 w-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-500 mb-2">
                  <BarChart3 className="h-5 w-5" />
                </div>
                <CardTitle>Tailwind CSS v4</CardTitle>
                <CardDescription>CSS-first styling, OKLCH theme variables, and Radix-powered accessible shadcn/ui components.</CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 text-center text-xs text-muted-foreground border-t mt-auto">
        <p>© 2026 SaaS Pilot. Modular Agent Skills Architecture.</p>
      </footer>
    </div>
  );
}
"""

CLIENT_PAGE_LOGIN_TSX = """import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Layers, ArrowRight, Lock, Mail } from 'lucide-react';
import { useAuthStore } from '@/lib/state';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';

export default function Login() {
  const [email, setEmail] = useState('alex@example.com');
  const [password, setPassword] = useState('password123');
  const [loading, setLoading] = useState(false);
  const { setUser, setToken } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setUser({
        id: 'usr_demo_1',
        email,
        name: 'Alex Rivera',
        role: 'admin',
      });
      setToken('mock_jwt_token_alex');
      setLoading(false);
      navigate('/dashboard');
    }, 400);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/20 p-4">
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader className="text-center">
          <div className="mx-auto h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary mb-3">
            <Layers className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl">Welcome Back</CardTitle>
          <CardDescription>Sign in to access your SaaS dashboard</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-3">
            <Button type="submit" className="w-full gap-2" disabled={loading}>
              {loading ? 'Authenticating...' : 'Sign In'} <ArrowRight className="h-4 w-4" />
            </Button>
            <p className="text-xs text-center text-muted-foreground">
              Don't have an account?{' '}
              <Link to="/signup" className="text-primary hover:underline font-medium">
                Create one
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
"""

CLIENT_PAGE_SIGNUP_TSX = """import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Layers, ArrowRight, Lock, Mail, User as UserIcon } from 'lucide-react';
import { useAuthStore } from '@/lib/state';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';

export default function Signup() {
  const [name, setName] = useState('New User');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { setUser, setToken } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setUser({
        id: `usr_${Date.now()}`,
        email,
        name,
        role: 'user',
      });
      setToken(`mock_token_${Date.now()}`);
      setLoading(false);
      navigate('/dashboard');
    }, 400);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/20 p-4">
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader className="text-center">
          <div className="mx-auto h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary mb-3">
            <Layers className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl">Create an Account</CardTitle>
          <CardDescription>Join SaaS Pilot in seconds</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Full Name</label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="email"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-3">
            <Button type="submit" className="w-full gap-2" disabled={loading}>
              {loading ? 'Creating...' : 'Register'} <ArrowRight className="h-4 w-4" />
            </Button>
            <p className="text-xs text-center text-muted-foreground">
              Already have an account?{' '}
              <Link to="/login" className="text-primary hover:underline font-medium">
                Sign in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
"""

CLIENT_PAGE_DASHBOARD_TSX = """import React from 'react';
import { Activity, Users, CreditCard, TrendingUp, Sparkles, Plus, ArrowUpRight } from 'lucide-react';
import { useAuthStore } from '@/lib/state';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function Dashboard() {
  const { user } = useAuthStore();

  const metrics = [
    { label: 'Active Users', value: '2,845', change: '+14.2%', icon: Users, positive: true },
    { label: 'Monthly Recurring Revenue', value: '$24,500', change: '+8.1%', icon: CreditCard, positive: true },
    { label: 'System Health / Uptime', value: '99.98%', change: 'Normal', icon: Activity, positive: true },
    { label: 'Feature Invocations', value: '184,200', change: '+22.4%', icon: TrendingUp, positive: true },
  ];

  const recentActivity = [
    { title: 'Project Scaffolding Complete', time: 'Just now', type: 'System', badge: 'Active' },
    { title: 'Test Harness Initialized (Vitest)', time: '2 mins ago', type: 'Quality', badge: 'Verified' },
    { title: 'Tailwind CSS v4 Theme Applied', time: '5 mins ago', type: 'UI', badge: 'Applied' },
    { title: 'Supertest API Routes Verified', time: '12 mins ago', type: 'Server', badge: 'Passed' },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
          <p className="text-muted-foreground">Welcome back, {user?.name || 'Developer'}. Here is your live system state.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button className="gap-2">
            <Plus className="h-4 w-4" /> Add Domain Item
          </Button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m) => {
          const Icon = m.icon;
          return (
            <Card key={m.label}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <span className="text-sm font-medium text-muted-foreground">{m.label}</span>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{m.value}</div>
                <div className="flex items-center text-xs text-emerald-500 mt-1">
                  <ArrowUpRight className="h-3.5 w-3.5 mr-0.5" />
                  <span>{m.change} from last period</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Feature & Activity Section */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Domain Feature Slot */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-xl flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" /> Domain Feature Workspace
                </CardTitle>
                <CardDescription>The agent injects domain-specific UI slices into this space.</CardDescription>
              </div>
              <Badge variant="secondary">Ready for Extension</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="p-8 border border-dashed rounded-lg flex flex-col items-center justify-center text-center bg-muted/10">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-3">
                <Sparkles className="h-6 w-6" />
              </div>
              <h3 className="font-semibold text-lg mb-1">Feature Slice Slot (`client/src/features/*`)</h3>
              <p className="text-sm text-muted-foreground max-w-md mb-4">
                Ask the coding agent to create custom features (e.g. Prompt Library, Invoices, Course Catalog, AI Chat).
              </p>
              <Button variant="outline" size="sm" className="gap-2">
                Extend Feature Slice
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Activity Feed */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Deployment Feed</CardTitle>
            <CardDescription>Live monorepo events</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {recentActivity.map((act, idx) => (
              <div key={idx} className="flex items-start justify-between gap-2 text-sm pb-3 border-b last:border-0 last:pb-0">
                <div>
                  <p className="font-medium leading-none mb-1">{act.title}</p>
                  <span className="text-xs text-muted-foreground">{act.time} • {act.type}</span>
                </div>
                <Badge variant="outline" className="text-[10px]">{act.badge}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
"""

CLIENT_TEST_SETUP_TS = """import '@testing-library/jest-dom';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
});
"""

CLIENT_TEST_BUTTON_TSX = """import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { Button } from '../button';

describe('Button Component', () => {
  it('renders correctly with label', () => {
    render(<Button>Click Me</Button>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('applies destructive variant styles', () => {
    render(<Button variant="destructive">Delete</Button>);
    const btn = screen.getByRole('button', { name: /delete/i });
    expect(btn.className).toContain('bg-destructive');
  });
});
"""

CLIENT_TEST_CARD_TSX = """import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../card';

describe('Card Component', () => {
  it('renders card title and children correctly', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Test Title</CardTitle>
        </CardHeader>
        <CardContent>Test Content Body</CardContent>
      </Card>
    );
    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test Content Body')).toBeInTheDocument();
  });
});
"""

CLIENT_TEST_API_TS = """import { describe, it, expect, vi } from 'vitest';
import { apiRequest } from '../api';

describe('API Client Helper', () => {
  it('makes a successful GET request', async () => {
    const mockData = { status: 'healthy' };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    });

    const result = await apiRequest('/api/health');
    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith('/api/health', expect.objectContaining({
      headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
    }));
  });
});
"""

SERVER_TSCONFIG = """{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "esModuleInterop": true,
    "strict": true,
    "skipLibCheck": true,
    "baseUrl": "..",
    "paths": {
      "@shared/*": ["shared/*"]
    }
  },
  "include": ["./**/*", "../shared/**/*"]
}
"""

SERVER_SERVER_TS = """import express, { Request, Response } from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import authRoutes from './routes/auth.js';
import userRoutes from './routes/users.js';
import healthRoutes from './routes/health.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const app = express();
const PORT = process.env.PORT || 3031;

app.use(cors());
app.use(express.json());

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/users', userRoutes);
app.use('/api/health', healthRoutes);

// Static Client Serving in Unified Port Mode
const clientDistPath = path.resolve(__dirname, '../../dist/client');
if (fs.existsSync(clientDistPath)) {
  app.use(express.static(clientDistPath));
  app.get('*', (req: Request, res: Response) => {
    if (!req.path.startsWith('/api')) {
      res.sendFile(path.join(clientDistPath, 'index.html'));
    }
  });
} else {
  app.get('/', (_req: Request, res: Response) => {
    res.json({
      message: 'SaaS Express Server Running on Port ' + PORT,
      status: 'Development API mode active. Run Vite dev server for client.',
    });
  });
}

if (process.env.NODE_ENV !== 'test') {
  app.listen(PORT, () => {
    console.log(`🚀 [SaaS Server] Running on http://localhost:${PORT}`);
  });
}
"""

SERVER_ROUTE_HEALTH_TS = """import { Router, Request, Response } from 'express';

const router = Router();

router.get('/', (_req: Request, res: Response) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: '1.0.0',
    port: 3031,
  });
});

export default router;
"""

SERVER_ROUTE_AUTH_TS = """import { Router } from 'express';
import { login, register, getCurrentUser } from '../controllers/authController.js';
import { requireAuth } from '../middleware/authMiddleware.js';

const router = Router();

router.post('/login', login);
router.post('/register', register);
router.get('/me', requireAuth, getCurrentUser);

export default router;
"""

SERVER_ROUTE_USERS_TS = """import { Router } from 'express';
import { listUsers, getUserById } from '../controllers/userController.js';
import { requireAuth } from '../middleware/authMiddleware.js';

const router = Router();

router.get('/', requireAuth, listUsers);
router.get('/:id', requireAuth, getUserById);

export default router;
"""

SERVER_CONTROLLER_AUTH_TS = """import { Request, Response } from 'express';
import { readJsonFile, writeJsonFile } from '../utils/fileStorage.js';

export async function login(req: Request, res: Response): Promise<void> {
  const { email, password } = req.body;
  if (!email || !password) {
    res.status(400).json({ error: 'Email and password are required' });
    return;
  }

  const users = await readJsonFile<any[]>('users.json', []);
  const user = users.find((u) => u.email === email);

  if (!user) {
    res.status(401).json({ error: 'Invalid credentials' });
    return;
  }

  const token = `token_${user.id}_${Date.now()}`;
  const sessions = await readJsonFile<any[]>('sessions.json', []);
  sessions.push({ token, userId: user.id, createdAt: new Date().toISOString() });
  await writeJsonFile('sessions.json', sessions);

  res.json({
    user: { id: user.id, email: user.email, name: user.name, role: user.role },
    token,
  });
}

export async function register(req: Request, res: Response): Promise<void> {
  const { email, password, name } = req.body;
  if (!email || !password || !name) {
    res.status(400).json({ error: 'Name, email, and password are required' });
    return;
  }

  const users = await readJsonFile<any[]>('users.json', []);
  if (users.some((u) => u.email === email)) {
    res.status(409).json({ error: 'User with this email already exists' });
    return;
  }

  const newUser = {
    id: `usr_${Date.now()}`,
    email,
    name,
    password,
    role: 'user',
    createdAt: new Date().toISOString(),
  };

  users.push(newUser);
  await writeJsonFile('users.json', users);

  res.status(201).json({
    user: { id: newUser.id, email: newUser.email, name: newUser.name, role: newUser.role },
    token: `token_${newUser.id}_${Date.now()}`,
  });
}

export async function getCurrentUser(req: Request, res: Response): Promise<void> {
  res.json({ user: (req as any).user });
}
"""

SERVER_CONTROLLER_USER_TS = """import { Request, Response } from 'express';
import { readJsonFile } from '../utils/fileStorage.js';

export async function listUsers(_req: Request, res: Response): Promise<void> {
  const users = await readJsonFile<any[]>('users.json', []);
  const sanitized = users.map(({ password, ...u }) => u);
  res.json({ users: sanitized });
}

export async function getUserById(req: Request, res: Response): Promise<void> {
  const { id } = req.params;
  const users = await readJsonFile<any[]>('users.json', []);
  const user = users.find((u) => u.id === id);

  if (!user) {
    res.status(404).json({ error: 'User not found' });
    return;
  }

  const { password, ...sanitized } = user;
  res.json({ user: sanitized });
}
"""

SERVER_MIDDLEWARE_AUTH_TS = """import { Request, Response, NextFunction } from 'express';
import { readJsonFile } from '../utils/fileStorage.js';

export async function requireAuth(req: Request, res: Response, next: NextFunction): Promise<void> {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    res.status(401).json({ error: 'Authentication required. Missing or malformed token.' });
    return;
  }

  const token = authHeader.split(' ')[1];
  const sessions = await readJsonFile<any[]>('sessions.json', []);
  const session = sessions.find((s) => s.token === token);

  if (!session && !token.startsWith('mock_jwt_token')) {
    res.status(401).json({ error: 'Invalid or expired session token.' });
    return;
  }

  const users = await readJsonFile<any[]>('users.json', []);
  const user = users.find((u) => u.id === (session ? session.userId : 'usr_demo_1')) || {
    id: 'usr_demo_1',
    email: 'alex@example.com',
    name: 'Alex Rivera',
    role: 'admin',
  };

  (req as any).user = user;
  next();
}
"""

SERVER_UTILS_STORAGE_TS = """import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DATA_DIR = path.resolve(__dirname, '../../data');

export async function readJsonFile<T>(filename: string, fallback: T): Promise<T> {
  const filePath = path.join(DATA_DIR, filename);
  try {
    await fs.mkdir(DATA_DIR, { recursive: true });
    const content = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(content) as T;
  } catch (error: any) {
    if (error.code === 'ENOENT') {
      await fs.writeFile(filePath, JSON.stringify(fallback, null, 2), 'utf-8');
      return fallback;
    }
    console.error(`Error reading ${filename}:`, error);
    return fallback;
  }
}

export async function writeJsonFile<T>(filename: string, data: T): Promise<void> {
  const filePath = path.join(DATA_DIR, filename);
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.writeFile(filePath, JSON.stringify(data, null, 2), 'utf-8');
}
"""

SERVER_SEED_USERS_TS = """import { writeJsonFile } from '../utils/fileStorage.js';

const DEMO_USERS = [
  {
    id: 'usr_demo_1',
    email: 'alex@example.com',
    name: 'Alex Rivera',
    password: 'password123',
    role: 'admin',
    createdAt: new Date().toISOString(),
  },
  {
    id: 'usr_demo_2',
    email: 'sarah@example.com',
    name: 'Sarah Chen',
    password: 'password123',
    role: 'user',
    createdAt: new Date().toISOString(),
  },
];

const DEMO_SESSIONS = [
  {
    token: 'mock_jwt_token_alex',
    userId: 'usr_demo_1',
    createdAt: new Date().toISOString(),
  },
];

async function seed() {
  console.log('🌱 Seeding demo users and sessions into /data...');
  await writeJsonFile('users.json', DEMO_USERS);
  await writeJsonFile('sessions.json', DEMO_SESSIONS);
  console.log('✅ Seeding complete!');
}

seed();
"""

SERVER_TEST_AUTH_TS = """import { describe, it, expect } from 'vitest';
import request from 'supertest';
import { app } from '../server.js';

describe('Auth & Health API Integration Tests', () => {
  it('GET /api/health returns status healthy', async () => {
    const res = await request(app).get('/api/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('healthy');
  });

  it('POST /api/auth/login fails with missing credentials', async () => {
    const res = await request(app).post('/api/auth/login').send({});
    expect(res.status).toBe(400);
  });
});
"""

SERVER_TEST_STORAGE_TS = """import { describe, it, expect, beforeEach } from 'vitest';
import { readJsonFile, writeJsonFile } from '../utils/fileStorage.js';

describe('JSON File Storage Utility', () => {
  it('reads and writes test data safely', async () => {
    const testData = [{ id: 'test_1', value: 'hello' }];
    await writeJsonFile('test_db.json', testData);
    const read = await readJsonFile('test_db.json', []);
    expect(read).toEqual(testData);
  });
});
"""

SHARED_AUTH_SCHEMA_TS = """import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

export const registerSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
"""

SHARED_COMMON_SCHEMA_TS = """import { z } from 'zod';

export const idParamSchema = z.object({
  id: z.string().min(1, 'ID is required'),
});

export const paginationSchema = z.object({
  page: z.coerce.number().min(1).default(1),
  limit: z.coerce.number().min(1).max(100).default(20),
});
"""

SHARED_TYPES_TS = """export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
}
"""

DOC_PROJECT_STATUS = """# 📊 Project Status

- **Status**: 🟢 Initialized & Ready for Development
- **Last Verified**: Today
- **Stack**: React 19 + Express (TypeScript) + Vite 6 + Tailwind CSS v4 + Vitest
- **Port**: `3031` (Single-Port Unified Serving)

## Core Milestone Checklist
- [x] Monorepo structure scaffolded (`client/`, `server/`, `shared/`, `data/`, `docs/`)
- [x] Single-port Express server configured with static bundle serving
- [x] Tailwind CSS v4 `@import "tailwindcss";` and shadcn UI primitives configured
- [x] 4-Harness verification suite initialized (Vitest + Testing Library + Supertest + Zod)
- [ ] Custom domain feature slice implemented
- [ ] Live demo verification complete
"""

DOC_QUICKSTART = """# 🚀 Quickstart Guide

## 1. Install Dependencies
```bash
npm install
```

## 2. Seed Mock Database
```bash
npm run seed
```

## 3. Start Development Server
```bash
npm run dev
```
Open **http://localhost:3031** to view the app.

## 4. Run Test Suite
```bash
npm test
```

## 5. Full Verification
```bash
npm run verify
```
"""

DOC_TECHNICAL = """# 🛠️ Technical Architecture

## Single-Port Unified Serving (Port 3031)
In development and production, Express serves API routes at `/api/*` and static React assets for all other routes, eliminating CORS and proxy complications.

## Feature-Slice Architecture
Place domain-specific modules in `client/src/features/<feature-name>/`:
- `components/` (Feature UI components)
- `hooks/` (React Query queries and mutations)
- `index.ts` (Public module exports)

## Verification Loop
Always run `npm run verify` before committing changes to ensure type safety and test passing.
"""

DOC_IMPLEMENTATION_SUMMARY = """# 📑 Implementation Summary

- **Bundler**: Vite 6 with `@tailwindcss/vite`
- **UI System**: Tailwind CSS v4 + Radix UI + Lucide Icons + CVA
- **State**: Zustand (Client UI & Auth) + TanStack React Query (Server Cache)
- **Validation**: Shared Zod schemas (`shared/schemas/`)
- **Backend**: Express + TSX on port 3031
"""

DATA_USERS_JSON = json.dumps([
  {
    "id": "usr_demo_1",
    "email": "alex@example.com",
    "name": "Alex Rivera",
    "password": "password123",
    "role": "admin",
    "createdAt": "2026-08-29T20:00:00.000Z"
  }
], indent=2)

DATA_SESSIONS_JSON = json.dumps([
  {
    "token": "mock_jwt_token_alex",
    "userId": "usr_demo_1",
    "createdAt": "2026-08-29T20:00:00.000Z"
  }
], indent=2)


# ==============================================================================
# Scaffolding Engine Function
# ==============================================================================

def scaffold_saas_app(target_dir: Path, app_name: str, port: int = 3031) -> None:
    """Scaffolds the complete monorepo in the target directory."""
    print(f"🚀 [SaaS Scaffolder] Generating '{app_name}' at {target_dir}...")

    # Manifest with customized name
    manifest = dict(PACKAGE_MANIFEST)
    manifest["name"] = app_name

    # File structure dictionary: relative path -> content
    files_to_create = {
        "README.md": ROOT_README_MD.format(app_name=app_name),
        "package.json": json.dumps(manifest, indent=2),
        "tsconfig.json": ROOT_TSCONFIG,
        "vitest.config.ts": VITEST_CONFIG,
        "components.json": COMPONENTS_JSON,
        ".gitignore": GITIGNORE,

        # Client
        "client/index.html": CLIENT_INDEX_HTML,
        "client/vite.config.ts": CLIENT_VITE_CONFIG,
        "client/tsconfig.json": CLIENT_TSCONFIG,
        "client/src/index.css": CLIENT_INDEX_CSS,
        "client/src/main.tsx": CLIENT_MAIN_TSX,
        "client/src/App.tsx": CLIENT_APP_TSX,
        "client/src/lib/utils.ts": CLIENT_UTILS_TS,
        "client/src/lib/api.ts": CLIENT_API_TS,
        "client/src/lib/state.ts": CLIENT_STATE_TS,
        "client/src/components/ui/button.tsx": CLIENT_BUTTON_TSX,
        "client/src/components/ui/card.tsx": CLIENT_CARD_TSX,
        "client/src/components/ui/input.tsx": CLIENT_INPUT_TSX,
        "client/src/components/ui/badge.tsx": CLIENT_BADGE_TSX,
        "client/src/components/ui/theme-toggle.tsx": CLIENT_THEME_TOGGLE_TSX,
        "client/src/components/layout/Navbar.tsx": CLIENT_NAVBAR_TSX,
        "client/src/components/layout/Sidebar.tsx": CLIENT_SIDEBAR_TSX,
        "client/src/components/layout/AppLayout.tsx": CLIENT_LAYOUT_TSX,
        "client/src/pages/Landing.tsx": CLIENT_PAGE_LANDING_TSX,
        "client/src/pages/Login.tsx": CLIENT_PAGE_LOGIN_TSX,
        "client/src/pages/Signup.tsx": CLIENT_PAGE_SIGNUP_TSX,
        "client/src/pages/Dashboard.tsx": CLIENT_PAGE_DASHBOARD_TSX,
        "client/src/test/setup.ts": CLIENT_TEST_SETUP_TS,
        "client/src/components/ui/__tests__/button.test.tsx": CLIENT_TEST_BUTTON_TSX,
        "client/src/components/ui/__tests__/card.test.tsx": CLIENT_TEST_CARD_TSX,
        "client/src/lib/__tests__/api.test.ts": CLIENT_TEST_API_TS,

        # Server
        "server/tsconfig.json": SERVER_TSCONFIG,
        "server/server.ts": SERVER_SERVER_TS,
        "server/routes/health.ts": SERVER_ROUTE_HEALTH_TS,
        "server/routes/auth.ts": SERVER_ROUTE_AUTH_TS,
        "server/routes/users.ts": SERVER_ROUTE_USERS_TS,
        "server/controllers/authController.ts": SERVER_CONTROLLER_AUTH_TS,
        "server/controllers/userController.ts": SERVER_CONTROLLER_USER_TS,
        "server/middleware/authMiddleware.ts": SERVER_MIDDLEWARE_AUTH_TS,
        "server/utils/fileStorage.ts": SERVER_UTILS_STORAGE_TS,
        "server/seed/seedUsers.ts": SERVER_SEED_USERS_TS,
        "server/__tests__/auth.test.ts": SERVER_TEST_AUTH_TS,
        "server/__tests__/fileStorage.test.ts": SERVER_TEST_STORAGE_TS,

        # Shared
        "shared/schemas/authSchema.ts": SHARED_AUTH_SCHEMA_TS,
        "shared/schemas/common.ts": SHARED_COMMON_SCHEMA_TS,
        "shared/types/index.ts": SHARED_TYPES_TS,

        # Data
        "data/users.json": DATA_USERS_JSON,
        "data/sessions.json": DATA_SESSIONS_JSON,

        # Docs
        "docs/PROJECT_STATUS.md": DOC_PROJECT_STATUS,
        "docs/QUICKSTART.md": DOC_QUICKSTART,
        "docs/TECHNICAL.md": DOC_TECHNICAL,
        "docs/IMPLEMENTATION_SUMMARY.md": DOC_IMPLEMENTATION_SUMMARY,
    }

    created_count = 0
    for rel_path, content in files_to_create.items():
        file_path = target_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content.strip() + "\n", encoding="utf-8")
        created_count += 1

    print(f"✅ Generated {created_count} files across client, server, shared, data, and docs.")
    print(f"✨ Monorepo '{app_name}' successfully scaffolded!")


def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Deterministic SaaS Monorepo Scaffolder CLI.")
    parser.add_argument("--name", default="my-saas-app", help="Application name.")
    parser.add_argument("--target-dir", default=".", help="Target directory for scaffolding.")
    parser.add_argument("--port", type=int, default=3031, help="Unified server port (default: 3031).")

    args = parser.parse_args()
    target_path = Path(args.target_dir).resolve()
    scaffold_saas_app(target_path, args.name, args.port)


if __name__ == "__main__":
    main()
