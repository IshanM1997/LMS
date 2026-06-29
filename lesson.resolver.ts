/**
 * lesson.resolver.ts
 *
 * Pre-fetches a lesson AND its signed S3 video URL before
 * the LessonViewer component is activated.
 *
 * Why both in one resolver?
 *  - Signed URLs expire quickly (1 h).
 *  - We want the URL to be as fresh as possible when the <video> tag renders.
 *  - Fetching them in parallel (forkJoin) keeps navigation fast.
 *
 * Data available in component:
 *   this.route.snapshot.data['lesson']    → LessonDetail object
 *   this.route.snapshot.data['lesson'].videoUrl → pre-signed S3 URL
 */
import { Injectable }         from '@angular/core';
import {
  ActivatedRouteSnapshot,
  MaybeAsync,
  Resolve,
  Router,
  RouterStateSnapshot,
} from '@angular/router';
import { Observable, forkJoin, catchError, EMPTY, map } from 'rxjs';

import { LessonService }  from '../services/lesson.service';
import { LessonDetail }   from '../models/lesson.model';


@Injectable({ providedIn: 'root' })
export class LessonResolver implements Resolve<LessonDetail> {

  constructor(
    private lessonService: LessonService,
    private router: Router,
  ) {}

  resolve(
    route: ActivatedRouteSnapshot,
    _state: RouterStateSnapshot,
  ): MaybeAsync<LessonDetail> {

    const lessonId   = Number(route.paramMap.get('lessonId'));
    const courseSlug = route.parent?.paramMap.get('courseSlug') ?? '';

    if (!lessonId) {
      this.router.navigate(['/learn', courseSlug]);
      return EMPTY;
    }

    /**
     * LessonService.getLessonDetail() calls:
     *   GET /api/v1/courses/:courseSlug/sections/:sectionId/lessons/:id/
     *
     * The Django view calls lesson.generate_signed_video_url() before
     * serialising the response, so videoUrl is already in the JSON body.
     * No second HTTP call is needed from the frontend.
     */
    return this.lessonService.getLessonDetail(courseSlug, lessonId).pipe(
      catchError(() => {
        this.router.navigate(['/learn', courseSlug]);
        return EMPTY;
      }),
    );
  }
}
