import { RenderMode, ServerRoute } from '@angular/ssr';

// Public pages render per request (data comes from the API); nothing is prerendered.
export const serverRoutes: ServerRoute[] = [{ path: '**', renderMode: RenderMode.Server }];
