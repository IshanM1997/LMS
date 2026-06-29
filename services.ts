/**
 * auth.service.ts
 */
import { Injectable }      from '@angular/core';
import { HttpClient }      from '@angular/common/http';
import { BehaviorSubject, tap, Observable } from 'rxjs';
import { Router }          from '@angular/router';
import { environment }     from '../../../environments/environment';

export interface AuthTokens { access: string; refresh: string; }
export interface LoginPayload { email: string; password: string; }

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly API = `${environment.apiUrl}/auth`;
  private _user$ = new BehaviorSubject<any>(null);

  constructor(private http: HttpClient, private router: Router) {
    const raw = localStorage.getItem('lms_user');
    if (raw) this._user$.next(JSON.parse(raw));
  }

  get user$() { return this._user$.asObservable(); }
  get currentUser() { return this._user$.value; }
  get isLoggedIn() { return !!this.currentUser; }

  login(payload: LoginPayload): Observable<AuthTokens> {
    return this.http.post<AuthTokens>(`${this.API}/token/`, payload).pipe(
      tap(tokens => {
        localStorage.setItem('lms_access', tokens.access);
        localStorage.setItem('lms_refresh', tokens.refresh);
        this.loadMe().subscribe();
      }),
    );
  }

  loadMe(): Observable<any> {
    return this.http.get(`${environment.apiUrl}/users/me/`).pipe(
      tap(user => {
        this._user$.next(user);
        localStorage.setItem('lms_user', JSON.stringify(user));
      }),
    );
  }

  logout(): void {
    localStorage.removeItem('lms_access');
    localStorage.removeItem('lms_refresh');
    localStorage.removeItem('lms_user');
    this._user$.next(null);
    this.router.navigate(['/auth/login']);
  }

  register(payload: any): Observable<any> {
    return this.http.post(`${environment.apiUrl}/users/register/`, payload);
  }
}


// ─────────────────────────────────────────────────────────────────────────────

/**
 * course.service.ts
 */
import { Course, CourseList } from '../models/course.model';
import { PaginatedResponse }  from '../models/pagination.model';

@Injectable({ providedIn: 'root' })
export class CourseService {
  private readonly API = `${environment.apiUrl}/courses`;

  constructor(private http: HttpClient) {}

  getCourses(params: Record<string, any> = {}): Observable<PaginatedResponse<CourseList>> {
    return this.http.get<PaginatedResponse<CourseList>>(`${this.API}/`, { params });
  }

  getCourse(slug: string): Observable<Course> {
    return this.http.get<Course>(`${this.API}/${slug}/`);
  }

  enroll(slug: string): Observable<any> {
    return this.http.post(`${this.API}/${slug}/enroll/`, {});
  }

  getMyEnrollments(): Observable<any[]> {
    return this.http.get<any[]>(`${this.API}/enrollments/my/`);
  }

  addReview(slug: string, payload: { rating: number; title: string; body: string }): Observable<any> {
    return this.http.post(`${this.API}/${slug}/reviews/`, payload);
  }
}


// ─────────────────────────────────────────────────────────────────────────────

/**
 * lesson.service.ts
 */
import { LessonDetail } from '../models/lesson.model';

@Injectable({ providedIn: 'root' })
export class LessonService {
  private readonly API = `${environment.apiUrl}/lessons`;

  constructor(private http: HttpClient) {}

  getLessonDetail(courseSlug: string, lessonId: number): Observable<LessonDetail> {
    return this.http.get<LessonDetail>(`${this.API}/${lessonId}/`);
  }

  /**
   * Request a pre-signed S3 PUT URL so the browser can upload a video
   * directly to S3 without routing through Django.
   */
  requestUploadUrl(lessonId: number): Observable<{ presigned_upload_url: string; s3_key: string }> {
    return this.http.post<any>(`${this.API}/${lessonId}/request-upload-url/`, {});
  }

  /**
   * Upload raw video bytes to S3 using the pre-signed PUT URL.
   * Content-Type must match what was used to generate the URL.
   */
  uploadVideoToS3(presignedUrl: string, file: File): Observable<any> {
    return this.http.put(presignedUrl, file, {
      headers: { 'Content-Type': file.type },
      reportProgress: true,
      observe: 'events',
    });
  }

  confirmUpload(lessonId: number): Observable<any> {
    return this.http.post(`${this.API}/${lessonId}/confirm-upload/`, {});
  }
}


// ─────────────────────────────────────────────────────────────────────────────

/**
 * progress.service.ts
 */
import { LessonProgress, CourseProgress } from '../models/progress.model';

@Injectable({ providedIn: 'root' })
export class ProgressService {
  private readonly API = `${environment.apiUrl}/progress`;

  constructor(private http: HttpClient) {}

  getLessonProgress(courseSlug: string): Observable<LessonProgress[]> {
    return this.http.get<LessonProgress[]>(`${this.API}/courses/${courseSlug}/lessons/`);
  }

  updateLessonProgress(lessonId: number, patch: Partial<LessonProgress>): Observable<LessonProgress> {
    return this.http.patch<LessonProgress>(`${this.API}/lessons/${lessonId}/`, patch);
  }

  getCourseProgress(): Observable<CourseProgress[]> {
    return this.http.get<CourseProgress[]>(`${this.API}/courses/`);
  }
}


// ─────────────────────────────────────────────────────────────────────────────

/**
 * quiz.service.ts
 */
import { Quiz, QuizAttempt } from '../models/quiz.model';

@Injectable({ providedIn: 'root' })
export class QuizService {
  private readonly API = `${environment.apiUrl}/quizzes`;

  constructor(private http: HttpClient) {}

  getQuiz(courseSlug: string, quizId: number): Observable<Quiz> {
    return this.http.get<Quiz>(`${this.API}/${quizId}/`);
  }

  startAttempt(quizId: number): Observable<QuizAttempt> {
    return this.http.post<QuizAttempt>(`${this.API}/${quizId}/start/`, {});
  }

  submitAttempt(quizId: number, attemptId: string, responses: any[]): Observable<QuizAttempt> {
    return this.http.post<QuizAttempt>(`${this.API}/${quizId}/submit/${attemptId}/`, { responses });
  }

  getMyAttempts(quizId: number): Observable<QuizAttempt[]> {
    return this.http.get<QuizAttempt[]>(`${this.API}/${quizId}/my-attempts/`);
  }
}


// ─────────────────────────────────────────────────────────────────────────────

/**
 * certificate.service.ts
 */
import { Certificate } from '../models/certificate.model';

@Injectable({ providedIn: 'root' })
export class CertificateService {
  private readonly API = `${environment.apiUrl}/certificates`;

  constructor(private http: HttpClient) {}

  getMyCertificates(): Observable<Certificate[]> {
    return this.http.get<Certificate[]>(`${this.API}/`);
  }

  getDownloadUrl(certId: string): Observable<{ download_url: string }> {
    return this.http.get<{ download_url: string }>(`${this.API}/${certId}/download/`);
  }

  verify(certId: string): Observable<Certificate> {
    return this.http.get<Certificate>(`${this.API}/${certId}/verify/`);
  }
}
