import { Card, Column, Columns, NativeForm, SearchTable } from '../components';
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
  return <Columns><Column id="single-column"><Card title={`${checkout ? 'Check-Out' : 'Check-In'}: ${kid.full_name}`}><p style={{ color: checkout ? 'green' : 'red' }}>{kid.full_name} ist {checkout ? 'anwesend.' : 'noch nicht eingecheckt!'}</p>{checkout && <><p>Wir hatten vom Kind folgendes:</p><ul>{kid.e_card && <li>E-Card</li>}{kid.id_card && <li>Ausweis</li>}{kid.consent && <li>Einverständniserklärung</li>}{kid.pocket_money > 0 && <li>Taschengeld: {money(kid.pocket_money)}</li>}</ul></>}<NativeForm token={data.csrf_token} action={`/${checkout ? 'check_out' : 'check_in'}/${kid.id}`} fields={fields} submit={checkout ? 'Auschecken' : 'Einchecken'} /></Card></Column></Columns>;
}

export function TrainPage({ data, departure, mutate }) {
  const source = departure ? [...data.kids].sort((a, b) => Number(b.train_departure) - Number(a.train_departure)) : data.kids.filter(kid => kid.train_arrival);
  const rows = source.map(kid => ({ ...kid, filterText: kid.full_name }));
  const columns = departure ? [
    { key: 'name', label: 'Name', render: linkKid },
    { key: 'train_departure', label: `Zugabreise: ${data.totals.train_departure}`, render: row => <button type="button" className="zug-switch" onClick={() => mutate('/toggle_zug_abreise/', { id: row.id }, false)}>{yesNo(row.train_departure)}</button> },
    { key: 'departure_note', label: 'Abreise-Notiz', render: row => <>{row.departure_note} <button type="button" onClick={() => { const value = window.prompt('Abreise-Notiz', row.departure_note || ''); if (value !== null) mutate('/update_notiz_abreise/', { id: row.id, notiz_abreise: value }); }}>✏️</button></> },
    { key: 'youth_ticket', label: 'Top-Jugendticket', render: row => yesNo(row.youth_ticket) },
    { key: 'age', label: 'Alter' },
    { key: 'registrant_name', label: 'Anmelder' },
    { key: 'registrant_phone', label: 'Anmelder Tel', render: row => <a href={`tel:${row.registrant_phone}`}>{row.registrant_phone}</a> },
    { key: 'siblings', label: 'Geschwister', render: row => displayOrPlaceholder(row.siblings) },
  ] : [
    { key: 'name', label: `Gesamt: ${data.totals.train_arrival}`, render: linkKid },
    { key: 'train_arrival', label: 'Zuganreise', render: row => yesNo(row.train_arrival) },
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
  return <><div className="print_only"><h1>{departure ? 'Zugabreise' : 'Zuganreise'}</h1>{printSummary}</div><main className="table-only" id="body-container"><SearchTable columns={columns} rows={rows} showFilter /></main></>;
}

const selectedKidTitle = (route, data) => data.kid?.full_name || route.title;

export const attendanceRoutes = [
  {
    pattern: /^\/zugabreise$/,
    page: 'train-departure',
    title: 'Alle Kinder',
    domain: 'attendance',
    readContractKey: 'train-departure',
    focusedReadContract: true,
    render: ({ data, mutate }) => <TrainPage data={data} departure mutate={mutate} />,
  },
  {
    pattern: /^\/zuganreise$/,
    page: 'train-arrival',
    title: 'Zuganreise',
    domain: 'attendance',
    readContractKey: 'train-arrival',
    focusedReadContract: true,
    render: ({ data, mutate }) => <TrainPage data={data} mutate={mutate} />,
  },
  {
    pattern: /^\/check_in\/(\d+)$/,
    page: 'check-in',
    title: 'Check-In',
    domain: 'attendance',
    readContractKey: 'check-in',
    focusedReadContract: true,
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
    focusedReadContract: true,
    params: match => ({ id: match[1] }),
    resolveTitle: selectedKidTitle,
    render: ({ data }) => <CheckPage data={data} checkout />,
  },
];
