import { useRef } from 'react';
import { Printer } from 'lucide-react';

import { Card, Column, Columns, DataTable, NativeForm } from '../components';
import { Button } from '../components/ui/button';
import { useErrorToast, useSuccessToast } from '../components/ui/toast';
import { displayOrPlaceholder, linkKid, money, NotFoundPage, yesNo } from './shared';

export function CheckPage({ data, checkout = false }) {
  const kid = data.kid;
  if (!kid) return <NotFoundPage />;
  const pocketMoneyBalance = Number(kid.pocket_money || 0);
  const checkoutMoneyLabel = pocketMoneyBalance >= 0
    ? `Taschengeld zurückgegeben (aktuell ${money(pocketMoneyBalance)})`
    : `Taschengeld eingezahlt (schuldet aktuell: ${money(Math.abs(pocketMoneyBalance))})`;
  const fields = checkout ? [
    { name: 'early_abreise_date', label: 'Abreisedatum', type: 'date', value: new Date().toISOString().slice(0, 10), required: true },
    { name: 'notiz', label: 'Notiz' },
    { name: 'amount', label: checkoutMoneyLabel, type: 'number', min: '0', step: '0.01', value: pocketMoneyBalance > 0 ? pocketMoneyBalance : 0 },
  ] : [
    { name: 'check_in_date', label: 'Check-in Datum', type: 'date', value: new Date().toISOString().slice(0, 10), required: true },
    { name: 'ausweis', label: 'Ausweis', type: 'checkbox', value: kid.id_card },
    { name: 'e_card', label: 'E-Card', type: 'checkbox', value: kid.e_card },
    { name: 'einverstaendnis_erklaerung', label: 'Einverständniserklärung', type: 'checkbox', value: kid.consent },
    { name: 'notiz', label: 'Notiz' },
    { name: 'amount', label: 'Taschengeld', type: 'number', min: '0', step: '0.01' },
  ];
  return <Columns><Column id="single-column"><Card title={`${checkout ? 'Check-Out' : 'Check-In'}: ${kid.full_name}`}><p className={checkout ? 'text-green-700' : 'text-red-700'}>{kid.full_name} ist {checkout ? 'anwesend.' : 'noch nicht eingecheckt!'}</p>{checkout && <><p>Wir hatten vom Kind folgendes:</p><ul>{kid.e_card && <li>E-Card</li>}{kid.id_card && <li>Ausweis</li>}{kid.consent && <li>Einverständniserklärung</li>}{kid.pocket_money > 0 && <li>Taschengeld: {money(kid.pocket_money)}</li>}</ul></>}<NativeForm token={data.csrf_token} action={`/${checkout ? 'check_out' : 'check_in'}/${kid.id}`} fields={fields} submit={checkout ? 'Auschecken' : 'Einchecken'} /></Card></Column></Columns>;
}

function TrainSegmentedControl({ selected, kidName, label, onChange }) {
  return (
    <div
      aria-label={`${label} für ${kidName}`}
      className="isolate inline-flex rounded-lg"
      role="group"
    >
      {[true, false].map((value, index) => {
        const active = Boolean(selected) === value;
        return (
          <Button
            aria-pressed={active}
            className={`${index === 0 ? 'rounded-r-none' : '-ml-px rounded-l-none'} border-border focus-visible:z-10`}
            key={String(value)}
            type="button"
            variant={active ? 'secondary' : 'outline'}
            onClick={() => {
              if (!active) onChange(value);
            }}
          >
            {value ? 'Ja' : 'Nein'}
          </Button>
        );
      })}
    </div>
  );
}

