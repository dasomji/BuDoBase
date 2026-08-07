import { useState } from 'react';
import {
  ChefHat,
  ChevronRight,
  ClipboardList,
  Gamepad2,
  ListChecks,
  MapPinned,
  Settings,
  Sparkles,
  UserRound,
  UsersRound,
} from 'lucide-react';

import { Logo } from './components';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarProvider,
  SidebarRail,
  useSidebar,
} from '@/components/ui/sidebar';
import { TooltipProvider } from '@/components/ui/tooltip';

const gamesUrl = 'https://honey-glue-e51.notion.site/Methoden-eaff0abb8b2a42bfb319c50d5357022c';

export const sidebarItems = [
  {
    label: 'Listen',
    icon: ClipboardList,
    children: [
      { label: 'Alle Kinder', href: '/all_kids' },
      { label: 'Gut zu wissen', href: '/gut-zu-wissen/' },
      { label: 'Mörderspielliste', href: '/murdergame' },
      { label: 'Zugabreise', href: '/zugabreise' },
      { label: 'Zuganreise', href: '/zuganreise' },
      { label: 'BuDo-Familien', href: '/budo_familien/' },
      { label: 'Spezialfamilien', href: '/spezial_familien/' },
    ],
  },
  {
    label: 'Schwerpunkte',
    icon: ListChecks,
    children: [
      { label: 'Übersicht', href: '/swp-dashboard/' },
      { label: 'SWP 1', href: '/swp-einteilung-w1' },
      { label: 'SWP 2', href: '/swp-einteilung-w2' },
    ],
  },
  {
    label: 'Happy Cleaning',
    icon: Sparkles,
    children: [
      { label: 'Übersicht', href: '/happy-cleaning/' },
      { label: 'Nummernliste', href: '/happy-cleaning/print/' },
    ],
  },
  { label: 'Auslagerorte', href: '/auslagerorte-list/', icon: MapPinned },
  { label: 'Küche', href: '/kitchen', icon: ChefHat },
  { label: 'Spiele', href: gamesUrl, icon: Gamepad2, external: true },
  { label: 'Team', href: '/team/', icon: UsersRound },
  {
    label: 'Orgi',
    icon: Settings,
    children: [
      { label: 'Serienbrief', href: '/serienbrief' },
      { label: 'Turnis', href: '/upload/' },
      { label: 'Aufenthaltsdoku', href: '/download-updated-excel/' },
      { label: 'Admin', href: '/admin/' },
    ],
  },
];

function normalizedPath(value) {
  if (!value || value === '/') return '/';
  return value.replace(/\/+$/, '');
}

