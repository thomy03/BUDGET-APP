import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Vérifier si c'est la page de login
  if (request.nextUrl.pathname === '/login') {
    return NextResponse.next();
  }

  // Pour les routes protégées, on laisse la gestion côté client
  // car le token est stocké en localStorage (non accessible côté serveur)
  // La protection réelle se fait dans le AuthService et les composants
  
  return NextResponse.next();
}

// Configuration des routes protégées
export const config = {
  matcher: [
    /*
     * Protège toutes les routes sauf:
     * - /login
     * - /api (si API routes)
     * - /_next (Next.js internals)
     * - /favicon.ico
     */
    '/((?!login|api|_next/static|_next/image|favicon.ico).*)',
  ],
};