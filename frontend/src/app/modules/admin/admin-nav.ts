export interface AdminNavItem {
  label: string;
  icon: string;
  route?: string;
  soon?: boolean;
}

export const ADMIN_NAV_ITEMS: AdminNavItem[] = [
  { label: 'Tableau de bord', icon: '📊', route: '/dashboard' },
  { label: 'Patients', icon: '👥', soon: true },
  { label: 'Facturation', icon: '📄', route: '/facturation' },
  { label: 'Paiements', icon: '💳', soon: true },
  { label: 'Pharmacie', icon: '💊', route: '/pharmacie' },
  { label: 'Laboratoire', icon: '🔬', route: '/laboratoire' },
  { label: 'Hospitalisation', icon: '🏥', route: '/hospitalisation' },
  { label: 'Assurances', icon: '🛡️', route: '/assurances' },
  { label: 'Avantages Patients', icon: '🎁', soon: true },
  { label: 'Rapports', icon: '📈', route: '/rapports' },
  { label: 'Audit Log', icon: '📋', route: '/audit' },
  { label: 'Utilisateurs', icon: '👤', soon: true },
  { label: 'Paramètres', icon: '⚙️', soon: true },
];
