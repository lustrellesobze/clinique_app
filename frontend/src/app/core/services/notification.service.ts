import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, interval } from 'rxjs';
import { tap, switchMap, startWith } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface Notification {
  id: string;
  user_id: string;
  type_notification: string;
  titre: string;
  message: string;
  est_lue: boolean;
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private apiUrl = `${environment.apiUrl}/notifications`;
  private unreadCountSubject = new BehaviorSubject<number>(0);
  public unreadCount$ = this.unreadCountSubject.asObservable();

  constructor(private http: HttpClient) {
    // Polling toutes les 30 secondes pour mettre à jour le compteur
    interval(30000)
      .pipe(
        startWith(0),
        switchMap(() => this.getUnreadCount())
      )
      .subscribe();
  }

  getNotifications(unreadOnly: boolean = false): Observable<Notification[]> {
    return this.http.get<Notification[]>(`${this.apiUrl}/?unread_only=${unreadOnly}`);
  }

  getUnreadCount(): Observable<{ count: number }> {
    return this.http.get<{ count: number }>(`${this.apiUrl}/unread-count`).pipe(
      tap(response => this.unreadCountSubject.next(response.count))
    );
  }

  markAsRead(notificationId: string): Observable<Notification> {
    return this.http.put<Notification>(`${this.apiUrl}/${notificationId}/read`, {}).pipe(
      tap(() => {
        const currentCount = this.unreadCountSubject.value;
        this.unreadCountSubject.next(Math.max(0, currentCount - 1));
      })
    );
  }

  markAllAsRead(): Observable<any> {
    return this.http.put(`${this.apiUrl}/mark-all-read`, {}).pipe(
      tap(() => this.unreadCountSubject.next(0))
    );
  }

  deleteNotification(notificationId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${notificationId}`);
  }

  refreshUnreadCount(): void {
    this.getUnreadCount().subscribe();
  }
}
