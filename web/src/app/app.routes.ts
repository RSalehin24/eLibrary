import { inject } from '@angular/core';
import { ResolveFn, Routes } from '@angular/router';

import { Book } from './book';
import { BookApi } from './book-api';
import { BookDetail } from './book-detail/book-detail';

const bookResolver: ResolveFn<Book> = (route) =>
  inject(BookApi).book(route.paramMap.get('slug') ?? '');

export const routes: Routes = [
  { path: 'books/:slug', component: BookDetail, resolve: { book: bookResolver } },
];
