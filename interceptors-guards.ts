/**
 * jwt.interceptor.ts
 *
 * Attaches the JWT access token to every outgoing API request.
 * On 401, attempts a silent token refresh and retries.
 */
import { Injectable }          from '@angular/core';
import {
  HttpEvent, HttpHandler, HttpInterceptor,
  HttpRequest, HttpErrorResponse,
}                              from '@angular/common/http';
import { Observable, throwError, BehaviorSubject } from 'rxjs';
import { catchError, filter, switchMap, take }      from 'rxjs/operators';
import { HttpClient }          from '@angular/common/http';
import { environment }         from '../../../environments/environment';

@Injectable()
export class JwtInterceptor implements HttpInterceptor {

  private refreshing = false;
  private refreshToken$ = new BehaviorSubject<string | null>(null);

  constructor(private http: HttpClient) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const token = localStorage.getItem('lms_access');
    const authReq = token ? this.addToken(req, token) : req;

    return next.handle(authReq).pipe(
      catchError((err: HttpErrorResponse) => {
        if (err.status === 401 && !req.url.includes('/auth/token/')) {
          return this.handle401(req, next);
        }
        return throwError(() => err);
      }),
    );
  }

  private addToken(req: HttpRequest<any>, token: string) {
    return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
  }

  private handle401(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (this.refreshing) {
      return this.refreshToken$.pipe(
        filter(t => !!t),
        take(1),
        switchMap(t => next.handle(this.addToken(req, t!))),
      );
    }

    this.refreshing = true;
    this.refreshToken$.next(null);

    const refresh = localStorage.getItem('lms_refresh');
    if (!refresh) {
      this.refreshing = false;
      localStorage.clear();
      return throwError(() => new Error('No refresh token'));
    }

    return this.http.post<{ access: string }>(
      `${environment.apiUrl}/auth/token/refresh/`, { refresh }
    ).pipe(
      switchMap(({ access }) => {
        localStorage.setItem('lms_access', access);
        this.refreshToken$.next(access);
        this.refreshing = false;
        return next.handle(this.addToken(req, access));
      }),
      catchError(err => {
        this.refreshing = false;
        localStorage.clear();
        return throwError(() => err);
      }),
    );
  }
}


// ─────────────────────────────────────────────────────────────────────────────

/**
 * auth.guard.ts
 * Blocks unauthenticated access; redirects to /auth/login.
 */
import { inject }              from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService }         from '../services/auth.service';

export const AuthGuard: CanActivateFn = (_route, _state) => {
  const auth   = inject(AuthService);
  const router = inject(Router);
  if (auth.isLoggedIn) return true;
  return router.createUrlTree(['/auth/login']);
};


// ─────────────────────────────────────────────────────────────────────────────

/**
 * instructor.guard.ts
 * Blocks non-instructor access to the instructor dashboard.
 */
export const InstructorGuard: CanActivateFn = (_route, _state) => {
  const auth   = inject(AuthService);
  const router = inject(Router);
  const user   = auth.currentUser;
  if (user?.role === 'instructor' || user?.role === 'admin') return true;
  return router.createUrlTree(['/']);
};


// ─────────────────────────────────────────────────────────────────────────────

/**
 * enrollment.guard.ts
 * Ensures the current user is enrolled in the course before entering Learn area.
 */
import { map, catchError, of } from 'rxjs';
import { CourseService }       from '../services/course.service';
import { CanActivateFn, ActivatedRouteSnapshot } from '@angular/router';

export const EnrollmentGuard: CanActivateFn = (route: ActivatedRouteSnapshot, _state) => {
  const courseService = inject(CourseService);
  const router        = inject(Router);
  const slug          = route.paramMap.get('courseSlug') ?? '';

  return courseService.getCourse(slug).pipe(
    map(course => {
      if (course.is_enrolled) return true;
      return router.createUrlTree(['/courses', slug]);
    }),
    catchError(() => of(router.createUrlTree(['/courses']))),
  );
};
