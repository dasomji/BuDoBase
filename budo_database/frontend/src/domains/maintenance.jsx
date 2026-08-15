import { useState } from 'react';

import { Card, Column, Columns, DataTable, findById, NativeForm } from '../components';
import { Button } from '../components/ui/button';
import { useErrorToast, useSuccessToast } from '../components/ui/toast';
import { formatGermanDate } from './shared';

export function TurnusUploadPage({ data, id }) {
  const turnus = id ? findById(data.turnuses, id) : null;
  return <Columns><Column id="single-column"><Card title={turnus ? `Excel-Datei hochladen für Turnus ${turnus.number}` : 'Turnis'}><NativeForm token={data.csrf_token} action={turnus ? `/upload_excel/${turnus.id}/` : '/upload/'} encType="multipart/form-data" fields={[{ name: 'turnus_nr', label: 'Turnus Nummer', type: 'number', value: turnus?.number, required: true }, { name: 'turnus_beginn', label: 'Beginn des Turnus (muss ein Samstag sein)', type: 'date', value: turnus?.start, required: true }, { name: 'uploadedFile', label: 'Excel-File', type: 'file' }]} submit={turnus ? 'Hochladen' : 'Turnus hinzufügen'} /></Card>{!turnus && <DataTable columns={[{ key: 'label', label: 'Turnus' }, { key: 'id', label: 'ID' }, { key: 'start', label: 'Turnusbeginn', render: row => formatGermanDate(row.start) }, { key: 'actions', label: 'Aktionen', sortable: false, render: row => <Button href={`/upload_excel/${row.id}/`}>Excel hochladen</Button> }]} rows={data.turnuses} />}</Column></Columns>;
}

export function AdminSettingsPage({ mutate }) {
  const [busy, setBusy] = useState(false);
  const showSuccess = useSuccessToast();
  const showError = useErrorToast();
  const recalculate = async () => {
    setBusy(true);
    try {
      const result = await mutate('/api/settings/recalculate-travel-times/', {});
      showSuccess(`Reisezeiten für ${result.updated} Auslagerorte neu berechnet.`);
    } catch (error) {
      showError(error.payload?.detail || 'Reisezeiten konnten nicht neu berechnet werden.');
    } finally {
      setBusy(false);
    }
  };
  return <Columns><Column id="single-column"><Card title="Reisezeiten"><p>Berechnet die Fahr- und Gehzeiten für alle Auslagerorte neu. Wenn ein Parkspot hinterlegt ist, wird dorthin geroutet.</p><div className="mt-4"><Button type="button" disabled={busy} onClick={recalculate}>{busy ? 'Reisezeiten werden berechnet…' : 'Alle Reisezeiten neu berechnen'}</Button></div></Card></Column></Columns>;
}

export const maintenanceRoutes = [
  {
    pattern: /^\/settings$/,
    page: 'admin-settings',
    title: 'Einstellungen',
    domain: 'maintenance',
    readContractKey: 'admin-settings',
    render: ({ mutate }) => <AdminSettingsPage mutate={mutate} />,
  },
  {
    pattern: /^\/upload$/,
    page: 'turnus-upload',
    title: 'Turnis',
    domain: 'maintenance',
    readContractKey: 'turnus-list',
    render: ({ data }) => <TurnusUploadPage data={data} />,
  },
  {
    pattern: /^\/upload_excel\/(\d+)$/,
    page: 'turnus-upload',
    title: 'Excel-Datei hochladen',
    domain: 'maintenance',
    readContractKey: 'turnus-upload',
    params: match => ({ id: match[1] }),
    render: ({ route, data }) => <TurnusUploadPage data={data} id={route.id} />,
  },
];
