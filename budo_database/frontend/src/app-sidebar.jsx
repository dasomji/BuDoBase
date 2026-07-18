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
      { label: 'Mörderspielliste', href: '/murdergame' },
      { label: 'Zugabreise', href: '/zugabreise' },
      { label: 'Zuganreise', href: '/zuganreise' },
      { label: 'BuDo-Familien', href: '/budo_familien/' },
      { label: 'Spezialfamilien', href: '/spezial_familien/' },
    ],
  },
  {
    label: 'Einteilungen',
    icon: ListChecks,
    children: [
      { label: 'Happy Cleaning', href: '/happy-cleaning/' },
      { label: 'SWP 1', href: '/swp-einteilung-w1' },
      { label: 'SWP 2', href: '/swp-einteilung-w2' },
    ],
  },
  { label: 'SWPs', href: '/swp-dashboard/', icon: Sparkles },
  { label: 'Auslagerorte', href: '/auslagerorte-list/', icon: MapPinned },
  { label: 'Küche', href: '/kitchen', icon: ChefHat },
  { label: 'Spiele', href: gamesUrl, icon: Gamepad2, external: true },
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

function isCurrent(href) {
  if (/^https?:/.test(href)) return false;
  return normalizedPath(window.location.pathname) === normalizedPath(href);
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
    return <SidebarMenuSubButton render={link} isActive={isCurrent(item.href)} />;
  }
  return (
    <SidebarMenuButton
      render={link}
      isActive={isCurrent(item.href)}
      tooltip={item.label}
    />
  );
}

function NavigationGroup({ item, index }) {
  const [open, setOpen] = useState(true);
  const { state, setOpen: setSidebarOpen } = useSidebar();
  const Icon = item.icon;
  const id = `sidebar-group-${index}`;
  const active = item.children.some(child => isCurrent(child.href));
  const toggle = () => {
    if (state === 'collapsed') {
      setSidebarOpen(true);
      setOpen(true);
      return;
    }
    setOpen(value => !value);
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

export function AppSidebar() {
  return (
    <Sidebar side="left" collapsible="icon" className="app-sidebar">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              render={<a href="/dashboard/" />}
              size="lg"
              tooltip="BuDoBase Dashboard"
              className="sidebar-brand"
            >
              <span className="sidebar-brand-logo"><Logo /></span>
              <span>BuDoBase</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <nav aria-label="Hauptnavigation">
              <SidebarMenu>
                {sidebarItems.map((item, index) => item.children ? (
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
              isActive={isCurrent('/profil/')}
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
      <SidebarProvider>
        {sidebar}
        <div className="app-shell-content">
          {header}
          {children}
        </div>
      </SidebarProvider>
    </TooltipProvider>
  );
}