function isCurrent(href, activePrefix) {
  if (/^https?:/.test(href)) return false;
  const pathname = normalizedPath(window.location.pathname);
  if (pathname === normalizedPath(href)) return true;
  if (!activePrefix) return false;
  const prefix = normalizedPath(activePrefix);
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

function NavigationLink({ item, sub = false }) {
  const Icon = item.icon;
  const link = (
    <a
      href={item.href}
      target={item.external ? '_blank' : undefined}
      rel={item.external ? 'noreferrer' : undefined}
    >
      {Icon && <Icon aria-hidden="true" />}
      <span>{item.label}</span>
    </a>
  );
  if (sub) {
    return <SidebarMenuSubButton render={link} isActive={isCurrent(item.href, item.activePrefix)} />;
  }
  return (
    <SidebarMenuButton
      render={link}
      isActive={isCurrent(item.href, item.activePrefix)}
      tooltip={item.label}
    />
  );
}

const SIDEBAR_GROUP_COOKIE_MAX_AGE = 60 * 60 * 24 * 7;
const SIDEBAR_STATE_COOKIE_NAME = 'sidebar_state';

function readSidebarState() {
  if (typeof document === 'undefined') return true;
  const prefix = `${SIDEBAR_STATE_COOKIE_NAME}=`;
  const cookie = document.cookie.split('; ').find(value => value.startsWith(prefix));
  return cookie ? cookie.slice(prefix.length) !== 'false' : true;
}

function sidebarGroupCookieName(label) {
  return `sidebar_group_${encodeURIComponent(label)}`;
}

function readSidebarGroupState(label) {
  const name = `${sidebarGroupCookieName(label)}=`;
  const cookie = document.cookie.split('; ').find(value => value.startsWith(name));
  return cookie ? cookie.slice(name.length) === 'true' : true;
}

function writeSidebarGroupState(label, open) {
  document.cookie = `${sidebarGroupCookieName(label)}=${open}; path=/; max-age=${SIDEBAR_GROUP_COOKIE_MAX_AGE}`;
}

function NavigationGroup({ item, index }) {
  const [open, setOpen] = useState(() => readSidebarGroupState(item.label));
  const { state, setOpen: setSidebarOpen } = useSidebar();
  const Icon = item.icon;
  const id = `sidebar-group-${index}`;
  const active = item.children.some(child => isCurrent(child.href, child.activePrefix));
  const setGroupOpen = value => {
    setOpen(current => {
      const next = typeof value === 'function' ? value(current) : value;
      writeSidebarGroupState(item.label, next);
      return next;
    });
  };
  const toggle = () => {
    if (state === 'collapsed') {
      setSidebarOpen(true);
      setGroupOpen(true);
      return;
    }
    setGroupOpen(value => !value);
  };
  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        aria-controls={id}
        aria-expanded={open}
        isActive={active}
        onClick={toggle}
        tooltip={item.label}
      >
        <Icon aria-hidden="true" />
        <span>{item.label}</span>
        <ChevronRight className={`sidebar-group-chevron ${open ? 'open' : ''}`} aria-hidden="true" />
      </SidebarMenuButton>
      {open && (
        <SidebarMenuSub id={id}>
          {item.children.map(child => (
            <SidebarMenuSubItem key={child.href}>
              <NavigationLink item={child} sub />
            </SidebarMenuSubItem>
          ))}
        </SidebarMenuSub>
      )}
    </SidebarMenuItem>
  );
}

function withDynamicNavEntries(events, permissions) {
  const eventItems = [...events]
    .sort((left, right) => (
      left.display_number - right.display_number || left.id - right.id
    ))
    .map(event => ({
      label: `Happy Cleaning ${event.display_number}`,
      href: `/happy-cleaning/${event.id}/assignment/`,
      activePrefix: `/happy-cleaning/${event.id}`,
    }));
  return sidebarItems.map(item => {
    if (item.label === 'Happy Cleaning') {
      return {
        ...item,
        children: [item.children[0], ...eventItems, item.children[1]],
      };
    }
    if (item.label === 'Orgi' && permissions?.view_auditevent) {
      return {
        ...item,
        children: [
          ...item.children.slice(0, -1),
          { label: 'Audit-Log', href: '/audit/' },
          item.children.at(-1),
        ],
      };
    }
    return item;
  });
}

export function AppSidebar({ happyCleaningEvents = [], permissions }) {
  const items = withDynamicNavEntries(happyCleaningEvents, permissions);
  return (
    <Sidebar side="left" collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              render={<a href="/dashboard/" />}
              tooltip="BuDoBase Dashboard"
              className="sidebar-brand"
            >
              <Logo />
              <span>BuDoBase</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <nav
              className="max-[900px]:[&_[data-sidebar=menu-button]]:text-[1.2rem] max-[900px]:[&_[data-sidebar=menu-sub-button]]:text-[1.2rem]"
              aria-label="Hauptnavigation"
            >
              <SidebarMenu>
                {items.map((item, index) => item.children ? (
                  <NavigationGroup item={item} index={index} key={item.label} />
                ) : (
                  <SidebarMenuItem key={item.href}>
                    <NavigationLink item={item} />
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </nav>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              render={<a href="/profil/" />}
              isActive={isCurrent('/profil/', '/profil/')}
              tooltip="Profil"
            >
              <UserRound aria-hidden="true" />
              <span>Profil</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

export function ApplicationShell({ sidebar, header, children }) {
  return (
    <TooltipProvider>
      <SidebarProvider defaultOpen={readSidebarState()}>
        {sidebar}
        <div className="app-shell-content">
          {header}
          {children}
        </div>
      </SidebarProvider>
    </TooltipProvider>
  );
}
