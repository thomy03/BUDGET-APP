"use client";

// @ts-ignore: Next.js handles CSS imports
import "./globals.css";
// @ts-ignore: Next.js handles CSS imports  
import "./calendar-modern.css";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import MonthPicker from "../components/MonthPicker";
import { useAuth } from "../lib/auth";
import { ToastProvider } from "../components/ui";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { isAuthenticated, user, logout } = useAuth();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Ne pas afficher la navigation sur la page de login
  const isLoginPage = pathname === "/login";

  // Éviter l'hydratation mismatch
  if (!mounted) {
    return (
      <html lang="fr">
        <head>
          <title>Budget Famille</title>
          <meta name="description" content="Gestion budgétaire familiale sécurisée" />
        </head>
        <body>
          <div className="min-h-screen bg-zinc-50 flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-zinc-900"></div>
          </div>
        </body>
      </html>
    );
  }

  return (
    <html lang="fr">
      <head>
        <title>Budget Famille</title>
        <meta name="description" content="Gestion budgétaire familiale sécurisée" />
      </head>
      <body>
        {!isLoginPage && (
          <header className="bg-white border-b border-zinc-200 shadow-sm">
            <nav className="container py-4 flex items-center gap-6">
              <Link
                href="/"
                className="font-bold text-xl text-zinc-900 hover:text-zinc-700 transition-colors"
              >
                💶 Budget Famille
              </Link>
              
              {isAuthenticated && (
                <>
                  <div className="flex gap-1 text-sm">
                    <Link
                      href="/"
                      className={`btn transition-all ${pathname === "/" ? "bg-zinc-900 text-white" : ""}`}
                    >
                      Dashboard
                    </Link>
                    <Link
                      href="/transactions"
                      className={`btn transition-all ${pathname === "/transactions" ? "bg-zinc-900 text-white" : ""}`}
                    >
                      Transactions
                    </Link>
                    <Link
                      href="/upload"
                      className={`btn transition-all ${pathname === "/upload" ? "bg-zinc-900 text-white" : ""}`}
                    >
                      Import
                    </Link>
                    <Link
                      href="/settings"
                      className={`btn transition-all ${pathname === "/settings" ? "bg-zinc-900 text-white" : ""}`}
                    >
                      Paramètres
                    </Link>
                    <Link
                      href="/analytics"
                      className={`btn transition-all ${pathname === "/analytics" ? "bg-zinc-900 text-white" : ""}`}
                    >
                      Analyses
                    </Link>
                  </div>
                  
                  <div className="ml-auto flex items-center gap-4">
                    <MonthPicker />
                    
                    <div className="flex items-center gap-3 text-sm">
                      <span className="text-zinc-600">
                        👤 {user}
                      </span>
                      <button
                        onClick={() => logout()}
                        className="btn text-red-600 hover:bg-red-50 border-red-200 transition-colors"
                      >
                        Déconnexion
                      </button>
                    </div>
                  </div>
                </>
              )}
            </nav>
          </header>
        )}
        
        <main className={isLoginPage ? "" : "min-h-screen bg-zinc-50"}>
          <ToastProvider>
            {children}
          </ToastProvider>
        </main>
      </body>
    </html>
  );
}