import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { parseRoute, routeHeaderAction } from '../routes';
import { DocumentationPage } from './documentation';

describe('documentation page', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('provides a structured handbook and complete table of contents', () => {
    render(<DocumentationPage />);

    expect(screen.getByText('BuDoBase einfach nutzen')).toBeInTheDocument();
    const contents = screen.getAllByRole('navigation', { name: 'Inhaltsverzeichnis' });
    expect(contents).toHaveLength(2);
    for (const navigation of contents) {
      expect(within(navigation).getAllByRole('link')).toHaveLength(15);
      expect(within(navigation).getByRole('link', { name: /Dashboard/ })).toHaveAttribute('href', '#dashboard');
      expect(within(navigation).getByRole('link', { name: /Erste Hilfe/ })).toHaveAttribute('href', '#erste-hilfe');
      expect(within(navigation).getByRole('link', { name: /Drucken/ })).toHaveAttribute('href', '#drucken');
      expect(within(navigation).getByRole('link', { name: /Taschengeld/ })).toHaveAttribute('href', '#taschengeld');
      expect(within(navigation).getByRole('link', { name: /Am Ende des Turnus/ })).toHaveAttribute('href', '#abschluss');
    }

    for (const heading of [
      'Dashboard',
      'Erste Hilfe',
      'Listen',
      'Drucken',
      'Kinder-Detailansicht & Check-in',
      'Taschengeld',
      'Schwerpunkte',
      'Happy Cleaning',
      'Auslagerorte',
      'Spiele',
      'Team & Turnus',
      'Küche',
      'Orgi-Funktionen',
      'Am Ende des Turnus',
    ]) {
      expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument();
    }
  });

  it('keeps printing guidance complete and separate from the list descriptions', () => {
    render(<DocumentationPage />);

    const printSection = screen.getByRole('heading', { name: 'Drucken' }).closest('section');
    for (const [name, href] of [
      ['Dokumentation', '/dokumentation/'],
      ['Gut zu wissen', '/gut-zu-wissen/'],
      ['Mörderspielliste', '/murdergame'],
      ['Zuganreise', '/zuganreise'],
      ['Zugabreise', '/zugabreise'],
      ['BuDo-Familien', '/budo_familien'],
      ['SWP 1', '/swp-einteilung-w1'],
      ['SWP 2', '/swp-einteilung-w2'],
      ['Happy-Cleaning-Nummernliste', '/happy-cleaning/print/'],
      ['Küche', '/kitchen'],
    ]) {
      expect(within(printSection).getByRole('link', { name })).toHaveAttribute('href', href);
    }
    expect(within(printSection).getByText('Alle Kinder').closest('p')).toHaveTextContent('besitzt deshalb keinen Drucken-Button');
  });

  it('labels every product image as synthetic Harry-Potter example data', () => {
    render(<DocumentationPage />);

    expect(screen.queryByText('Zu den Screenshots')).not.toBeInTheDocument();
    expect(screen.getAllByText('Synthetische Beispieldaten')).toHaveLength(8);
    expect(screen.getByAltText(/Dashboard.*Harry Potter.*Hermione Granger.*Ron Weasley/)).toBeInTheDocument();
    expect(screen.getByAltText(/eingeklappter Sidebar.*geöffneter Taschengeld-Karte/)).toBeInTheDocument();
    expect(screen.getByAltText(/Taschengeldübersicht.*Harry Potter.*Hermione Granger/)).toBeInTheDocument();
  });

  it('owns an authenticated route and a working print action', () => {
    const route = parseRoute('/dokumentation/');
    expect(route).toMatchObject({
      page: 'documentation',
      domain: 'documentation',
      readContractKey: 'documentation',
    });

    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    render(routeHeaderAction(route, {}));
    screen.getByRole('button', { name: 'Dokumentation drucken' }).click();
    expect(print).toHaveBeenCalledOnce();
  });
});
