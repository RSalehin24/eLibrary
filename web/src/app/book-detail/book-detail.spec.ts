import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute } from '@angular/router';
import { describe, expect, it } from 'vitest';

import { Book } from '../book';
import { BookDetail } from './book-detail';

const BOOK: Book = {
  slug: 'bangla-bhasha',
  title: 'বাংলা ভাষা',
  author: 'নমুনা লেখক',
  description: 'বর্ণনা',
  subjects: ['ভাষা'],
};

describe('BookDetail', () => {
  it('shows the book and sets the page title', async () => {
    TestBed.configureTestingModule({
      providers: [{ provide: ActivatedRoute, useValue: { snapshot: { data: { book: BOOK } } } }],
    });
    const fixture = TestBed.createComponent(BookDetail);
    await fixture.whenStable();
    expect(fixture.nativeElement.textContent).toContain('বাংলা ভাষা');
    expect(TestBed.inject(Title).getTitle()).toBe('বাংলা ভাষা — নমুনা লেখক');
  });
});
