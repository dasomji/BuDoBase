import { useState } from 'react';
import { Dialog } from '@base-ui/react/dialog';
import {
  ArrowRightLeft,
  BookOpenText,
  ChefHat,
  ChevronRight,
  ClipboardList,
  Gamepad2,
  ListChecks,
  MapPinned,
  Settings,
  ShieldCheck,
  Sparkles,
  UserRound,
  UsersRound,
} from 'lucide-react';

import { Logo } from './components';
import { Button } from '@/components/ui/button';
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
  { label: 'Dokumentation', href: '/dokumentation/', icon: BookOpenText },
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
    ],
  },
  {
    label: 'Schwerpunkte',
    icon: ListChecks,
    children: [
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
  { label: 'Team & Turnus', href: '/teams/', icon: UsersRound },
  {
    label: 'Orgi',
    icon: Settings,
    children: [
      { label: 'Taschengeld', href: '/taschengeld/' },
      { label: 'Serienbrief', href: '/serienbrief' },
      { label: 'Aufenthaltsdoku', href: '/download-updated-excel/' },
    ],
  },
  {
    label: 'Admin',
    icon: ShieldCheck,
    children: [
      { label: 'Django', href: '/admin/' },
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
        children: [...item.children, ...eventItems],
      };
    }
    if (item.label === 'Admin') {
      if (!permissions?.is_superuser) return null;
      const adminItems = [];
      if (permissions?.change_tags) {
        adminItems.push({ label: 'Auslagerort-Tags', href: '/auslagerorte/tags/' });
      }
      if (permissions?.view_auditevent) {
        adminItems.push({ label: 'Audit-Log', href: '/audit/' });
      }
      if (permissions?.admin_settings) {
        adminItems.push({ label: 'Einstellungen', href: '/settings/' });
      }
      return {
        ...item,
        children: [
          ...adminItems,
          ...item.children,
        ],
      };
    }
    return item;
  }).filter(Boolean);
}

function TurnusSwitcher({ selection, onChange, busy }) {
  const [open, setOpen] = useState(false);
  const options = selection.options || [];
  const selected = options.find(option => Number(option.id) === Number(selection.selected_id));
  const selectTurnus = option => {
    setOpen(false);
    if (Number(option.id) !== Number(selection.selected_id)) {
      onChange?.(Number(option.id));
    }
  };

  return (
    <div className="px-4 py-2 group-data-[collapsible=icon]:hidden">
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <div className="flex min-w-0 items-center gap-1">
          <span className="sr-only">Aktiver Turnus:</span>
          <span
            className="min-w-0 truncate text-sm font-semibold"
            data-slot="active-turnus"
            title={selected?.label}
          >
            {selected?.label || 'Nicht ausgewählt'}
          </span>
          <Dialog.Trigger
            render={(
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label="Turnus wechseln"
                aria-busy={busy}
                title="Turnus wechseln"
                disabled={busy}
              />
            )}
            disabled={busy}
          >
            <ArrowRightLeft aria-hidden="true" />
          </Dialog.Trigger>
        </div>
        <Dialog.Portal>
          <Dialog.Backdrop className="fixed inset-0 z-[var(--z-modal)] bg-black/45" />
          <Dialog.Viewport className="fixed inset-0 z-[var(--z-modal)] grid place-items-center overflow-y-auto p-4">
            <Dialog.Popup className="card grid max-h-[calc(100dvh-2rem)] w-full max-w-md gap-4 overflow-y-auto bg-surface-solid p-5">
              <div>
                <Dialog.Title className="text-xl font-semibold">Turnus wechseln</Dialog.Title>
                <Dialog.Description className="text-sm text-muted-foreground">
                  Wähle den Turnus aus, mit dem du weiterarbeiten möchtest.
                </Dialog.Description>
              </div>
              <div className="grid gap-2">
                {options.map(option => {
                  const current = Number(option.id) === Number(selection.selected_id);
                  return (
                    <Button
                      className="h-auto w-full justify-between py-2 text-left whitespace-normal"
                      variant={current ? 'outline' : 'secondary'}
                      type="button"
                      aria-current={current ? 'true' : undefined}
                      disabled={busy}
                      onClick={() => selectTurnus(option)}
                      key={option.id}
                    >
                      <span>{option.label}</span>
                      {current && <span className="text-xs text-muted-foreground">Aktiv</span>}
                    </Button>
                  );
                })}
              </div>
              <div className="flex justify-end">
                <Dialog.Close render={<Button type="button" variant="secondary" />}>
                  Abbrechen
                </Dialog.Close>
              </div>
            </Dialog.Popup>
          </Dialog.Viewport>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

export function AppSidebar({
  happyCleaningEvents = [],
  permissions,
  turnusSelection,
  onTurnusChange,
  turnusSwitching = false,
  withoutTurnus = false,
}) {
  const availableItems = withDynamicNavEntries(happyCleaningEvents, permissions);
  const items = withoutTurnus
    ? availableItems.filter(item => item.label === 'Team & Turnus')
    : availableItems;
  const options = turnusSelection?.options || [];
  return (
    <Sidebar side="left" collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              render={<a href={withoutTurnus ? '/teams/' : '/dashboard/'} />}
              tooltip={withoutTurnus ? 'Team & Turnus' : 'BuDoBase Dashboard'}
              className="sidebar-brand"
            >
              <Logo />
              <span>BuDoBase</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        {options.length > 0 && (
          <TurnusSwitcher
            selection={turnusSelection}
            onChange={onTurnusChange}
            busy={turnusSwitching}
          />
        )}
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
