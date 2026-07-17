import { useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export const navItems = [
  ['/admin/', 'Admin'],
  ['/all_kids', 'Alle Kinder'],
  ['/swp-dashboard/', 'SWPs'],
  ['/auslagerorte-list/', 'Auslagerorte'],
  ['/kitchen', 'Küche'],
  ['https://honey-glue-e51.notion.site/Methoden-eaff0abb8b2a42bfb319c50d5357022c', 'Spiele'],
];

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
    const items = [
      ...(data.kids || []).map(kid => ({
        id: `kid-${kid.id}`,
        href: `/kid_details/${kid.id}`,
        label: `${kid.present ? '' : '❌ '}${kid.full_name}`,
      })),
      ...(data.focuses || []).map(focus => ({ id: `focus-${focus.id}`, href: `/schwerpunkt/${focus.id}`, label: `🚀${focus.name}` })),
      ...(data.places || []).map(place => ({ id: `place-${place.id}`, href: `/auslagerorte/${place.id}`, label: `🏡 ${place.name}` })),
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
  const [open, setOpen] = useState(false);
  return (
    <>
      <header id="headermenu">
        <div id="header-content">
          <div id="logo"><a href="/dashboard/"><Logo /></a></div>
          <div id="headertitle"><h1>{title}</h1></div>
          {authenticated && (
            <>
              <GlobalSearch data={searchData} />
              <nav id="navmenu-container" className="desktop-navbar">
                {navItems.map(([href, label]) => <a key={href} href={href}>{label}</a>)}
              </nav>
              {action && <div id="headerbutton">{action}</div>}
              <button id="menu-button" className="button" type="button" aria-label="Menü öffnen" onClick={() => setOpen(true)}>☰</button>
            </>
          )}
        </div>
      </header>
      {open && (
        <div className="mobile-drawer">
          <nav>
            <button className="closebtn" type="button" onClick={() => setOpen(false)}>×</button>
            <a href="/profil/">Profil</a>
            <a href="/logout/">Ausloggen</a>
            {navItems.map(([href, label]) => <a key={href} href={href}>{label}</a>)}
            <a href="/zugabreise">Zugabreise</a>
            <a href="/zuganreise">Zuganreise</a>
            <a href="/budo_familien/">BuDo-Familien</a>
            <a href="/spezial_familien/">Spezialfamilien</a>
          </nav>
          <button type="button" className="mobile-drawer-backdrop" aria-label="Menü schließen" onClick={() => setOpen(false)} />
        </div>
      )}
    </>
  );
}

export function Card({ title, children, id, initiallyClosed = false, className = '' }) {
  const mobile = typeof window !== 'undefined' && window.matchMedia('(max-width: 759px)').matches;
  const [closed, setClosed] = useState(initiallyClosed || mobile);
  return (
    <section className={`card ${closed ? 'closed-card' : ''} ${className}`} id={id}>
      <div
        className="info-header-container card-toggle"
        role="button"
        tabIndex={0}
        aria-expanded={!closed}
        aria-label={`${title} ${closed ? 'öffnen' : 'schließen'}`}
        onClick={() => setClosed(value => !value)}
        onKeyDown={event => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            setClosed(value => !value);
          }
        }}
      >
        <h2>{title}</h2>
        <span className="icon" aria-hidden="true">
          <span className="open-icon">{closed ? '+' : '−'}</span>
        </span>
      </div>
      <div className="card-info-container" aria-hidden={closed} inert={closed || undefined}>
        <div className="card-info-content">{children}</div>
      </div>
    </section>
  );
}

