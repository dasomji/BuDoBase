import { Card, Column, Columns, findById, NativeForm, SearchTable } from '../components';
import { formatGermanDate } from './shared';

export function TurnusUploadPage({ data, id }) {
  const turnus = id ? findById(data.turnuses, id) : null;
  return <Columns><Column id="single-column"><Card title={turnus ? `Excel-Datei hochladen für Turnus ${turnus.number}` : 'Turnis'}><NativeForm token={data.csrf_token} action={turnus ? `/upload_excel/${turnus.id}/` : '/upload/'} encType="multipart/form-data" fields={[{ name: 'turnus_nr', label: 'Turnus Nummer', type: 'number', value: turnus?.number, required: true }, { name: 'turnus_beginn', label: 'Beginn des Turnus', type: 'date', value: turnus?.start, required: true }, { name: 'uploadedFile', label: 'Excel-File', type: 'file' }]} submit={turnus ? 'Hochladen' : 'Turnus hinzufügen'} /></Card>{!turnus && <SearchTable columns={[{ key: 'label', label: 'Turnus' }, { key: 'id', label: 'ID' }, { key: 'start', label: 'Turnusbeginn', render: row => formatGermanDate(row.start) }, { key: 'actions', label: 'Aktionen', sortable: false, render: row => <a className="button" href={`/upload_excel/${row.id}/`}>Excel hochladen</a> }]} rows={data.turnuses} />}</Column></Columns>;
}

export function SimpleUploadPage({ data }) {
  return <Columns><Column id="single-column"><Card title="Upload XLSX"><NativeForm token={data.csrf_token} action="/upload_spezialfamilien/" encType="multipart/form-data" fields={[{ name: 'csv_file', label: 'Datei', type: 'file', required: true }]} submit="Hochladen" /></Card></Column></Columns>;
}

export const maintenanceRoutes = [
  {
    pattern: /^\/upload$/,
    page: 'turnus-upload',
    title: 'Turnis',
    domain: 'maintenance',
    readContractKey: 'turnus-list',
    focusedReadContract: true,
    render: ({ data }) => <TurnusUploadPage data={data} />,
  },
  {
    pattern: /^\/upload_excel\/(\d+)$/,
    page: 'turnus-upload',
    title: 'Excel-Datei hochladen',
    domain: 'maintenance',
    readContractKey: 'turnus-upload',
    focusedReadContract: true,
    params: match => ({ id: match[1] }),
    render: ({ route, data }) => <TurnusUploadPage data={data} id={route.id} />,
  },
  {
    pattern: /^\/upload_spezialfamilien$/,
    page: 'special-upload',
    title: 'Upload XLSX',
    domain: 'maintenance',
    readContractKey: 'special-upload',
    focusedReadContract: true,
    render: ({ data }) => <SimpleUploadPage data={data} />,
  },
];
