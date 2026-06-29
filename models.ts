/**
 * models/course.model.ts
 */
export interface CourseList {
  id: number;
  title: string;
  slug: string;
  subtitle: string;
  thumbnail: string;
  instructor_name: string;
  category_name: string;
  level: 'beginner' | 'intermediate' | 'advanced' | 'all';
  status: 'draft' | 'published' | 'archived';
  effective_price: number;
  is_free: boolean;
  total_enrolled: number;
  average_rating: number;
  language: string;
  certificate_enabled: boolean;
  created_at: string;
}

export interface Section {
  id: number;
  title: string;
  description: string;
  order: number;
  lesson_count: number;
  lessons?: LessonSummary[];
}

export interface LessonSummary {
  id: number;
  title: string;
  lesson_type: 'video' | 'text' | 'quiz' | 'assignment';
  order: number;
  duration_seconds: number;
  duration_formatted: string;
  is_free_preview: boolean;
  is_published: boolean;
}

export interface Review {
  id: number;
  author: number;
  author_name: string;
  rating: 1 | 2 | 3 | 4 | 5;
  title: string;
  body: string;
  is_approved: boolean;
  created_at: string;
}

export interface Course extends CourseList {
  description: string;
  instructor: number;
  category: number;
  price: number;
  discount_price: number | null;
  preview_video_url: string;
  what_you_will_learn: string[];
  requirements: string[];
  who_is_this_for: string;
  enrollment_limit: number | null;
  published_at: string | null;
  sections: Section[];
  tags: { id: number; name: string; slug: string }[];
  reviews: Review[];
  is_enrolled: boolean;
}


/**
 * models/lesson.model.ts
 */
export interface LessonAttachment {
  id: number;
  title: string;
  file: string;
  file_size: number;
  created_at: string;
}

export interface LessonDetail {
  id: number;
  section: number;
  title: string;
  lesson_type: 'video' | 'text' | 'quiz' | 'assignment';
  order: number;
  description: string;
  content: string;
  duration_seconds: number;
  duration_formatted: string;
  is_free_preview: boolean;
  is_published: boolean;
  /** Pre-signed S3 URL (expires in 1 h) — generated server-side */
  video_url: string;
  thumbnail_url: string;
  external_video_url: string;
  attachments: LessonAttachment[];
  created_at: string;
}


/**
 * models/quiz.model.ts
 */
export interface Choice {
  id: number;
  text: string;
  order: number;
}

export interface Question {
  id: number;
  text: string;
  question_type: 'single' | 'multiple' | 'true_false' | 'short_answer';
  image: string | null;
  points: number;
  order: number;
  choices: Choice[];
}

export interface Quiz {
  id: number;
  course: number;
  lesson: number | null;
  title: string;
  description: string;
  pass_percentage: number;
  time_limit_minutes: number | null;
  max_attempts: number;
  randomize_questions: boolean;
  show_answers_after: boolean;
  is_published: boolean;
  question_count: number;
  questions: Question[];
}

export interface QuizAttempt {
  attempt_id: string;
  quiz: number;
  status: 'in_progress' | 'submitted' | 'timed_out';
  score: number | null;
  total_points: number;
  earned_points: number;
  passed: boolean | null;
  started_at: string;
  submitted_at: string | null;
}


/**
 * models/progress.model.ts
 */
export interface LessonProgress {
  id: number;
  lesson: number;
  lesson_title: string;
  is_completed: boolean;
  watch_time_seconds: number;
  last_position_seconds: number;
  completed_at: string | null;
  updated_at: string;
}

export interface CourseProgress {
  id: number;
  course_title: string;
  course_slug: string;
  total_lessons: number;
  completed_lessons: number;
  percentage: number;
  last_accessed_lesson: number | null;
  updated_at: string;
}


/**
 * models/certificate.model.ts
 */
export interface Certificate {
  certificate_id: string;
  course: number;
  course_title: string;
  student_name: string;
  issued_at: string;
  download_url: string;
  verification_url: string;
}


/**
 * models/pagination.model.ts
 */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
