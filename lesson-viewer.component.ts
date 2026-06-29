/**
 * lesson-viewer.component.ts
 *
 * Renders a video lesson using the pre-signed S3 URL injected by LessonResolver.
 * Periodically saves watch position to the progress API.
 */
import {
  Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewInit,
} from '@angular/core';
import { ActivatedRoute }   from '@angular/router';
import { CommonModule }     from '@angular/common';
import { Subject, interval, takeUntil } from 'rxjs';

import { LessonDetail }     from '../../../models/lesson.model';
import { ProgressService }  from '../../../core/services/progress.service';

@Component({
  selector: 'app-lesson-viewer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="lesson-viewer">
      <!-- Lesson metadata is already available — no loading state needed -->
      <h1 class="lesson-title">{{ lesson.title }}</h1>

      <ng-container [ngSwitch]="lesson.lesson_type">

        <!-- VIDEO ──────────────────────────────────────────────────────── -->
        <ng-container *ngSwitchCase="'video'">
          <div class="video-wrapper">
            <video
              #videoPlayer
              class="video-player"
              controls
              controlsList="nodownload"
              [src]="lesson.video_url"
              (timeupdate)="onTimeUpdate($event)"
              (ended)="onVideoEnded()"
              (loadedmetadata)="resumePlayback()"
            ></video>
          </div>
        </ng-container>

        <!-- TEXT / ARTICLE ─────────────────────────────────────────────── -->
        <ng-container *ngSwitchCase="'text'">
          <article class="lesson-content" [innerHTML]="lesson.content"></article>
          <button class="btn-complete" (click)="markComplete()">
            Mark as Complete
          </button>
        </ng-container>

      </ng-container>

      <!-- Attachments -->
      <section *ngIf="lesson.attachments?.length" class="attachments">
        <h3>Downloads</h3>
        <ul>
          <li *ngFor="let att of lesson.attachments">
            <a [href]="att.file" target="_blank" download>{{ att.title }}</a>
          </li>
        </ul>
      </section>
    </div>
  `,
})
export class LessonViewerComponent implements OnInit, OnDestroy, AfterViewInit {

  @ViewChild('videoPlayer') videoRef!: ElementRef<HTMLVideoElement>;

  lesson!: LessonDetail;
  private destroy$ = new Subject<void>();
  private lastSavedPosition = 0;

  constructor(
    private route: ActivatedRoute,
    private progressService: ProgressService,
  ) {}

  ngOnInit(): void {
    /**
     * Data was pre-fetched by LessonResolver — available synchronously.
     * No HTTP call made in the component.
     */
    this.lesson = this.route.snapshot.data['lesson'];
  }

  ngAfterViewInit(): void {
    if (this.lesson.lesson_type === 'video') {
      // Auto-save watch position every 10 seconds
      interval(10_000)
        .pipe(takeUntil(this.destroy$))
        .subscribe(() => this.saveProgress(false));
    }
  }

  resumePlayback(): void {
    const progress = this.route.parent?.snapshot.data['progress'] as any[];
    const record   = progress?.find(p => p.lesson === this.lesson.id);
    if (record?.last_position_seconds && this.videoRef?.nativeElement) {
      this.videoRef.nativeElement.currentTime = record.last_position_seconds;
    }
  }

  onTimeUpdate(event: Event): void {
    const video    = event.target as HTMLVideoElement;
    const position = Math.floor(video.currentTime);
    // Throttle: only update local state, periodic save via interval
    this.lastSavedPosition = position;
  }

  onVideoEnded(): void {
    this.saveProgress(true);
  }

  markComplete(): void {
    this.saveProgress(true);
  }

  private saveProgress(completed: boolean): void {
    this.progressService.updateLessonProgress(this.lesson.id, {
      last_position_seconds: this.lastSavedPosition,
      is_completed: completed,
    }).pipe(takeUntil(this.destroy$)).subscribe();
  }

  ngOnDestroy(): void {
    this.saveProgress(false); // final save on leave
    this.destroy$.next();
    this.destroy$.complete();
  }
}
