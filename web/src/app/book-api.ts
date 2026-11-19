import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { Book } from './book';

@Injectable({ providedIn: 'root' })
export class BookApi {
  private readonly http = inject(HttpClient);

  book(slug: string): Observable<Book> {
    return this.http.get<Book>(`/api/catalog/books/${encodeURIComponent(slug)}`);
  }
}