export function Columns({ children, className = '' }) {
  return <main className={`flex-container ${className}`} id="body-container">{children}</main>;
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

export function SearchTable({ columns, rows, showFilter = false, id = 'kids-table', empty = 'Keine Einträge' }) {
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
      {showFilter && <input className="filter-table" type="search" placeholder="Kinder filtern..." aria-label="Kinder filtern" value={query} onChange={event => setQuery(event.target.value)} />}
      <div className="table-container">
        <table id={id}>
          <thead><tr className="table-header">{columns.map((column, index) => {
            const direction = sort?.key === column.key ? sort.direction : undefined;
            const nextDirection = direction === 'ascending' ? 'absteigend' : direction === 'descending' ? 'aufsteigend' : '';
            return <th key={column.key} className={index === 0 ? 'headcol' : ''} aria-sort={direction}>{column.sortable === false ? column.label : <button className="table-sort-button" type="button" aria-label={`${column.label}${nextDirection ? ` ${nextDirection}` : ''} sortieren`} onClick={() => sortBy(column.key)}><span>{column.label}</span>{direction && <span className="sort-indicator" aria-hidden="true">{direction === 'ascending' ? '▲' : '▼'}</span>}</button>}</th>;
          })}</tr></thead>
          <tbody>
            {visibleRows.map(row => <tr className="table_row" key={row.id}>{columns.map((column, index) => <td className={`${column.className || 'text-cell'} ${index === 0 ? 'headcol' : ''}`} key={column.key}>{column.render ? column.render(row) : row[column.key]}</td>)}</tr>)}
            {!visibleRows.length && <tr><td colSpan={columns.length}>{empty}</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function CsrfInput({ token }) {
  return <input type="hidden" name="csrfmiddlewaretoken" value={token} />;
}

export function RestForm({ target, token, children, className = '', encType, onSuccess, resetOnSuccess = false }) {
  const [errors, setErrors] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const submit = async event => {
    event.preventDefault();
    const form = event.currentTarget;
    setSubmitting(true);
    setErrors([]);
    const body = new FormData(form);
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
        setErrors(result.errors || ['Das Formular konnte nicht gespeichert werden.']);
        return;
      }
      if (onSuccess) {
        await onSuccess(result);
        if (resetOnSuccess) form.reset();
        return;
      }
      window.location.assign(result.redirect || target);
    } catch (error) {
      setErrors([error.message]);
    } finally {
      setSubmitting(false);
    }
  };
  return <form action={target} method="post" encType={encType} className={className} onSubmit={submit}><CsrfInput token={token} />{errors.length > 0 && <ul className="errorlist" role="alert">{errors.map(error => <li key={error}>{error}</li>)}</ul>}{children}{submitting && <p aria-live="polite">Wird gespeichert…</p>}</form>;
}

export function NativeForm({ action = '', method = 'post', token, encType, fields, submit = 'Speichern', children }) {
  const Form = method.toLowerCase() === 'post' ? RestForm : 'form';
  const formProps = method.toLowerCase() === 'post' ? { target: action, token, encType, className: 'form-grid' } : { action, method, encType, className: 'form-grid' };
  return (
    <Form {...formProps}>
      {fields.map(field => {
        if (field.type === 'select') {
          return <label key={field.name}>{field.label}<select name={field.name} defaultValue={field.value ?? ''} multiple={field.multiple}>{field.options?.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>;
        }
        if (field.type === 'textarea') {
          return <label key={field.name}>{field.label}<textarea name={field.name} defaultValue={field.value ?? ''} required={field.required} /></label>;
        }
        if (field.type === 'checkbox') {
          return <label className="checkbox-row" key={field.name}><input type="checkbox" name={field.name} defaultChecked={Boolean(field.value)} />{field.label}</label>;
        }
        return <label key={field.name}>{field.label}<input name={field.name} type={field.type || 'text'} defaultValue={field.type === 'file' ? undefined : field.value ?? ''} required={field.required} multiple={field.multiple} accept={field.accept} min={field.min} step={field.step} /></label>;
      })}
      {children}
      <div className="form-buttons"><input className="button" type="submit" value={submit} /></div>
    </Form>
  );
}

export function MapCard({ places = [] }) {
  const element = useRef(null);
  const locations = useMemo(() => places.map(place => ({
    ...place,
    point: (place.coordinates || '').split(',').map(Number),
  })).filter(place => place.point.length === 2 && place.point.every(Number.isFinite)), [places]);
  useEffect(() => {
    if (!element.current || !locations.length) return undefined;
    const map = L.map(element.current, { scrollWheelZoom: false });
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
  return <Card title="Karte" id="swp-map" className="transparent"><div className="react-map interactive-map" id="map" ref={element}>{!locations.length && <p>Keine Koordinaten verfügbar.</p>}</div></Card>;
}

export function Messages({ items = [] }) {
  if (!items.length) return null;
  return <ul className="messages">{items.map((message, index) => <li className={message.tags} key={`${message.text}-${index}`}>{message.text}</li>)}</ul>;
}
