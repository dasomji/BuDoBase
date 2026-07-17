import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import {
  BirthdaysPage,
  FamiliesPage,
  KidCountPage,
  MurderPage,
  reportRoutes,
  SerialLetterPage,
} from './reports';

describe('operational report pages', () => {
  afterEach(cleanup);

  it('opts every report route into its focused read contract', () => {
    expect(reportRoutes.map(route => [route.readContractKey, route.focusedReadContract])).toEqual([
      ['serial-letter', true],
      ['murder-game', true],
      ['kid-count', true],
      ['families', true],
      ['special-families', true],
      ['birthdays', true],
    ]);
  });

  it('retains the serial-letter fields and printable document structure', () => {
    const { container } = render(<SerialLetterPage data={{ kids: [{
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

    expect(screen.getByText('Ada Lovelace')).toHaveClass('serienbrief_name');
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
    expect(container.querySelector('.serienbrief-kid')).toBeInTheDocument();
    expect(container.querySelectorAll('.serienbrief-container')).toHaveLength(4);
  });

  it('retains the murder-game kid and team labels in contract order', () => {
    render(<MurderPage data={{
      kids: [{ id: 1, full_name: 'Ada Kind' }],
      team: [{ id: 2, rufname: 'Boris', role_display: 'Betreuer:in' }],
    }} />);

    expect(screen.getByRole('heading', { name: 'Mörderspiel: Kids & Team' })).toHaveClass('murder_name');
    expect(screen.getByText('Ada Kind')).toHaveClass('murder_name');
    expect(screen.getByText('Betreuer:in Boris')).toHaveClass('murder_name');
  });

  it('preserves family grouping, labels, ordering, links, and empty behavior', () => {
    const { rerender } = render(<FamiliesPage data={{ kids: [
      { id: 1, full_name: 'Aaron First', present: false, age: 13, budo_family: 'S' },
      { id: 2, full_name: 'Abel Second', present: true, age: 12, budo_family: 'S' },
      { id: 3, full_name: 'Ada Third', present: true, age: 14, budo_family: 'L' },
    ] }} />);

    const headings = screen.getAllByRole('heading').map(heading => heading.textContent);
    expect(headings).toEqual(['S (2)', 'L (1)']);
    const smallie = screen.getByRole('heading', { name: 'S (2)' }).closest('.card');
    expect(within(smallie).getAllByRole('listitem').map(item => item.textContent)).toEqual([
      'Aaron First ❌ – 13',
      'Abel Second – 12',
    ]);
    expect(screen.getByRole('link', { name: 'Aaron First ❌' })).toHaveAttribute('href', '/kid_details/1');

    rerender(<FamiliesPage special data={{ kids: [] }} />);
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
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

    expect(screen.getByRole('link', { name: 'Ada Lovelace ❌' })).toHaveAttribute('href', '/kid_details/1');
    expect(screen.getByText('01.01.2011 ❗')).toBeInTheDocument();
    expect(screen.getByText('02.07.2012')).toBeInTheDocument();
    expect(screen.getByText('❌')).toBeInTheDocument();
    expect(screen.getAllByText('---')).toHaveLength(3);
    const noteForms = screen.getAllByRole('button', { name: 'Speichern' }).map(button => button.closest('form'));
    expect(noteForms[0]).toHaveAttribute('action', '/kindergeburtstage/');
    expect(noteForms[0]).toHaveFormValues({ kid_id: '1', notiz: '' });
  });

  it('retains the standalone checked-in Kinder count and centering structure', () => {
    const { container } = render(<KidCountPage data={{ totals: { checked_in: 8, kids: 12 } }} />);

    expect(screen.getByRole('heading', { name: '8/12' })).toHaveClass('gesamtkinderzahl');
    expect(container.querySelector('main')).toHaveClass('gesamtkinderzahl-body');
    expect(container.querySelector('.gesamtkinderzahl-container')).toContainElement(screen.getByRole('heading'));
  });
});
