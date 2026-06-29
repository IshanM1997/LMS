# 🎓 LMS — Learning Management System

A production-ready Learning Management System built with **Django REST Framework** (backend) and **Angular 17** (frontend).  
Features courses, video lessons with S3 signed-URL streaming, quizzes, progress tracking, and auto-generated PDF certificates.

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Folder Structure](#folder-structure)
- [Key Design Patterns](#key-design-patterns)
  - [Django Content-Type Framework](#django-content-type-framework)
  - [Video Streaming with Signed URLs](#video-streaming-with-signed-urls)
  - [Angular Route Resolvers](#angular-route-resolvers)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Environment Variables](#environment-variables)

---

## Features

| Area | Details |
|---|---|
| **Courses** | Catalogue, categories, tags (via Content Types), reviews, enrolment |
| **Video Lessons** | AWS S3 private storage, pre-signed GET URLs (time-limited), direct-upload pre-signed PUT URLs |
| **Quizzes** | Single/multi-choice, true/false, short-answer, timed attempts, auto-scoring |
| **Progress** | Lesson-level watch time & completion, course-level percentage, resume playback |
| **Certificates** | Auto-generated PDF via Celery when 100% complete, signed S3 download URL, public verification |
| **Auth** | JWT (access + refresh), role-based (student / instructor / admin) |

---

## Architecture Overview

```
Browser (Angular SPA)
       │
       ▼
   Nginx (80/443)
    ├── /api  ──►  Django (Gunicorn :8000)
    │                   ├── PostgreSQL (data)
    │                   ├── Redis (cache + Celery broker)
    │                   └── Celery Worker (PDF generation, email)
    └── /     ──►  Angular dist (static files)
                        │
                        └── AWS S3 (videos + certificates — direct signed-URL access)
```

---

## Tech Stack

**Backend**

| Library | Version | Purpose |
|---|---|---|
| Django | 5.0 | Web framework |
| djangorestframework | 3.15 | REST API |
| djangorestframework-simplejwt | 5.3 | JWT authentication |
| django-filter | 24 | Queryset filtering |
| boto3 | 1.34 | AWS S3 (signed URLs) |
| Celery + Redis | 5.4 | Async tasks (certificate generation) |
| ReportLab | 4.1 | PDF certificate rendering |
| PostgreSQL | 16 | Primary database |

**Frontend**

| Library | Version | Purpose |
|---|---|---|
| Angular | 17 | SPA framework |
| Angular Router | 17 | Resolvers, lazy-loaded routes |
| RxJS | 7 | Reactive streams |
| Angular HTTP Client | 17 | API calls + JWT interceptor |

---

## Folder Structure

```
lms/
│
├── docker-compose.yml          # Full stack: db, redis, backend, celery, frontend, nginx
├── .env.example                # Environment variable template
│
├── backend/                    # Django project root
│   ├── manage.py
│   ├── requirements.txt
│   ├── Dockerfile
│   │
│   ├── config/                 # Django project package
│   │   ├── __init__.py
│   │   ├── settings.py         # All settings (JWT, S3, Redis, Celery, CORS, …)
│   │   ├── urls.py             # Root URL conf → api/v1/ router
│   │   ├── wsgi.py
│   │   └── celery.py           # Celery app initialisation
│   │
│   ├── apps/
│   │   │
│   │   ├── users/              # Custom User model & auth helpers
│   │   │   ├── models.py           User, UserProfile
│   │   │   ├── serializers.py      Registration, Me, ChangePassword
│   │   │   ├── views.py            RegisterView, MeView, UserViewSet
│   │   │   ├── urls.py
│   │   │   └── admin.py
│   │   │
│   │   ├── courses/            # Course catalogue
│   │   │   ├── models.py
│   │   │   │   ├── Tag             Generic tag (Content Type framework)
│   │   │   │   ├── TaggedItem      Through-model: Tag ↔ any object (CT + object_id)
│   │   │   │   ├── Review          Generic review (CT + object_id)
│   │   │   │   ├── Category        Hierarchical categories
│   │   │   │   ├── Course          Main course model (GenericRelation → tags, reviews)
│   │   │   │   ├── Enrollment      Student ↔ Course membership
│   │   │   │   └── Section         Ordered groups of lessons within a course
│   │   │   ├── serializers.py
│   │   │   ├── views.py            CourseViewSet (enroll, publish, reviews actions)
│   │   │   ├── permissions.py      IsInstructorOrReadOnly, IsEnrolledOrInstructor
│   │   │   ├── urls.py
│   │   │   └── admin.py
│   │   │
│   │   ├── lessons/            # Video & text lessons
│   │   │   ├── models.py
│   │   │   │   ├── Lesson          video_s3_key, generate_signed_video_url()
│   │   │   │   ├── VideoUploadRequest  Pre-signed PUT URL for direct browser→S3 upload
│   │   │   │   └── LessonAttachment    Downloadable files per lesson
│   │   │   ├── serializers.py
│   │   │   ├── views.py            LessonViewSet (request_upload_url, confirm_upload)
│   │   │   ├── urls.py
│   │   │   └── admin.py
│   │   │
│   │   ├── quizzes/            # Quiz engine
│   │   │   ├── models.py
│   │   │   │   ├── Quiz            pass_percentage, time_limit, max_attempts
│   │   │   │   ├── Question        single/multiple/true_false/short_answer
│   │   │   │   ├── Choice          answer options (is_correct hidden from students)
│   │   │   │   ├── QuizAttempt     per-student attempt (UUID, score, passed)
│   │   │   │   └── QuestionResponse  selected choices + text answer
│   │   │   ├── serializers.py
│   │   │   ├── views.py            QuizViewSet (start, submit, my-attempts actions)
│   │   │   ├── urls.py
│   │   │   └── admin.py
│   │   │
│   │   ├── progress/           # Progress tracking
│   │   │   ├── models.py
│   │   │   │   ├── LessonProgress  watch_time_seconds, last_position_seconds, is_completed
│   │   │   │   └── CourseProgress  percentage, recompute(), triggers certificate
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   └── urls.py
│   │   │
│   │   └── certificates/       # Certificate generation & delivery
│   │       ├── models.py           Certificate (UUID, pdf_s3_key, get_download_url())
│   │       ├── tasks.py            generate_certificate Celery task (ReportLab → S3 → email)
│   │       ├── serializers.py
│   │       ├── views.py            MyCertificatesView, CertificateVerifyView, DownloadView
│   │       └── urls.py
│   │
│   └── templates/
│       └── certificates/       # Certificate HTML templates (WeasyPrint alternative)
│
├── frontend/                   # Angular 17 application
│   ├── angular.json
│   ├── package.json
│   ├── tsconfig.json
│   ├── Dockerfile
│   │
│   ├── src/
│   │   ├── main.ts
│   │   ├── app/
│   │   │   ├── app.module.ts
│   │   │   ├── app-routing.module.ts       All routes with resolver bindings
│   │   │   │
│   │   │   ├── core/                       Singletons (loaded once)
│   │   │   │   ├── guards/
│   │   │   │   │   ├── auth.guard.ts           Redirects unauthenticated users
│   │   │   │   │   ├── instructor.guard.ts     Role check: instructor | admin
│   │   │   │   │   └── enrollment.guard.ts     Checks course.is_enrolled
│   │   │   │   ├── interceptors/
│   │   │   │   │   └── jwt.interceptor.ts      Attaches Bearer token; silent refresh on 401
│   │   │   │   └── services/
│   │   │   │       ├── auth.service.ts
│   │   │   │       ├── course.service.ts
│   │   │   │       ├── lesson.service.ts       uploadVideoToS3() (direct PUT to S3)
│   │   │   │       ├── quiz.service.ts
│   │   │   │       ├── progress.service.ts
│   │   │   │       └── certificate.service.ts
│   │   │   │
│   │   │   ├── models/                     TypeScript interfaces
│   │   │   │   ├── course.model.ts
│   │   │   │   ├── lesson.model.ts         LessonDetail.video_url (signed URL)
│   │   │   │   ├── quiz.model.ts
│   │   │   │   ├── progress.model.ts
│   │   │   │   ├── certificate.model.ts
│   │   │   │   └── pagination.model.ts
│   │   │   │
│   │   │   ├── features/
│   │   │   │   ├── auth/                   Login, Register pages
│   │   │   │   ├── home/                   Landing page
│   │   │   │   ├── courses/
│   │   │   │   │   ├── resolvers/
│   │   │   │   │   │   └── course.resolver.ts  Fetches Course by slug before navigation
│   │   │   │   │   ├── services/           (re-exports from core)
│   │   │   │   │   ├── course-list/        Course catalogue with filters
│   │   │   │   │   └── course-detail/      Full course page (pre-loaded by resolver)
│   │   │   │   │
│   │   │   │   ├── learn/                  Authenticated learner area
│   │   │   │   │   ├── course-player/      Sidebar + section/lesson navigation
│   │   │   │   │   ├── lesson-viewer/
│   │   │   │   │   │   ├── lesson-viewer.component.ts
│   │   │   │   │   │   │   Video player using pre-signed URL from LessonResolver;
│   │   │   │   │   │   │   auto-saves watch position every 10 s; resumes from last position
│   │   │   │   │   │   └── resolvers/
│   │   │   │   │   │       └── lesson.resolver.ts  GET lesson + signed video URL
│   │   │   │   │   └── quiz-player/
│   │   │   │   │       ├── quiz-player.component.ts  Timer, multi-select, submit
│   │   │   │   │       └── resolvers/
│   │   │   │   │           └── quiz.resolver.ts
│   │   │   │   │
│   │   │   │   ├── instructor/             Instructor dashboard (lazy module)
│   │   │   │   │   ├── instructor.module.ts
│   │   │   │   │   ├── course-form/        Create / edit course
│   │   │   │   │   ├── lesson-form/        Upload video (pre-signed PUT → S3)
│   │   │   │   │   ├── quiz-builder/       Add questions & choices
│   │   │   │   │   └── analytics/          Enrolment + completion stats
│   │   │   │   │
│   │   │   │   ├── progress/
│   │   │   │   │   └── resolvers/
│   │   │   │   │       └── progress.resolver.ts  Pre-fetches lesson progress array
│   │   │   │   │
│   │   │   │   ├── certificates/
│   │   │   │   │   ├── resolvers/
│   │   │   │   │   │   └── certificate.resolver.ts
│   │   │   │   │   ├── certificate-list/   My certificates + signed download links
│   │   │   │   │   └── certificate-verify/ Public verification page
│   │   │   │   │
│   │   │   │   └── profile/                User profile & password change
│   │   │   │
│   │   │   └── shared/                     Reusable components & pipes
│   │   │       ├── components/
│   │   │       │   ├── star-rating/
│   │   │       │   ├── progress-bar/
│   │   │       │   ├── video-player/       Thin wrapper around <video>
│   │   │       │   └── pagination/
│   │   │       └── pipes/
│   │   │           ├── duration.pipe.ts    seconds → MM:SS
│   │   │           └── file-size.pipe.ts   bytes → KB/MB
│   │   │
│   │   └── environments/
│   │       ├── environment.ts
│   │       └── environment.prod.ts
│   │
│   └── nginx.conf              # Serve Angular SPA; proxy /api → backend
│
└── nginx/
    └── nginx.conf              # Main reverse-proxy config
```

---

## Key Design Patterns

### Django Content-Type Framework

Tags and Reviews are attached to **any** model (Course, Lesson, etc.) without hard-coded foreign keys.

```python
# courses/models.py

class TaggedItem(models.Model):
    tag          = models.ForeignKey(Tag, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id    = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

class Course(models.Model):
    # Exposes a queryset of TaggedItem rows for this course
    tags    = GenericRelation(TaggedItem)
    reviews = GenericRelation(Review)
```

Usage:
```python
ct = ContentType.objects.get_for_model(Course)
TaggedItem.objects.create(tag=python_tag, content_type=ct, object_id=course.pk)
```

---

### Video Streaming with Signed URLs

Videos are stored in a **private** S3 bucket. Clients never receive the S3 key — only a time-limited URL.

**Upload flow (instructor → S3 direct upload)**

```
Instructor browser
  → POST /api/v1/lessons/:id/request-upload-url/
  ← { presigned_upload_url, s3_key }          (Django generates PUT URL)
  → PUT <presigned_upload_url> (raw file)       (browser → S3, bypasses Django)
  → POST /api/v1/lessons/:id/confirm-upload/    (Django records s3_key on Lesson)
```

**Playback flow (student)**

```
Angular LessonResolver
  → GET /api/v1/lessons/:id/              (requires enrolment)
  ← { ..., video_url: "https://s3.amazonaws.com/...?X-Amz-Signature=..." }
                                          (Django calls lesson.generate_signed_video_url())
Angular <video [src]="lesson.video_url">  (browser streams directly from S3)
```

Signed URL code:
```python
# lessons/models.py
def generate_signed_video_url(self, expiry_seconds=3600) -> str:
    s3 = boto3.client('s3', ...)
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': self.video_s3_key},
        ExpiresIn=expiry_seconds,
    )
```

---

### Angular Route Resolvers

Resolvers run **before** component activation — data is available synchronously in `ngOnInit`.  
No loading spinners, no conditional `*ngIf="data"` guards needed in templates.

```typescript
// app-routing.module.ts
{
  path: 'learn/:courseSlug/lessons/:lessonId',
  component: LessonViewerComponent,
  resolve: { lesson: LessonResolver },   // ← runs first
}

// lesson-viewer.component.ts
ngOnInit() {
  this.lesson = this.route.snapshot.data['lesson'];   // synchronous
  // this.lesson.video_url is already the signed S3 URL
}
```

**Resolver hierarchy for the Learn area:**

```
/learn/:courseSlug          ← ProgressResolver   (lesson progress array)
  /lessons/:lessonId        ← LessonResolver     (lesson + signed video URL)
  /quizzes/:quizId          ← QuizResolver       (quiz + questions)
```

**Certificate resolver** pre-loads the full certificates list so the page renders instantly:

```typescript
// certificates/certificate-list.component.ts
ngOnInit() {
  this.certificates = this.route.snapshot.data['certificates'];
}
```

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Node 20 + Angular CLI (for local frontend dev)
- AWS account with an S3 bucket (for video storage)

### 1. Clone & configure

```bash
git clone https://github.com/yourorg/lms.git
cd lms
cp .env.example backend/.env
# Edit backend/.env with your database, AWS, and email credentials
```

### 2. Start all services

```bash
docker compose up --build
```

Services available at:

| Service | URL |
|---|---|
| Angular SPA | http://localhost:80 |
| Django API | http://localhost:8000/api/v1/ |
| Django Admin | http://localhost:8000/admin/ |

### 3. Bootstrap data

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py loaddata initial_categories
```

### 4. Frontend development

```bash
cd frontend
npm install
ng serve        # http://localhost:4200
```

### 5. Run tests

```bash
# Backend
docker compose exec backend pytest --cov=apps

# Frontend
cd frontend && ng test
```

---

## API Reference

### Auth

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/token/` | Obtain access + refresh tokens |
| POST | `/api/v1/auth/token/refresh/` | Refresh access token |
| POST | `/api/v1/users/register/` | Create account |
| GET/PATCH | `/api/v1/users/me/` | Profile |

### Courses

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/courses/` | List courses (filterable) |
| GET | `/api/v1/courses/:slug/` | Course detail |
| POST | `/api/v1/courses/:slug/enroll/` | Enrol in course |
| POST | `/api/v1/courses/:slug/publish/` | Publish (instructor) |
| GET/POST | `/api/v1/courses/:slug/reviews/` | List / add reviews |

### Lessons

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/lessons/:id/` | Lesson detail (includes signed video URL) |
| POST | `/api/v1/lessons/:id/request-upload-url/` | Pre-signed S3 PUT URL |
| POST | `/api/v1/lessons/:id/confirm-upload/` | Confirm upload completed |

### Quizzes

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/quizzes/:id/` | Quiz with questions |
| POST | `/api/v1/quizzes/:id/start/` | Start attempt |
| POST | `/api/v1/quizzes/:id/submit/:attemptId/` | Submit & score |
| GET | `/api/v1/quizzes/:id/my-attempts/` | My attempt history |

### Progress

| Method | Path | Description |
|---|---|---|
| PATCH | `/api/v1/progress/lessons/:lessonId/` | Update watch time / mark complete |
| GET | `/api/v1/progress/courses/` | All course-level progress |
| GET | `/api/v1/progress/courses/:slug/lessons/` | Lesson-level progress |

### Certificates

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/certificates/` | My certificates |
| GET | `/api/v1/certificates/:id/download/` | Signed PDF URL |
| GET | `/api/v1/certificates/:id/verify/` | Public verification |

---

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DB_*` | PostgreSQL connection |
| `REDIS_URL` | Redis connection (cache + Celery) |
| `AWS_ACCESS_KEY_ID` | AWS credentials for S3 |
| `AWS_STORAGE_BUCKET_NAME` | Private S3 bucket for videos + certificates |
| `AWS_SIGNED_URL_EXPIRY` | Signed URL lifetime in seconds (default 3600) |
| `CORS_ALLOWED_ORIGINS` | Angular dev/prod origins |

---

## License

MIT © 2024 Your Organization
