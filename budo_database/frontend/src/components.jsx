import { Children, useEffect, useId, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import { SearchIcon } from 'lucide-react';

import { Button, buttonVariants } from '@/components/ui/button';
import { SidebarTrigger } from '@/components/ui/sidebar';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
} from '@/components/ui/table';
import { useErrorToast, useToastManager } from '@/components/ui/toast';
import { useIsMobile } from '@/hooks/use-mobile';

export {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
};

export function findById(items, id) {
  return items.find(item => Number(item.id) === Number(id));
}

export function Logo() {
  return (
    <svg width="28" height="24" viewBox="0 0 28 24" fill="none" aria-label="BuDoBase">
      <path d="M26.6287 20.7499L15.0825.7499A1.25 1.25 0 0 0 14 .125a1.25 1.25 0 0 0-1.0825.625L1.37 20.75H.25v2.5h27.5v-2.5h-1.1213ZM8.5 20.75H4.2575L14 3.875l9.7425 16.875H19.5L14 10.75l-5.5 10Zm5.5-4.8125 2.6462 4.8125h-5.2912L14 15.9375Z" fill="black" />
    </svg>
  );
}

export function GlobalSearch({ data, onNavigate = path => window.location.assign(path) }) {
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const blurTimer = useRef(null);
  const results = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase('de');
    if (!needle) return [];
    const searchIndex = data.search_index || { kids: [], focuses: [], places: [] };
    const items = [
      ...searchIndex.kids.map(kid => ({
        id: `kid-${kid.id}`,
        href: `/kid_details/${kid.id}`,
        label: `${kid.present ? '' : '❌ '}${kid.full_name}`,
      })),
      ...searchIndex.focuses.map(focus => ({ id: `focus-${focus.id}`, href: `/schwerpunkt/${focus.id}`, label: `🚀${focus.name}` })),
      ...searchIndex.places.map(place => ({ id: `place-${place.id}`, href: `/auslagerorte/${place.id}`, label: `🏡 ${place.name}` })),
    ];
    return items.filter(item => item.label.toLocaleLowerCase('de').includes(needle));
  }, [data, query]);
  const open = focused && results.length > 0 && results.length < 20;
  const select = path => {
    if (blurTimer.current) window.clearTimeout(blurTimer.current);
    onNavigate(path);
  };
  const handleKeyDown = event => {
    if (!open) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setSelectedIndex(index => Math.min(index + 1, results.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setSelectedIndex(index => Math.max(index - 1, -1));
    } else if (event.key === 'Enter' && selectedIndex >= 0) {
      event.preventDefault();
      select(results[selectedIndex].href);
    } else if (event.key === 'Escape') {
      setFocused(false);
      setSelectedIndex(-1);
    }
  };
  useEffect(() => () => {
    if (blurTimer.current) window.clearTimeout(blurTimer.current);
  }, []);
  return (
    <div id="headersearch" className="search-filter">
      <label className="sr-only" htmlFor="global-search">Suche</label>
      <input
        id="global-search"
        role="combobox"
        aria-autocomplete="list"
        aria-controls="global-search-results"
        aria-expanded={open}
        aria-activedescendant={selectedIndex >= 0 ? results[selectedIndex]?.id : undefined}
        value={query}
        onChange={event => { setQuery(event.target.value); setSelectedIndex(-1); }}
        onFocus={() => { setFocused(true); setSelectedIndex(-1); }}
        onBlur={() => { blurTimer.current = window.setTimeout(() => { setFocused(false); setSelectedIndex(-1); }, 150); }}
        onKeyDown={handleKeyDown}
        placeholder="Suche..."
      />
      {open && (
        <div id="global-search-results" className="search-results react-search-results" role="listbox" onMouseDown={event => event.preventDefault()}>
          {results.map((result, index) => (
            <a
              id={result.id}
              className={`search-result-link ${index === selectedIndex ? 'selected' : ''}`}
              href={result.href}
              key={result.id}
              role="option"
              aria-selected={index === selectedIndex}
              onClick={event => { event.preventDefault(); select(result.href); }}
            >
              <div className="search-item">{result.label}</div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

export function Header({ title, authenticated, searchData, action }) {
  const [searchOpen, setSearchOpen] = useState(false);
  const headerRef = useRef(null);
  const mobile = useIsMobile();
  useEffect(() => {
    const updateHeaderHeight = () => {
      const height = headerRef.current?.getBoundingClientRect().height || 0;
      document.documentElement.style.setProperty('--app-header-height', `${height}px`);
    };
    updateHeaderHeight();
    window.addEventListener('resize', updateHeaderHeight);
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(updateHeaderHeight);
    if (headerRef.current) observer?.observe(headerRef.current);
    return () => {
      window.removeEventListener('resize', updateHeaderHeight);
      observer?.disconnect();
      document.documentElement.style.removeProperty('--app-header-height');
    };
  }, [searchOpen]);
  const titleNode = <div id="headertitle" key="title"><h1 className="max-[900px]:text-[1.2rem]">{title}</h1></div>;
  const sidebarTrigger = (
    <SidebarTrigger
      key="sidebar-trigger"
      id="menu-button"
      className="max-[900px]:[&_svg]:size-[30px]!"
      size="icon"
      aria-label="Sidebar ein- oder ausklappen"
    />
  );
  const searchToggle = (
    <Button
      key="search-toggle"
      id="search-button"
      type="button"
      variant="ghost"
      size="icon"
      aria-label={searchOpen ? 'Suche schließen' : 'Suche öffnen'}
      aria-controls="headersearch"
      aria-expanded={searchOpen}
      onClick={() => setSearchOpen(open => !open)}
    >
      <SearchIcon className="size-[30px]" aria-hidden="true" />
    </Button>
  );
  const search = <GlobalSearch key="search" data={searchData} />;
  const actionNode = action ? <div id="headerbutton" key="action">{action}</div> : null;
  const authenticatedContent = mobile
    ? [titleNode, actionNode, searchToggle, sidebarTrigger, search]
    : [sidebarTrigger, titleNode, search, actionNode];

  return (
    <header id="headermenu" ref={headerRef}>
      <div
        id="header-content"
        className={[
          searchOpen ? 'search-open' : '',
          action ? 'has-action' : '',
        ].filter(Boolean).join(' ')}
      >
        {authenticated
          ? authenticatedContent
          : [<div id="logo" key="logo"><a href="/dashboard/"><Logo /></a></div>, titleNode]}
      </div>
    </header>
  );
}

export function Card({
  title,
  children,
  id,
  initiallyClosed = false,
  className = '',
  headerAction = null,
  actions = null,
  showToggleIcon,
  as: Container = 'section',
  headingLevel = 2,
  expanded,
  onExpandedChange,
}) {
  const mobile = useIsMobile();
  const contentId = useId();
  const [internallyClosed, setInternallyClosed] = useState(initiallyClosed || mobile);
  const controlled = expanded !== undefined;
  const closed = controlled ? !expanded : internallyClosed;
  const toggleIconVisible = showToggleIcon ?? className.split(/\s+/).includes('transparent');
  useEffect(() => {
    if (!controlled) setInternallyClosed(initiallyClosed || mobile);
  }, [controlled, initiallyClosed, mobile]);
  const Heading = `h${headingLevel}`;
  const toggle = () => {
    if (controlled) onExpandedChange?.(!expanded);
    else setInternallyClosed(value => !value);
  };
  return (
    <Container className={`card ${closed ? 'closed-card' : ''} ${className}`} id={id}>
      <div
        className="info-header-container card-toggle"
        role="button"
        tabIndex={0}
        aria-expanded={!closed}
        aria-controls={contentId}
        aria-label={`${title} ${closed ? 'öffnen' : 'schließen'}`}
        onClick={toggle}
        onKeyDown={event => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggle();
          }
        }}
      >
        <Heading>{title}</Heading>
        {headerAction && (
          <span
            className="card-header-action"
            onClick={event => event.stopPropagation()}
            onKeyDown={event => event.stopPropagation()}
          >
            {headerAction}
          </span>
        )}
        {toggleIconVisible && (
          <span className="icon" aria-hidden="true">{closed ? '+' : '−'}</span>
        )}
      </div>
      <div className="card-info-container" id={contentId} aria-hidden={closed} inert={closed || undefined}>
        <div className="card-info-content">
          {children}
          {actions && (
            <footer className="flex flex-wrap justify-end gap-2 pt-3 print:hidden" data-slot="card-actions">
              {actions}
            </footer>
          )}
        </div>
      </div>
    </Container>
  );
}

export function Columns({ children, className = '' }) {
  return <main className={className} id="body-container">{children}</main>;
}

export function ConfirmationDialog({
  open,
  title,
  confirmLabel,
  confirmAriaLabel,
  cancelLabel,
  onConfirm,
  onCancel,
  destructive = false,
  initialFocusRef,
  role = 'dialog',
  children,
}) {
  const titleId = useId();
  const cancelRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    (initialFocusRef?.current || cancelRef.current)?.focus();
    const cancelOnEscape = event => {
      if (event.key === 'Escape') onCancel();
    };
    document.addEventListener('keydown', cancelOnEscape);
    return () => document.removeEventListener('keydown', cancelOnEscape);
  }, [initialFocusRef, onCancel, open]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-[var(--z-modal)] grid place-items-center bg-black/45 p-6"
      onClick={event => { if (event.target === event.currentTarget) onCancel(); }}
    >
      <section
        className="card w-full max-w-[30rem] bg-surface-solid p-6"
        role={role}
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <h2 id={titleId}>{title}</h2>
        {children}
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <Button ref={cancelRef} type="button" variant="secondary" onClick={onCancel}>{cancelLabel}</Button>
          <Button
            type="button"
            variant={destructive ? 'destructive' : 'default'}
            disabled={!onConfirm}
            aria-label={confirmAriaLabel}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </section>
    </div>
  );
}

const responsiveCardMinWidthRem = 20;
const responsiveCardGapRem = 1;

function responsiveCardColumnCount(width) {
  const rootFontSize = typeof window === 'undefined'
    ? 16
    : Number.parseFloat(window.getComputedStyle(document.documentElement).fontSize) || 16;
  const minimumCardWidth = responsiveCardMinWidthRem * rootFontSize;
  const gap = responsiveCardGapRem * rootFontSize;
  if (width >= minimumCardWidth * 3 + gap * 2) return 3;
  if (width >= minimumCardWidth * 2 + gap) return 2;
  return 1;
}

function IndependentResponsiveCardGrid({ children, className, maxColumns }) {
  const gridRef = useRef(null);
  const [columnCount, setColumnCount] = useState(1);

  useEffect(() => {
    const grid = gridRef.current;
    if (!grid) return undefined;
    const updateColumnCount = width => setColumnCount(Math.min(maxColumns, responsiveCardColumnCount(width)));
    updateColumnCount(grid.getBoundingClientRect().width);
    if (typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(entries => {
      const entry = entries.find(item => item.target === grid);
      if (entry) updateColumnCount(entry.contentRect.width);
    });
    observer.observe(grid);
    return () => observer.disconnect();
  }, [maxColumns]);

  const cardsByColumn = Array.from({ length: columnCount }, () => []);
  Children.toArray(children).forEach((child, index) => {
    cardsByColumn[index % columnCount].push(child);
  });

  return (
    <Columns className={`responsive-card-grid grid min-w-0 grid-cols-1 ${className}`}>
      <div className={`grid min-w-0 grid-cols-1 items-start gap-4 ${maxColumns >= 2 ? '@[41rem]:grid-cols-2' : ''} ${maxColumns >= 3 ? '@[62rem]:grid-cols-3' : ''}`} ref={gridRef}>
        {cardsByColumn.map((cards, index) => (
          <div className="flex min-w-0 flex-col gap-4" data-card-column={index + 1} key={index}>
            {cards}
          </div>
        ))}
      </div>
    </Columns>
  );
}

export function ResponsiveCardGrid({ children, className = '', independentColumns = false, maxColumns = 3 }) {
  if (independentColumns) {
    return <IndependentResponsiveCardGrid className={className} maxColumns={maxColumns}>{children}</IndependentResponsiveCardGrid>;
  }
  return (
    <Columns className={`grid min-w-0 grid-cols-1 items-start gap-4 min-[901px]:grid-cols-3 ${className}`}>
      {children}
    </Columns>
  );
}

export function Column({ children, id, className = '' }) {
  return <div className={`detail-column ${className}`} id={id}>{children}</div>;
}

export function FieldList({ items }) {
  return <>{items.filter(([, value]) => value !== null && value !== undefined && value !== '').map(([label, value]) => <p key={label}><span className="label">{label}</span>: {value}</p>)}</>;
}

function tableSortValue(column, row) {
  if (column.sortValue) return column.sortValue(row);
  if (row[column.key] !== null && row[column.key] !== undefined) return row[column.key];
  if (column.key === 'name') return row.full_name ?? row.filterText ?? '';
  return '';
}

function compareTableValues(left, right) {
  if (typeof left === 'boolean' || typeof right === 'boolean') return Number(left) - Number(right);
  const leftText = String(left ?? '').trim();
  const rightText = String(right ?? '').trim();
  const leftNumber = Number(leftText);
  const rightNumber = Number(rightText);
  if (leftText && rightText && Number.isFinite(leftNumber) && Number.isFinite(rightNumber)) return leftNumber - rightNumber;
  return leftText.localeCompare(rightText, 'de', { numeric: true, sensitivity: 'base' });
}

export function DataTable({
  columns,
  rows,
  showFilter = false,
  id,
  empty = 'Keine Einträge',
  beforeFilter = null,
  stickyHeader = false,
  stickyFirstColumn = false,
  verticalScroll = false,
}) {
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState(null);
  const visibleRows = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase('de');
    const filtered = needle
      ? rows.filter(row => String(row.filterText ?? row.full_name ?? row.name ?? '').toLocaleLowerCase('de').includes(needle))
      : rows;
    if (!sort) return filtered;
    const column = columns.find(item => item.key === sort.key);
    if (!column) return filtered;
    const direction = sort.direction === 'ascending' ? 1 : -1;
    return filtered
      .map((row, index) => ({ row, index }))
      .sort((left, right) => direction * compareTableValues(tableSortValue(column, left.row), tableSortValue(column, right.row)) || left.index - right.index)
      .map(item => item.row);
  }, [columns, query, rows, sort]);
  const sortBy = key => setSort(current => ({
    key,
    direction: current?.key === key && current.direction === 'ascending' ? 'descending' : 'ascending',
  }));
  return (
    <>
      {(beforeFilter || showFilter) && (
        <div
          className={`table-controls${beforeFilter ? ' max-[900px]:sticky max-[900px]:top-[var(--app-header-height,0px)] max-[900px]:z-5 max-[900px]:flex-none' : ''}`}
          data-slot={beforeFilter ? 'table-sticky-controls' : undefined}
        >
          {beforeFilter}
          {showFilter && <input className="filter-table" type="search" placeholder="Kinder filtern..." aria-label="Kinder filtern" value={query} onChange={event => setQuery(event.target.value)} />}
        </div>
      )}
      <TableScroll
        stickyHeader={stickyHeader}
        stickyFirstColumn={stickyFirstColumn}
        verticalScroll={verticalScroll}
      >
        <Table id={id}>
          <TableHeader><TableRow>{columns.map(column => {
            const direction = sort?.key === column.key ? sort.direction : undefined;
            const nextDirection = direction === 'ascending' ? 'absteigend' : direction === 'descending' ? 'aufsteigend' : '';
            return <TableHead className={column.className} key={column.key} scope="col" data-priority={column.priority} aria-sort={direction}>{column.sortable === false ? column.label : <button className="table-sort-button" type="button" aria-label={`${column.label}${nextDirection ? ` ${nextDirection}` : ''} sortieren`} onClick={() => sortBy(column.key)}><span>{column.label}</span>{direction && <span className="sort-indicator" aria-hidden="true">{direction === 'ascending' ? '▲' : '▼'}</span>}</button>}</TableHead>;
          })}</TableRow></TableHeader>
          <TableBody>
            {visibleRows.map(row => <TableRow key={row.id}>{columns.map(column => <TableCell className={column.className} data-priority={column.priority} key={column.key}>{column.render ? column.render(row) : row[column.key]}</TableCell>)}</TableRow>)}
            {!visibleRows.length && <TableRow><TableCell colSpan={columns.length}>{empty}</TableCell></TableRow>}
          </TableBody>
        </Table>
      </TableScroll>
    </>
  );
}

export function CsrfInput({ token }) {
  return <input type="hidden" name="csrfmiddlewaretoken" value={token} />;
}

export function RestForm({ target, token, children, className = '', encType, onSuccess, resetOnSuccess = false }) {
  const [submitting, setSubmitting] = useState(false);
  const showError = useErrorToast();
  const submittingRef = useRef(false);
  const submit = async event => {
    event.preventDefault();
    if (submittingRef.current) return;
    submittingRef.current = true;
    const form = event.currentTarget;
    setSubmitting(true);
    const body = new FormData(form);
    form.querySelectorAll('input[type="file"][multiple][name]').forEach(input => {
      body.delete(input.name);
      Array.from(input.files || []).forEach(file => body.append(input.name, file));
    });
    const submitter = event.nativeEvent.submitter;
    if (submitter?.name) body.set(submitter.name, submitter.value);
    body.set('_target', target);
    try {
      const response = await fetch('/api/form-submit/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': token },
        body,
      });
      const result = await response.json();
      if (!response.ok || !result.ok) {
        showError((result.errors || ['Das Formular konnte nicht gespeichert werden.']).join(' '));
        return;
      }
      if (onSuccess) {
        await onSuccess(result);
        if (resetOnSuccess) form.reset();
        return;
      }
      window.location.assign(result.redirect || target);
    } catch (error) {
      showError(error.message);
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  };
  return <form action={target} method="post" encType={encType} className={className} onSubmit={submit} aria-busy={submitting}><CsrfInput token={token} />{typeof children === 'function' ? children({ submitting }) : children}{submitting && <p aria-live="polite">Wird gespeichert…</p>}</form>;
}

export function NativeForm({ action = '', method = 'post', token, encType, fields, submit = 'Speichern', children }) {
  const contents = (submitting = false) => (
    <>
      {fields.map(field => {
        if (field.render) {
          return <div key={field.name}>{field.render()}</div>;
        }
        if (field.type === 'checkbox-group') {
          const selected = new Set((field.value || []).map(String));
          return <fieldset className="checkbox-group" key={field.name}><legend>{field.label}</legend><div className="checkbox-group-options">{field.options?.map(option => <label className="checkbox-row" key={option.value}><input type="checkbox" name={field.name} value={option.value} defaultChecked={selected.has(String(option.value))} />{option.label}</label>)}</div></fieldset>;
        }
        if (field.type === 'select') {
          return <label key={field.name}>{field.label}<select name={field.name} defaultValue={field.value ?? ''} multiple={field.multiple}>{field.options?.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>;
        }
        if (field.type === 'textarea') {
          return <label key={field.name}>{field.label}<textarea name={field.name} defaultValue={field.value ?? ''} required={field.required} /></label>;
        }
        if (field.type === 'checkbox') {
          if (field.groupLabel) return <fieldset className="checkbox-group" key={field.name}><legend>{field.groupLabel}</legend><label className="checkbox-row"><input type="checkbox" name={field.name} defaultChecked={Boolean(field.value)} />{field.label}</label></fieldset>;
          return <label className="checkbox-row" key={field.name}><input type="checkbox" name={field.name} defaultChecked={Boolean(field.value)} />{field.label}</label>;
        }
        return <label key={field.name}>{field.label}<input name={field.name} type={field.type || 'text'} defaultValue={field.type === 'file' ? undefined : field.value ?? ''} required={field.required} multiple={field.multiple} accept={field.accept} min={field.min} step={field.step} /></label>;
      })}
      <div className="form-buttons">{children}<input className={buttonVariants()} type="submit" value={submit} disabled={submitting} /></div>
    </>
  );
  if (method.toLowerCase() === 'post') {
    return <RestForm target={action} token={token} encType={encType} className="form-grid">{({ submitting }) => contents(submitting)}</RestForm>;
  }
  return <form action={action} method={method} encType={encType} className="form-grid">{contents()}</form>;
}

export function MapCard({ places = [], headerAction = null }) {
  const element = useRef(null);
  const locations = useMemo(() => places.map(place => ({
    ...place,
    point: (place.coordinates || '').split(',').map(Number),
  })).filter(place => place.point.length === 2 && place.point.every(Number.isFinite)), [places]);
  useEffect(() => {
    if (!element.current || !locations.length) return undefined;
    const map = L.map(element.current, { scrollWheelZoom: true, touchZoom: true });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      subdomains: 'abcd',
      attribution: '© OpenStreetMap contributors © CARTO',
    }).addTo(map);
    const markers = locations.map(location => L.marker(location.point, {
      icon: L.divIcon({
        className: 'leaflet-text',
        html: `<b><a href="${location.href || `/auslagerorte/${location.id}/`}">📍${location.name}</a></b>`,
      }),
    }).addTo(map));
    const bounds = L.featureGroup(markers).getBounds();
    map.fitBounds(bounds, { paddingBottomRight: [150, 0], maxZoom: 12 });
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(element.current);
    return () => { observer.disconnect(); map.remove(); };
  }, [locations]);
  return <Card title="Karte" id="swp-map" className="transparent" headerAction={headerAction}><div className="react-map interactive-map" id="map" ref={element}>{!locations.length && <p>Keine Koordinaten verfügbar.</p>}</div></Card>;
}

const MESSAGE_LEVELS = ['error', 'warning', 'success', 'info'];

const messageLevel = tags => {
  const tagSet = new Set((tags || '').split(/\s+/));
  return MESSAGE_LEVELS.find(level => tagSet.has(level)) || 'info';
};

export function Messages({ items = [] }) {
  const toastManager = useToastManager();
  const published = useRef(new Set());

  useEffect(() => {
    items.forEach((message, index) => {
      const key = `${message.tags || ''}\u0000${message.text}\u0000${index}`;
      if (published.current.has(key)) return;
      published.current.add(key);
      const type = messageLevel(message.tags);
      toastManager.add({
        description: message.text,
        type,
        priority: type === 'error' ? 'high' : 'low',
      });
    });
  }, [items, toastManager]);

  return null;
}
