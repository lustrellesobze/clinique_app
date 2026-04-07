export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserInfo;
}

export interface UserInfo {
  id: string;
  nom: string;
  prenom: string;
  email: string;
  role: UserRole;
  service: string | null;
}

export type UserRole =
  | 'infirmiere_accueil'
  | 'caissier_central'
  | 'medecin'
  | 'caissier_pharmacie'
  | 'caissier_labo'
  | 'caissier_imagerie'
  | 'comptable'
  | 'resp_hospit'
  | 'gestionnaire_assurance'
  | 'admin';

// Mapping rôle → route de redirection après login
export const ROLE_ROUTES: Record<UserRole, string> = {
  infirmiere_accueil: '/accueil',
  caissier_central: '/caisse',
  medecin: '/medecin',
  caissier_pharmacie: '/pharmacie',
  caissier_labo: '/laboratoire',
  caissier_imagerie: '/imagerie',
  comptable: '/assurances',
  resp_hospit: '/hospitalisation',
  gestionnaire_assurance: '/assurances',
  admin: '/admin',
};

// Labels lisibles pour afficher le rôle dans l'UI
export const ROLE_LABELS: Record<UserRole, string> = {
  infirmiere_accueil: 'Infirmière d\'accueil',
  caissier_central: 'Caissier(ère) central(e)',
  medecin: 'Médecin',
  caissier_pharmacie: 'Caissier(ère) Pharmacie',
  caissier_labo: 'Caissier(ère) Laboratoire',
  caissier_imagerie: 'Caissier(ère) Imagerie',
  comptable: 'Comptable',
  resp_hospit: 'Responsable Hospitalisation',
  gestionnaire_assurance: 'Gestionnaire Assurances',
  admin: 'Administrateur',
};
