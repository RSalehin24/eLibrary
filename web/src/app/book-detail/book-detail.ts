import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';
import { Meta, Title } from '@angular/platform-browser';
import { ActivatedRoute } from '@angular/router';

import { Book, parseBook } from '../book';

@Component({
  selector: 'app-book-detail',
  imports: [MatCardModule, MatChipsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <mat-card appearance="outlined">
      <mat-card-header>
        <mat-card-title>{{ book.title }}</mat-card-title>
        <mat-card-subtitle>{{ book.author }}</mat-card-subtitle>
      </mat-card-header>
      <mat-card-content>
        <p>{{ book.description }}</p>
        <mat-chip-set aria-label="বিষয়">
          @for (subject of book.subjects; track subject) {
            <mat-chip>{{ subject }}</mat-chip>
          }
        </mat-chip-set>
      </mat-card-content>
    </mat-card>
  `,
  styles: `
    :host {
      display: block;
      max-width: 48rem;
      margin: 1rem auto;
      padding: 0 1rem;
    }
  `,
})
export class BookDetail {
  protected readonly book: Book = parseBook(inject(ActivatedRoute).snapshot.data['book']);

  constructor() {
    inject(Title).setTitle(`${this.book.title} — ${this.book.author}`);
    inject(Meta).updateTag({ name: 'description', content: this.book.description });
  }
}
