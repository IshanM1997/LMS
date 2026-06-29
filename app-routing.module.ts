/**
 * app-routing.module.ts
 *
 * Angular route configuration with Resolvers to pre-fetch course data
 * before the component activates — eliminating loading flicker.
 *
 * Resolvers used:
 *  - CourseResolver      : fetches full course detail (title, sections, etc.)
 *  - LessonResolver      : fetches lesson + signed video URL
 *  - QuizResolver        : fetches quiz with questions
 *  - ProgressResolver    : fetches student progress for a course
 *  - CertificateResolver : fetches certificates for the current user
 */
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { AuthGuard }        from './core/guards/auth.guard';
import { InstructorGuard }  from './core/guards/instructor.guard';
import { EnrollmentGuard }  from './core/guards/enrollment.guard';

import { CourseResolver }      from './features/courses/resolvers/course.resolver';
import { LessonResolver }      from './features/lessons/resolvers/lesson.resolver';
import { QuizResolver }        from './features/quizzes/resolvers/quiz.resolver';
import { ProgressResolver }    from './features/progress/resolvers/progress.resolver';
import { CertificateResolver } from './features/certificates/resolvers/certificate.resolver';

export const routes: Routes = [
  // ── Public ──────────────────────────────────────────────────────────────────
  {
    path: '',
    loadComponent: () => import('./features/home/home.component').then(m => m.HomeComponent),
  },
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.module').then(m => m.AuthModule),
  },

  // ── Course catalogue (public) ────────────────────────────────────────────────
  {
    path: 'courses',
    loadComponent: () =>
      import('./features/courses/course-list/course-list.component').then(m => m.CourseListComponent),
  },
  {
    path: 'courses/:slug',
    loadComponent: () =>
      import('./features/courses/course-detail/course-detail.component').then(m => m.CourseDetailComponent),
    /**
     * CourseResolver runs BEFORE the component is created.
     * The component receives pre-loaded data via `this.route.snapshot.data['course']`
     * — no loading spinner needed on first render.
     */
    resolve: { course: CourseResolver },
  },

  // ── Learner area (requires auth + enrolment) ─────────────────────────────────
  {
    path: 'learn/:courseSlug',
    canActivate: [AuthGuard, EnrollmentGuard],
    resolve: { progress: ProgressResolver },
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./features/learn/course-player/course-player.component').then(m => m.CoursePlayerComponent),
      },
      {
        path: 'lessons/:lessonId',
        loadComponent: () =>
          import('./features/learn/lesson-viewer/lesson-viewer.component').then(m => m.LessonViewerComponent),
        /**
         * LessonResolver:
         *  1. Fetches the lesson metadata.
         *  2. Calls GET /api/v1/lessons/:id/signed-url/ to obtain a short-lived
         *     pre-signed S3 URL from the backend.
         *  3. Returns both as { lesson, videoUrl } in route data.
         *
         * This guarantees the signed URL is fresh when the component initialises,
         * and the <video> element can start buffering immediately.
         */
        resolve: { lesson: LessonResolver },
      },
      {
        path: 'quizzes/:quizId',
        loadComponent: () =>
          import('./features/learn/quiz-player/quiz-player.component').then(m => m.QuizPlayerComponent),
        resolve: { quiz: QuizResolver },
      },
    ],
  },

  // ── Instructor dashboard ─────────────────────────────────────────────────────
  {
    path: 'instructor',
    canActivate: [AuthGuard, InstructorGuard],
    loadChildren: () =>
      import('./features/instructor/instructor.module').then(m => m.InstructorModule),
  },

  // ── Certificates ─────────────────────────────────────────────────────────────
  {
    path: 'certificates',
    canActivate: [AuthGuard],
    loadComponent: () =>
      import('./features/certificates/certificate-list/certificate-list.component').then(
        m => m.CertificateListComponent,
      ),
    resolve: { certificates: CertificateResolver },
  },
  {
    path: 'certificates/verify/:id',
    loadComponent: () =>
      import('./features/certificates/certificate-verify/certificate-verify.component').then(
        m => m.CertificateVerifyComponent,
      ),
  },

  // ── Misc ─────────────────────────────────────────────────────────────────────
  {
    path: 'profile',
    canActivate: [AuthGuard],
    loadComponent: () =>
      import('./features/profile/profile.component').then(m => m.ProfileComponent),
  },
  { path: '**', redirectTo: '' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { scrollPositionRestoration: 'top' })],
  exports: [RouterModule],
})
export class AppRoutingModule {}
