import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  BirthdaysPage,
  FamiliesPage,
  KidCountPage,
  MurderPage,
  reportRoutes,
  SerialLetterPage,
} from './reports';

describe('operational report pages', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('declares every report route contract', () => {
    expect(reportRoutes.map(route => route.readContractKey)).toEqual([
      'serial-letter',
      'murder-game',
      'kid-count',
      'families',
      'birthdays',
    ]);
  });

  it('offers BuDo-Familien printing from the shared page header', () => {
    const print = vi.spyOn(window, 'print').mockImplementation(() => {});
    const familiesRoute = reportRoutes.find(route => route.page === 'families');

    render(familiesRoute.headerAction?.());

    const printButton = screen.getByRole('button', { name: 'Drucken' });
    expect(printButton).toHaveTextContent('Drucken');
    expect(printButton.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
    fireEvent.click(printButton);
    expect(print).toHaveBeenCalledOnce();
  });

  it('retains the serial-letter fields and printable document structure', () => {
    render(<SerialLetterPage data={{ kids: [{
      id: 7,
      full_name: 'Ada Lovelace',
      e_card: false,
      id_card: true,
      consent: true,
      over_the_counter_medication: 'Ibuprofen',
      prescription_medication: 'Inhalator',
      tetanus: '2024',
      tick_vaccine: '2025',
      illness: 'Asthma',
      drugs: 'Notfallspray',
      special_food: 'glutenfrei',
    }] }} />);

    expect(screen.getByRole('heading', { name: 'Ada Lovelace' })).toBeInTheDocument();
    expect(screen.getByText('E-Card: Nein')).toBeInTheDocument();
    expect(screen.getByText('Ausweis: Ja')).toBeInTheDocument();
    expect(screen.getByText('Einverständnis für ärztliche Behandlung: Ja')).toBeInTheDocument();
    expect(screen.getByText('Rezeptfreie Medikamente: Ibuprofen')).toBeInTheDocument();
    expect(screen.getByText('Medikamente auf Rezept: Inhalator')).toBeInTheDocument();
    expect(screen.getByText('Tetanusimpfung: 2024')).toBeInTheDocument();
    expect(screen.getByText('Zeckenimpfung: 2025')).toBeInTheDocument();
    expect(screen.getByText('Krankheit: Asthma')).toBeInTheDocument();
    expect(screen.getByText('Medikamente: Notfallspray')).toBeInTheDocument();
    expect(screen.getByText('Ernährung: glutenfrei')).toBeInTheDocument();
  });

  it('retains the murder-game kid and team labels in contract order', () => {
    render(<MurderPage data={{
      kids: [{ id: 1, full_name: 'Ada Kind' }],
      team: [{ id: 2, rufname: 'Boris', role_display: 'Betreuer:in' }],
    }} />);

    const pageStyle = document.querySelector('style[data-print-page-style]');
    expect(pageStyle).toHaveAttribute('media', 'print');
    expect(pageStyle).toHaveTextContent('@page { margin: 0; }');
    expect(screen.getByRole('heading', { name: 'Mörderspiel: Kids & Team' })).toBeInTheDocument();
    expect(screen.getByText('Ada Kind')).toBeInTheDocument();
    expect(screen.getByText('Betreuer:in Boris')).toBeInTheDocument();
  });

  it('preserves family grouping, labels, ordering, links, responsive layout hooks, and empty behavior', () => {
    const { rerender } = render(<FamiliesPage data={{ kids: [
      { id: 1, full_name: 'Aaron First', present: false, age: 13, budo_family: 'S' },
      { id: 2, full_name: 'Abel Second', present: true, age: 12, budo_family: 'S' },
      { id: 3, full_name: 'Ada Third', present: true, age: 14, budo_family: 'L' },
    ] }} />);

    const layout = screen.getByRole('main');
    const headings = within(layout).getAllByRole('heading').map(heading => heading.textContent);
    expect(headings).toEqual(['S (2)', 'L (1)']);
    const smallie = within(layout).getByRole('heading', { name: 'S (2)' }).closest('.card');
    expect(layout).toHaveClass('responsive-card-grid');
    expect(layout.firstElementChild).toHaveClass('gap-4', '@[41rem]:grid-cols-2');
    expect(layout.firstElementChild).not.toHaveClass('@[62rem]:grid-cols-3');
    expect(within(smallie).getByRole('list')).toHaveClass('[grid-template-columns:repeat(auto-fit,minmax(min(14rem,100%),1fr))]');
    expect(within(smallie).getAllByRole('listitem').map(item => item.textContent)).toEqual([
      'Aaron First ❌ – 13',
      'Abel Second – 12',
    ]);
    expect(screen.getByRole('link', { name: 'Aaron First ❌' })).toHaveAttribute('href', '/kid_details/1');
    expect(within(smallie).getByRole('list')).toBeInTheDocument();

    rerender(<FamiliesPage data={{ kids: [] }} />);
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
  });

  it('builds one Schwerpunkte-style print page per populated BuDo family', () => {
    render(<FamiliesPage data={{ kids: [
      { id: 1, full_name: 'Aaron First', present: false, age: 13, budo_family: 'S' },
      { id: 2, full_name: 'Abel Second', present: true, age: 12, budo_family: 'S' },
      { id: 3, full_name: 'Ada Third', present: true, age: 14, budo_family: 'L' },
      { id: 4, full_name: 'Ohne Familie', present: false, age: 11, budo_family: null },
    ] }} />);

    const familyRegion = document.querySelector('.families-page');
    expect(familyRegion).toHaveAttribute('aria-label', 'BuDo-Familien-Listen');
    const printPages = familyRegion.querySelector('.allocation-print-pages');
    const pages = [...printPages.querySelectorAll(':scope > .allocation-print-page')];
    expect(pages.map(page => within(page).getByRole('heading', { hidden: true }).textContent)).toEqual([
      'S',
      'L',
    ]);
    expect(pages.map(page => within(page).getAllByRole('listitem', { hidden: true }).map(item => item.textContent))).toEqual([
      ['Aaron First', 'Abel Second'],
      ['Ada Third'],
    ]);
    pages.forEach(page => {
      expect(page.querySelector('.allocation-print-illustration[aria-hidden="true"]')).toBeInTheDocument();
      expect(within(page).queryByRole('link', { hidden: true })).not.toBeInTheDocument();
      expect(page).not.toHaveTextContent('❌');
    });
    expect(document.querySelector('style[data-print-page-style]')).toHaveTextContent('@page { margin: 0; }');
  });

  it('renders calculated birthdays without receiving raw social-security numbers', () => {
    render(<BirthdaysPage data={{ csrf_token: 'token', kids: [
      {
        id: 1,
        full_name: 'Ada Lovelace',
        present: false,
        birthday: '2011-01-01',
        sv_birthday: '2012-07-02',
      },
      {
        id: 2,
        full_name: 'Berta Invalid',
        present: true,
        birthday: null,
        sv_birthday: null,
      },
    ] }} />);

    const adaRow = screen.getByRole('link', { name: 'Ada Lovelace ❌' }).closest('tr');
    expect(within(adaRow).getByRole('link', { name: 'Ada Lovelace ❌' })).toHaveAttribute('href', '/kid_details/1');
    expect(screen.getByText('01.01.2011 ❗')).toBeInTheDocument();
    expect(screen.getByText('02.07.2012')).toBeInTheDocument();
    expect(within(adaRow).getAllByRole('cell')[3]).toHaveTextContent('❌');
    expect(screen.getAllByText('---')).toHaveLength(3);
    const noteForms = screen.getAllByRole('button', { name: 'Speichern' }).map(button => button.closest('form'));
    expect(noteForms[0]).toHaveAttribute('action', '/kindergeburtstage/');
    expect(noteForms[0]).toHaveFormValues({ kid_id: '1', notiz: '' });
    expect(within(noteForms[0]).getByPlaceholderText('Notiz...')).toHaveAttribute('data-slot', 'input');
  });

  it('retains the standalone checked-in Kinder count and centering structure', () => {
    render(<KidCountPage data={{ totals: { checked_in: 8, kids: 12 } }} />);
    expect(screen.getByRole('heading', { name: '8/12' })).toBeInTheDocument();
  });
});
