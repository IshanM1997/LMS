/**
 * quiz-player.component.ts
 *
 * Quiz player with timer, multi-select answers, and submission.
 * Quiz data is pre-fetched by QuizResolver.
 */
import {
  Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef,
} from '@angular/core';
import { CommonModule }   from '@angular/common';
import { FormsModule }    from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Subject, interval, takeUntil } from 'rxjs';

import { Quiz, Question, QuizAttempt } from '../../../models/quiz.model';
import { QuizService }                  from '../../../core/services/quiz.service';

interface AnswerMap { [questionId: number]: number[] | string }

@Component({
  selector: 'app-quiz-player',
  standalone: true,
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="quiz-player" *ngIf="quiz">

      <!-- Header -->
      <div class="quiz-header">
        <h2>{{ quiz.title }}</h2>
        <div class="quiz-meta">
          <span>{{ quiz.question_count }} questions</span>
          <span *ngIf="quiz.pass_percentage"> · Pass: {{ quiz.pass_percentage }}%</span>
          <span *ngIf="timeRemaining !== null" class="timer" [class.urgent]="timeRemaining < 60">
            ⏱ {{ formatTime(timeRemaining) }}
          </span>
        </div>
      </div>

      <!-- Pre-attempt -->
      <div *ngIf="!attempt" class="quiz-start">
        <p>{{ quiz.description }}</p>
        <p *ngIf="quiz.time_limit_minutes">Time limit: {{ quiz.time_limit_minutes }} min</p>
        <p>Max attempts: {{ quiz.max_attempts }}</p>
        <button class="btn-primary" (click)="startAttempt()">Start Quiz</button>
      </div>

      <!-- In-progress -->
      <div *ngIf="attempt && !result" class="quiz-body">
        <div class="question-card" *ngFor="let q of quiz.questions; let i = index">
          <p class="question-text"><strong>{{ i + 1 }}.</strong> {{ q.text }}</p>
          <img *ngIf="q.image" [src]="q.image" class="question-image" alt="Question image" />

          <!-- Single / Multiple choice -->
          <ul *ngIf="q.question_type !== 'short_answer'" class="choices">
            <li *ngFor="let c of q.choices">
              <label>
                <input
                  [type]="q.question_type === 'multiple' ? 'checkbox' : 'radio'"
                  [name]="'q_' + q.id"
                  [value]="c.id"
                  (change)="onChoiceChange(q, c.id, $event)"
                />
                {{ c.text }}
              </label>
            </li>
          </ul>

          <!-- Short answer -->
          <textarea
            *ngIf="q.question_type === 'short_answer'"
            [(ngModel)]="answers[q.id]"
            rows="3"
            placeholder="Your answer…"
          ></textarea>
        </div>

        <button class="btn-primary" (click)="submitQuiz()" [disabled]="submitting">
          {{ submitting ? 'Submitting…' : 'Submit Quiz' }}
        </button>
      </div>

      <!-- Result -->
      <div *ngIf="result" class="quiz-result" [class.passed]="result.passed" [class.failed]="!result.passed">
        <h3>{{ result.passed ? '🎉 Passed!' : '😞 Not Passed' }}</h3>
        <p>Score: <strong>{{ result.score }}%</strong></p>
        <p>{{ result.earned_points }} / {{ result.total_points }} points</p>
        <button class="btn-secondary" (click)="reset()">Try Again</button>
      </div>

    </div>
  `,
})
export class QuizPlayerComponent implements OnInit, OnDestroy {

  quiz!: Quiz;
  attempt: QuizAttempt | null = null;
  result: QuizAttempt | null  = null;
  answers: AnswerMap = {};
  submitting = false;
  timeRemaining: number | null = null;

  private destroy$ = new Subject<void>();

  constructor(
    private route: ActivatedRoute,
    private quizService: QuizService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.quiz = this.route.snapshot.data['quiz'];
  }

  startAttempt(): void {
    this.quizService.startAttempt(this.quiz.id).subscribe(attempt => {
      this.attempt = attempt;
      this.answers = {};
      if (this.quiz.time_limit_minutes) {
        this.startTimer(this.quiz.time_limit_minutes * 60);
      }
      this.cdr.markForCheck();
    });
  }

  onChoiceChange(question: Question, choiceId: number, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    if (question.question_type === 'multiple') {
      const current = (this.answers[question.id] as number[]) ?? [];
      this.answers[question.id] = checked
        ? [...current, choiceId]
        : current.filter(id => id !== choiceId);
    } else {
      this.answers[question.id] = [choiceId];
    }
  }

  submitQuiz(): void {
    if (!this.attempt) return;
    this.submitting = true;

    const responses = this.quiz.questions.map(q => ({
      question: q.id,
      selected_choices: Array.isArray(this.answers[q.id]) ? this.answers[q.id] : [],
      text_answer: typeof this.answers[q.id] === 'string' ? this.answers[q.id] : '',
    }));

    this.quizService.submitAttempt(this.quiz.id, this.attempt.attempt_id, responses)
      .subscribe(result => {
        this.result    = result;
        this.submitting = false;
        this.cdr.markForCheck();
      });
  }

  reset(): void {
    this.attempt  = null;
    this.result   = null;
    this.answers  = {};
    this.timeRemaining = null;
  }

  formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  private startTimer(seconds: number): void {
    this.timeRemaining = seconds;
    interval(1000).pipe(takeUntil(this.destroy$)).subscribe(() => {
      if (this.timeRemaining! > 0) {
        this.timeRemaining!--;
        this.cdr.markForCheck();
      } else {
        this.submitQuiz();
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
