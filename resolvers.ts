/**
 * quiz.resolver.ts
 * Fetches a quiz (with questions but WITHOUT correct-answer flags)
 * before the QuizPlayer component activates.
 */
import { Injectable }  from '@angular/core';
import { ActivatedRouteSnapshot, Resolve, Router, RouterStateSnapshot } from '@angular/router';
import { Observable, catchError, EMPTY } from 'rxjs';

import { QuizService } from '../services/quiz.service';
import { Quiz }        from '../models/quiz.model';


@Injectable({ providedIn: 'root' })
export class QuizResolver implements Resolve<Quiz> {

  constructor(private quizService: QuizService, private router: Router) {}

  resolve(route: ActivatedRouteSnapshot, _state: RouterStateSnapshot): Observable<Quiz> {
    const quizId     = Number(route.paramMap.get('quizId'));
    const courseSlug = route.parent?.paramMap.get('courseSlug') ?? '';

    return this.quizService.getQuiz(courseSlug, quizId).pipe(
      catchError(() => {
        this.router.navigate(['/learn', courseSlug]);
        return EMPTY;
      }),
    );
  }
}


/**
 * progress.resolver.ts
 * Pre-fetches lesson-level progress for the current student
 * so the course player sidebar renders completed/incomplete states immediately.
 */
import { ProgressService } from '../services/progress.service';
import { LessonProgress }  from '../models/progress.model';


@Injectable({ providedIn: 'root' })
export class ProgressResolver implements Resolve<LessonProgress[]> {

  constructor(private progressService: ProgressService, private router: Router) {}

  resolve(route: ActivatedRouteSnapshot, _state: RouterStateSnapshot): Observable<LessonProgress[]> {
    const courseSlug = route.paramMap.get('courseSlug') ?? '';
    return this.progressService.getLessonProgress(courseSlug).pipe(
      catchError(() => {
        // Non-fatal — return empty so player still loads
        return [[] as LessonProgress[]];
      }),
    );
  }
}


/**
 * certificate.resolver.ts
 * Pre-fetches the authenticated user's certificates list.
 */
import { CertificateService } from '../services/certificate.service';
import { Certificate }        from '../models/certificate.model';


@Injectable({ providedIn: 'root' })
export class CertificateResolver implements Resolve<Certificate[]> {

  constructor(private certService: CertificateService) {}

  resolve(_route: ActivatedRouteSnapshot, _state: RouterStateSnapshot): Observable<Certificate[]> {
    return this.certService.getMyCertificates().pipe(catchError(() => [[] as Certificate[]]));
  }
}
