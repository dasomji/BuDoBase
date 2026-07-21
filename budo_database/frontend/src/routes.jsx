import { allocationRoutes } from './domains/allocation';
import { auditRoutes } from './domains/audit';
import { attendanceRoutes } from './domains/attendance';
import { authRoutes } from './domains/auth';
import { dashboardRoutes } from './domains/dashboard';
import { focusRoutes } from './domains/focuses';
import { happyCleaningRoutes } from './domains/happyCleaning';
import { kidRoutes } from './domains/kids';
import { kitchenRoutes } from './domains/kitchen';
import { maintenanceRoutes } from './domains/maintenance';
import { profileRoutes } from './domains/profiles';
import { placeRoutes } from './domains/places';
import { reportRoutes } from './domains/reports';
import { notFoundRoute } from './domains/shared';

export const routeDefinitions = [
  ...dashboardRoutes,
  ...auditRoutes,
  ...authRoutes,
  ...profileRoutes,
  ...maintenanceRoutes,
  ...kidRoutes,
  ...attendanceRoutes,
  ...reportRoutes,
  ...focusRoutes,
  ...happyCleaningRoutes,
  ...placeRoutes,
  ...kitchenRoutes,
  ...allocationRoutes,
];

export function parseRoute(pathname) {
  const path = pathname.replace(/\/+$/, '') || '/';
  for (const definition of routeDefinitions) {
    const match = path.match(definition.pattern);
    if (match) return { ...definition, ...(definition.params?.(match) || {}) };
  }
  return notFoundRoute;
}

export function renderRoute(route, props) {
  return route.render({ route, ...props });
}

export function resolveRouteTitle(route, data) {
  if (!data?.authenticated) return route.title;
  return route.resolveTitle?.(route, data) || route.title;
}

export function resolveRouteHeaderTitle(route, data, title) {
  return route.resolveHeaderTitle?.(route, data, title) || title;
}

export function routeHeaderAction(route, data, pageContext = {}) {
  return route.headerAction?.(data, pageContext) || null;
}

export function isPublicRoute(route) {
  return route.domain === 'auth';
}
