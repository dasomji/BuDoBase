import { allocationRoutes } from './domains/allocation';
import { attendanceRoutes } from './domains/attendance';
import { authRoutes } from './domains/auth';
import { dashboardRoutes } from './domains/dashboard';
import { focusRoutes } from './domains/focuses';
import { kidRoutes } from './domains/kids';
import { kitchenRoutes } from './domains/kitchen';
import { maintenanceRoutes } from './domains/maintenance';
import { peopleRoutes } from './domains/people';
import { placeRoutes } from './domains/places';
import { reportRoutes } from './domains/reports';
import { notFoundRoute } from './domains/shared';

export const routeDefinitions = [
  ...dashboardRoutes,
  ...authRoutes,
  ...peopleRoutes,
  ...maintenanceRoutes,
  ...kidRoutes,
  ...attendanceRoutes,
  ...reportRoutes,
  ...focusRoutes,
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

export function routeHeaderAction(route, data) {
  return route.headerAction?.(data) || null;
}

export function isPublicRoute(route) {
  return route.domain === 'auth';
}
