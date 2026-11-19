import { HttpInterceptorFn } from '@angular/common/http';
import { InjectionToken, inject } from '@angular/core';

/** Where `/api/*` lives for server-side rendering; unset in the browser, which uses the page origin. */
export const API_ORIGIN = new InjectionToken<string>('API_ORIGIN');

// why: on the server a relative URL would resolve to the public host (Caddy), which the container
// cannot reach; SSR calls the gateway by its internal address instead (INV-WEB-024).
export const apiOriginInterceptor: HttpInterceptorFn = (request, next) => {
  const origin = inject(API_ORIGIN, { optional: true });
  const needsOrigin = origin !== null && request.url.startsWith('/api/');
  return next(needsOrigin ? request.clone({ url: origin + request.url }) : request);
};
