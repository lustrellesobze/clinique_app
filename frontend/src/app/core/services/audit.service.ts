import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AuditLogEntry {
  id: string;
  created_at: string;
  categorie: string;
  categorie_label: string;
  titre: string;
  details_ligne: string;
  statut_label: string;
  user_id?: string | null;
  user_nom?: string | null;
  user_prenom?: string | null;
  user_role?: string | null;
  action: string;
  entity_type?: string | null;
  entity_id?: string | null;
  ip?: string | null;
}

export interface AuditLogList {
  total: number;
  date_jour?: string | null;
  entries: AuditLogEntry[];
}

export interface AuditUserOption {
  id: string;
  nom: string;
  prenom: string;
  role: string;
}

@Injectable({ providedIn: 'root' })
export class AuditService {
  private readonly api = `${environment.apiUrl.replace(/\/+$/, '')}/api/audit`;

  constructor(private http: HttpClient) {}

  listUsers(): Observable<AuditUserOption[]> {
    return this.http.get<AuditUserOption[]>(`${this.api}/users`);
  }

  listLogs(params: {
    user_id?: string;
    categorie?: string;
    recherche?: string;
    date_debut?: string;
    date_fin?: string;
    limit?: number;
  }): Observable<AuditLogList> {
    let p = new HttpParams();
    if (params.user_id) p = p.set('user_id', params.user_id);
    if (params.categorie && params.categorie !== 'toutes') {
      p = p.set('categorie', params.categorie);
    }
    if (params.recherche?.trim()) p = p.set('recherche', params.recherche.trim());
    if (params.date_debut) p = p.set('date_debut', params.date_debut);
    if (params.date_fin) p = p.set('date_fin', params.date_fin);
    if (params.limit) p = p.set('limit', String(params.limit));
    return this.http.get<AuditLogList>(this.api, { params: p });
  }
}
