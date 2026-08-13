import { cleanup, fireEvent, render as testingLibraryRender, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Toaster } from '../components/ui/toast';
import { routeDataRequest } from '../dataLoader';
import { parseRoute } from '../routes';
import { AdminSettingsPage, SimpleUploadPage, TurnusUploadPage } from './maintenance';

const render = ui => testingLibraryRender(ui, {
  wrapper: ({ children }) => <Toaster timeout={0}>{children}</Toaster>,
});

describe('maintenance and settings pages', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('loads only the three focused maintenance contracts', () => {
    expect(routeDataRequest(parseRoute('/upload'))).toEqual({
      contractKey: 'turnus-list',
      params: {},
      url: '/api/route-data/turnus-list/',
    });
    expect(routeDataRequest(parseRoute('/upload_excel/27'))).toEqual({
      contractKey: 'turnus-upload',
      params: { id: '27' },
      url: '/api/route-data/turnus-upload/?id=27',
    });
    expect(routeDataRequest(parseRoute('/upload_spezialfamilien'))).toEqual({
      contractKey: 'special-upload',
      params: {},
      url: '/api/route-data/special-upload/',
    });
    expect(routeDataRequest(parseRoute('/settings/'))).toEqual({
      contractKey: 'admin-settings',
      params: {},
      url: '/api/route-data/admin-settings/',
    });
  });

  it('retains multipart workbook inputs for both maintenance workflows', () => {
    const { unmount } = render(<TurnusUploadPage data={{ csrf_token: 'token', turnuses: [] }} />);
    expect(screen.getByLabelText('Excel-File').form).toHaveAttribute('enctype', 'multipart/form-data');
    unmount();

    render(<SimpleUploadPage data={{ csrf_token: 'token' }} />);
    expect(screen.getByLabelText('Datei')).toBeRequired();
    expect(screen.getByLabelText('Datei').form).toHaveAttribute('action', '/upload_spezialfamilien/');
  });

  it('renders the focused Turnus list and selected upload values', () => {
    const data = {
      csrf_token: 'token',
      turnuses: [
        { id: 27, label: 'T2-2026', number: 2, start: '2026-07-01' },
        { id: 14, label: 'T1-2025', number: 1, start: '2025-07-01' },
      ],
    };
    const { unmount } = render(<TurnusUploadPage data={data} />);

    expect(screen.getAllByRole('link', { name: 'Excel hochladen' })[0]).toHaveAttribute('href', '/upload_excel/27/');
    expect(screen.getByText('T1-2025')).toBeInTheDocument();
    expect(screen.getByLabelText('Turnus Nummer')).toHaveValue(null);
    expect(screen.getByLabelText('Turnus Nummer').form.elements.csrfmiddlewaretoken).toHaveValue('token');
    unmount();

    render(<TurnusUploadPage data={{ ...data, turnuses: [data.turnuses[0]] }} id="27" />);
    expect(screen.getByLabelText('Turnus Nummer')).toHaveValue(2);
    expect(screen.getByLabelText('Beginn des Turnus (muss ein Samstag sein)')).toHaveValue('2026-07-01');
    expect(screen.getByLabelText('Excel-File').form).toHaveAttribute('action', '/upload_excel/27/');
    expect(screen.getByRole('button', { name: 'Hochladen' })).toHaveValue('Hochladen');
  });

  it('recalculates all travel times from the staff settings page', async () => {
    const user = userEvent.setup();
    const mutate = vi.fn().mockResolvedValue({ updated: 12 });
    render(<AdminSettingsPage mutate={mutate} />);

    await user.click(screen.getByRole('button', { name: 'Alle Reisezeiten neu berechnen' }));

    expect(mutate).toHaveBeenCalledWith('/api/settings/recalculate-travel-times/', {});
    expect(await screen.findByText('Reisezeiten für 12 Auslagerorte neu berechnet.')).toBeInTheDocument();
  });

  it('submits exact workbook multipart data once and shows progress', async () => {
    let resolveRequest;
    const fetchMock = vi.fn().mockReturnValue(new Promise(resolve => { resolveRequest = resolve; }));
    vi.stubGlobal('fetch', fetchMock);
    render(<TurnusUploadPage data={{
      csrf_token: 'csrf-token',
      turnuses: [{ id: 27, label: 'T2-2026', number: 2, start: '2026-07-01' }],
    }} id="27" />);
    const file = new File(['workbook-content'], 'turnus.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    fireEvent.change(screen.getByLabelText('Excel-File'), { target: { files: [file] } });
    const submit = screen.getByRole('button', { name: 'Hochladen' });

    fireEvent.click(submit);
    fireEvent.click(submit);

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(await screen.findByText('Wird gespeichert…')).toBeInTheDocument();
    expect(submit).toBeDisabled();
    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers).toEqual({ 'X-CSRFToken': 'csrf-token' });
    expect(options.body.get('_target')).toBe('/upload_excel/27/');
    expect(options.body.get('turnus_nr')).toBe('2');
    expect(options.body.get('turnus_beginn')).toBe('2026-07-01');
    expect(options.body.get('csrfmiddlewaretoken')).toBe('csrf-token');
    const uploadedFile = options.body.get('uploadedFile');
    expect(uploadedFile).toBeInstanceOf(File);
    expect(screen.getByLabelText('Excel-File').files[0]).toMatchObject({
      name: 'turnus.xlsx',
      size: 16,
      type: file.type,
    });

    resolveRequest({ ok: false, json: async () => ({ ok: false, errors: ['Arbeitsmappe ungültig.'] }) });
    const toast = await screen.findByText('Arbeitsmappe ungültig.', { selector: '.app-toast-description' });
    expect(toast.closest('.app-toast')).toHaveAttribute('data-type', 'error');
    await waitFor(() => expect(submit).not.toBeDisabled());
    expect(screen.getByLabelText('Excel-File').files[0]).toBe(file);
  });
});
