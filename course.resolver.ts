/**
 * course.resolver.ts
 *
 * Pre-fetches full course data before the route is activated.
 * Used on the Course Detail page and as a parent resolver for the Learn area.
 *
 * Pattern:
 *   Router → CourseResolver.resolve() → HTTP GET /api/v1/courses/:slug/
 *         → data stored in route snapshot → Component reads synchronously
 *
 * No loading spinner needed in the component; the Router waits for resolution.
 */
import { Injectable } from '@angular/core';
import {
  ActivatedRouteSnapshot,
  MaybeAsync,
  RedirectCommand,
  Resolve,
  Router,
  RouterStateSnapshot,
} from '@angular/router';
import { Observable, catchError, EMPTY } from 'rxjs';

import { CourseService } from '../services/course.service';
import { Course }        from '../models/course.model';


@Injectable({ providedIn: 'root' })
export class CourseResolver implements Resolve<Course> {

  constructor(
    private courseService: CourseService,
    private router: Router,
  ) {}

  resolve(
    route: ActivatedRouteSnapshot,
    _state: RouterStateSnapshot,
  ): MaybeAsync<Course | RedirectCommand> {

    const slug = route.paramMap.get('slug') ?? route.parent?.paramMap.get('courseSlug');

    if (!slug) {
      this.router.navigate(['/courses']);
      return EMPTY;
    }

    return this.courseService.getCourse(slug).pipe(
      catchError(() => {
        this.router.navigate(['/courses']);
        return EMPTY;
      }),
    );
  }
}
