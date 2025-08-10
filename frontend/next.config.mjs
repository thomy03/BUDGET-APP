import path from 'path';

export default { 
  reactStrictMode: true,
  output: 'standalone',
  experimental: {
    outputFileTracingRoot: path.join(process.cwd(), '.')
  },
  // Améliorer la compatibilité WSL2
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      // Réduire l'utilisation de la mémoire en mode développement sur WSL2
      config.cache = false;
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }
    return config;
  }
};