export function TrainPage({ data, departure, mutate }) {
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();
  const transportLabel = departure ? 'Zugabreise' : 'Zuganreise';
  const save = async (...args) => {
    try {
      await mutate(...args);
      showSuccess(`${transportLabel} wurde gespeichert.`);
    } catch {
      showError(`Die ${transportLabel} konnte nicht gespeichert werden.`);
    }
  };
  const departureOrder = useRef(null);
  // Freeze the initial status-sorted order for this page visit so refreshed values do not move rows.
  if (departure && departureOrder.current === null) {
    departureOrder.current = [...data.kids]
      .sort((a, b) => Number(b.train_departure) - Number(a.train_departure))
      .map(kid => kid.id);
  }
  const departurePosition = new Map((departureOrder.current || []).map((id, index) => [id, index]));
  const source = departure
    ? [...data.kids].sort((a, b) => (departurePosition.get(a.id) ?? Number.MAX_SAFE_INTEGER) - (departurePosition.get(b.id) ?? Number.MAX_SAFE_INTEGER))
    : data.kids;
  const rows = source.map(kid => ({ ...kid, filterText: kid.full_name }));
  const columns = departure ? [
    { key: 'name', label: 'Name', render: linkKid },
    {
      key: 'train_departure',
      label: `Zugabreise: ${data.totals.train_departure}`,
      render: row => (
        <TrainSegmentedControl
          selected={row.train_departure}
          kidName={row.full_name}
          label="Zugabreise"
          onChange={() => save('/toggle_zug_abreise/', { id: row.id }, false)}
        />
      ),
    },
    { key: 'departure_note', label: 'Abreise-Notiz', render: row => <>{row.departure_note} <Button type="button" variant="ghost" size="icon-sm" aria-label={`Abreise-Notiz von ${row.full_name} bearbeiten`} onClick={() => { const value = window.prompt('Abreise-Notiz', row.departure_note || ''); if (value !== null) save('/update_notiz_abreise/', { id: row.id, notiz_abreise: value }); }}>✏️</Button></> },
    { key: 'youth_ticket', label: 'Top-Jugendticket', render: row => yesNo(row.youth_ticket) },
    { key: 'age', label: 'Alter' },
    { key: 'registrant_name', label: 'Anmelder' },
    { key: 'registrant_phone', label: 'Anmelder Tel', render: row => <a href={`tel:${row.registrant_phone}`}>{row.registrant_phone}</a> },
    { key: 'siblings', label: 'Geschwister', render: row => displayOrPlaceholder(row.siblings) },
  ] : [
    { key: 'name', label: 'Name', render: linkKid },
    {
      key: 'train_arrival',
      label: `Zuganreise: ${data.totals.train_arrival}`,
      render: row => (
        <TrainSegmentedControl
          selected={row.train_arrival}
          kidName={row.full_name}
          label="Zuganreise"
          onChange={() => save('/toggle_zug_anreise/', { id: row.id }, false)}
        />
      ),
    },
    { key: 'youth_ticket', label: 'Top-Jt', render: row => yesNo(row.youth_ticket) },
    { key: 'age', label: 'Alter' },
    { key: 'registrant_name', label: 'Anmelder' },
    { key: 'registrant_phone', label: 'Anmelder Tel', render: row => <a href={`tel:${row.registrant_phone}`}>{row.registrant_phone}</a> },
    { key: 'siblings', label: 'Geschwister', render: row => displayOrPlaceholder(row.siblings) },
  ];
  const printSummary = departure
    ? <p>Kinder: {rows.length}</p>
    : <>
      <p>Kinder, die ihr abholt: {data.totals.train_arrival}</p>
      <p>Kinder mit Top-Jugendticket: {data.totals.with_youth_ticket}</p>
      <p>Kinder ohne Top-Jugendticket: {data.totals.without_youth_ticket}</p>
    </>;
  const arrivalPrintColumns = columns.map(column => ({
    ...column,
    sortable: false,
    ...(column.key === 'train_arrival' ? { render: row => yesNo(row.train_arrival) } : {}),
  }));
  const arrivalPrintRows = rows.filter(row => row.train_arrival);
  return <>
    {departure && <div className="hidden p-8 text-xs print:block"><h1>Zugabreise</h1>{printSummary}</div>}
    <main className={`table-only${departure ? '' : ' print:hidden'}`} id="body-container"><DataTable columns={columns} rows={rows} showFilter stickyFirstColumn /></main>
    {!departure && (
      <section aria-hidden="true" aria-label="Zuganreise-Druckliste" className="hidden print:block">
        <div className="p-8 text-xs"><h1>Zuganreise</h1>{printSummary}</div>
        <DataTable columns={arrivalPrintColumns} rows={arrivalPrintRows} stickyFirstColumn />
      </section>
    )}
  </>;
}

const selectedKidTitle = (route, data) => data.kid?.full_name || route.title;

export const attendanceRoutes = [
  {
    pattern: /^\/zugabreise$/,
    page: 'train-departure',
    title: 'Zugabreise',
    domain: 'attendance',
    readContractKey: 'train-departure',
    headerAction: () => (
      <Button
        aria-label="Drucken"
        className="mobile-icon-action"
        size="responsive-icon"
        type="button"
        onClick={() => window.print()}
      >
        <span className="desktop-action-label">Drucken</span>
        <Printer className="mobile-action-label" aria-hidden="true" />
      </Button>
    ),
    render: ({ data, mutate }) => <TrainPage data={data} departure mutate={mutate} />,
  },
  {
    pattern: /^\/zuganreise$/,
    page: 'train-arrival',
    title: 'Zuganreise',
    domain: 'attendance',
    readContractKey: 'train-arrival',
    headerAction: () => (
      <Button
        aria-label="Drucken"
        className="mobile-icon-action"
        size="responsive-icon"
        type="button"
        onClick={() => window.print()}
      >
        <span className="desktop-action-label">Drucken</span>
        <Printer className="mobile-action-label" aria-hidden="true" />
      </Button>
    ),
    render: ({ data, mutate }) => <TrainPage data={data} mutate={mutate} />,
  },
  {
    pattern: /^\/check_in\/(\d+)$/,
    page: 'check-in',
    title: 'Check-In',
    domain: 'attendance',
    readContractKey: 'check-in',
    params: match => ({ id: match[1] }),
    resolveTitle: selectedKidTitle,
    render: ({ data }) => <CheckPage data={data} />,
  },
  {
    pattern: /^\/check_out\/(\d+)$/,
    page: 'check-out',
    title: 'Check-Out',
    domain: 'attendance',
    readContractKey: 'check-out',
    params: match => ({ id: match[1] }),
    resolveTitle: selectedKidTitle,
    render: ({ data }) => <CheckPage data={data} checkout />,
  },
];
