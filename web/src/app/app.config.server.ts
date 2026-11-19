import { ApplicationConfig, mergeApplicationConfig } from '@angular/core';
import { provideServerRendering, withRoutes } from '@angular/ssr';

import { appConfig } from './app.config';
import { serverRoutes } from './app.routes.server';
import { API_ORIGIN } from './core/api-origin';

// Spike default: the fixture API is served by this same server. In the stack it is the gateway.
const DEFAULT_API_ORIGIN = 'http://127.0.0.1:4000';

const serverConfig: ApplicationConfig = {
  providers: [
    provideServerRendering(withRoutes(serverRoutes)),
    { provide: API_ORIGIN, useValue: process.env['ELIBRARY_API_ORIGIN'] ?? DEFAULT_API_ORIGIN },
  ],
};

export const config = mergeApplicationConfig(appConfig, serverConfig);
