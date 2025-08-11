import { ImportMonth } from "./api";

/**
 * Détermine le mois cible optimal pour la redirection après import
 * @param months - Mois détectés dans l'import
 * @param suggestedMonth - Mois suggéré par le backend
 * @param currentMonth - Mois actuellement sélectionné dans l'app
 * @returns Le mois cible au format YYYY-MM ou null si aucun mois valide
 */
export function pickTargetMonth(
  months: ImportMonth[],
  suggestedMonth: string | null,
  currentMonth: string
): string | null {
  if (!months || months.length === 0) {
    return null;
  }

  // Si un seul mois détecté, le prendre
  if (months.length === 1) {
    return months[0]?.month || null;
  }

  // Prioriser le mois suggéré par le backend s'il existe et contient des nouvelles transactions
  if (suggestedMonth) {
    const suggested = months.find(m => m.month === suggestedMonth && m.transaction_count > 0);
    if (suggested) {
      return suggestedMonth;
    }
  }

  // Sinon, prendre le mois avec le plus de nouvelles transactions
  const monthsWithNew = months.filter(m => m?.transaction_count > 0);
  if (monthsWithNew.length === 0) {
    return months[0]?.month || null; // Fallback sur le premier mois
  }

  // Trier par nombre de nouvelles transactions (décroissant), puis par date (décroissant)
  const bestMonth = monthsWithNew.sort((a, b) => {
    if (a.transaction_count !== b.transaction_count) {
      return b.transaction_count - a.transaction_count;
    }
    return b.month.localeCompare(a.month);
  })[0];

  return bestMonth?.month || null;
}

/**
 * Convertit un mois au format YYYY-MM en texte lisible
 * @param month - Mois au format YYYY-MM
 * @returns Texte lisible ex: "Janvier 2024"
 */
export function humanizeMonth(month: string): string {
  try {
    const parts = month.split('-');
    if (parts.length < 2) return month;
    
    const [year, monthNum] = parts;
    if (!year || !monthNum) return month;
    
    const date = new Date(parseInt(year), parseInt(monthNum) - 1, 1);
    
    return date.toLocaleDateString('fr-FR', {
      month: 'long',
      year: 'numeric'
    });
  } catch {
    return month; // Fallback si le format est invalide
  }
}

/**
 * Génère un résumé de l'import pour affichage
 * @param months - Mois détectés avec métadonnées
 * @returns Résumé avec total des nouvelles transactions et texte descriptif
 */
export function generateImportSummary(months: ImportMonth[]): {
  totalNew: number;
  monthsSummary: string;
} {
  if (!months || months.length === 0) {
    return {
      totalNew: 0,
      monthsSummary: "Aucun mois détecté"
    };
  }

  const totalNew = months.reduce((sum, month) => sum + month.transaction_count, 0);

  if (months.length === 1) {
    return {
      totalNew,
      monthsSummary: humanizeMonth(months[0]?.month || '')
    };
  }

  // Trier les mois par ordre chronologique pour l'affichage
  const sortedMonths = months
    .filter(m => m.transaction_count > 0) // Seulement les mois avec nouvelles transactions
    .sort((a, b) => a.month.localeCompare(b.month));

  if (sortedMonths.length === 0) {
    return {
      totalNew: 0,
      monthsSummary: "Aucune nouvelle transaction"
    };
  }

  if (sortedMonths.length <= 3) {
    // Afficher tous les mois si 3 ou moins
    const monthsText = sortedMonths
      .map(m => `${humanizeMonth(m.month)} (${m.transaction_count})`)
      .join(', ');
    return {
      totalNew,
      monthsSummary: monthsText
    };
  }

  // Si plus de 3 mois, afficher les 2 premiers et le décompte
  const firstTwo = sortedMonths.slice(0, 2)
    .map(m => `${humanizeMonth(m.month)} (${m.transaction_count})`)
    .join(', ');
  const remaining = sortedMonths.length - 2;
  
  return {
    totalNew,
    monthsSummary: `${firstTwo} et ${remaining} autre${remaining > 1 ? 's' : ''} mois`
  };
}

/**
 * Construit l'URL de redirection vers la page des transactions
 * @param month - Mois cible au format YYYY-MM
 * @param importId - ID unique de l'import pour mise en évidence
 * @returns URL de redirection
 */
export function buildTransactionUrl(month: string, importId: string): string {
  const params = new URLSearchParams();
  params.set('month', month);
  
  if (importId) {
    params.set('importId', importId);
  }

  return `/transactions?${params.toString()}`;
}

/**
 * Formate une taille de fichier en octets vers un texte lisible
 * @param bytes - Taille en octets
 * @returns Texte formaté ex: "2.5 MB"
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Valide qu'un fichier est acceptable pour l'import
 * @param file - Fichier à valider
 * @param maxSize - Taille maximum en octets (défaut: 10MB)
 * @returns Objet avec validité et message d'erreur éventuel
 */
export function validateImportFile(file: File, maxSize: number = 10 * 1024 * 1024): {
  valid: boolean;
  error?: string;
} {
  if (!file) {
    return { valid: false, error: "Aucun fichier sélectionné" };
  }

  // Vérifier la taille
  if (file.size > maxSize) {
    return { 
      valid: false, 
      error: `Fichier trop volumineux (${formatFileSize(file.size)}). Maximum autorisé: ${formatFileSize(maxSize)}` 
    };
  }

  // Vérifier l'extension
  const allowedExtensions = ['.csv', '.xlsx', '.xls'];
  const fileName = file.name.toLowerCase();
  const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext));
  
  if (!hasValidExtension) {
    return { 
      valid: false, 
      error: `Format de fichier non supporté. Formats acceptés: ${allowedExtensions.join(', ')}` 
    };
  }

  // Vérifier le type MIME si disponible
  const allowedMimeTypes = [
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/csv'
  ];
  
  if (file.type && !allowedMimeTypes.includes(file.type)) {
    // Ne pas bloquer si le MIME type n'est pas reconnu, 
    // car certains navigateurs ne le détectent pas correctement
    console.warn('Type MIME non reconnu:', file.type);
  }

  return { valid: true };
}

/**
 * Détermine l'icône à afficher selon l'extension du fichier
 * @param filename - Nom du fichier
 * @returns Emoji représentant le type de fichier
 */
export function getFileIcon(filename: string): string {
  const ext = filename.toLowerCase().split('.').pop();
  
  switch (ext) {
    case 'csv':
      return '📊';
    case 'xlsx':
    case 'xls':
      return '📈';
    default:
      return '📄';
  }
}