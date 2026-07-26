import { EyeIcon, EyeOffIcon } from 'lucide-react';

import { Card, Column, DataTable } from '../components';
import { Button } from '../components/ui/button';
import { useErrorToast } from '../components/ui/toast';
import { displayOrPlaceholder, linkKid } from './shared';

const EMPTY_STATS = {
  average_age: null,
  sex: { male: 0, female: 0, diverse: 0 },
  families: { S: 0, M: 0, L: 0, XL: 0 },
};

const medalRankClasses = {
  1: 'bg-[linear-gradient(145deg,#fff0a3,#d4a514_70%,#b8860b)]',
  2: 'bg-[linear-gradient(145deg,#f4f4f4,#b8bec4_70%,#8d949b)]',
  3: 'bg-[linear-gradient(145deg,#efbc83,#c77832_70%,#96501f)]',
};

function MedalButton({ active, children, rank, ...props }) {
  return (
    <Button
      className={`inline-flex size-9.5 shrink-0 items-center justify-center rounded-full border border-foreground/45 p-0 font-semibold text-[#30291d] shadow-[inset_0_1px_1px_rgba(255,255,255,.65),0_1px_2px_rgba(55,55,55,.2)] [text-shadow:0_1px_rgba(255,255,255,.45)] hover:-translate-y-px hover:brightness-105 ${medalRankClasses[rank]} ${active ? 'border-foreground shadow-[inset_0_0_0_2px_rgba(255,255,255,.75),0_0_0_2px_#373737,0_2px_5px_rgba(55,55,55,.35)]' : ''}`}
      variant="ghost"
      size="icon"
      type="button"
      aria-pressed={active}
      {...props}
    >
      {children}
    </Button>
  );
}

function formatAverageAge(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '---';
  return new Intl.NumberFormat('de-AT', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function AllocationStats({ focus, showKids }) {
  const stats = focus.stats || EMPTY_STATS;
  const sex = { ...EMPTY_STATS.sex, ...stats.sex };
  const families = { ...EMPTY_STATS.families, ...stats.families };
  return (
    <div className={showKids ? 'mb-3 border-b border-foreground/25 pb-2' : ''} aria-label={`Statistik ${focus.name}`}>
      <p className="mb-1"><span className="label">Ø Alter</span>: {formatAverageAge(stats.average_age)}</p>
      <p className="mb-1"><span className="label">Geschlechter</span>: {sex.male} ♂ · {sex.female} ♀ · {sex.diverse} ⚧</p>
      <p className="m-0"><span className="label">BuDo-Familien</span>: {families.S} S · {families.M} M · {families.L} L · {families.XL} XL</p>
    </div>
  );
}

function AllocationCard({ focus, kids, showKids }) {
  const assignedKids = kids.filter(kid => focus.kid_ids.includes(kid.id));
  return (
    <Card title={`${focus.name}: ${focus.kid_ids.length}`}>
      <AllocationStats focus={focus} showKids={showKids} />
      <ul className={`${showKids ? 'grid' : 'hidden'} m-0 grid-cols-1 gap-x-4 gap-y-1 pl-4 min-[901px]:grid-cols-2 [&>li]:min-w-0 [&>li]:break-inside-avoid`} aria-hidden={!showKids}>
        {showKids && assignedKids.length === 0
          ? <li className="col-span-full italic">Noch keine Kinder für diesen Schwerpunkt eingeteilt</li>
          : assignedKids.map(kid => <li key={kid.id}>{linkKid(kid)}</li>)}
      </ul>
    </Card>
  );
}

export function AllocationPage({ data, week, mutate, showKids = true }) {
  const showError = useErrorToast();
  const save = async (...args) => {
    try {
      await mutate(...args);
    } catch {
      showError('Die Schwerpunktdaten konnten nicht gespeichert werden.');
    }
  };
  const focuses = data.focuses.filter(focus => focus.week === `w${week}`);
  const rows = data.kids.map(kid => ({ ...kid, filterText: kid.full_name }));
  const columns = [
    { key: 'name', label: 'Name', render: linkKid },
    {
      key: 'assigned',
      label: 'Einteilung',
      sortValue: kid => focuses.find(focus => kid.focus_ids.includes(focus.id))?.name || '',
      render: kid => (
        <select
          value={kid.focus_ids.find(id => focuses.some(focus => focus.id === id)) || ''}
          onChange={event => event.target.value && save('/update-schwerpunkt-wahl/', {
            kid_id: kid.id,
            swp_id: Number(event.target.value),
            choice_rank: null,
          })}
        >
          <option value="">Nicht zugeordnet</option>
          {focuses.map(focus => <option value={focus.id} key={focus.id}>{focus.name}</option>)}
        </select>
      ),
    },
    ...focuses.map(focus => ({
      key: `focus-${focus.id}`,
      label: focus.name,
      render: kid => {
        const choice = kid.choices.find(item => item.week === `w${week}`);
        return (
          <span className="inline-flex gap-1">
            {['1', '2', '3'].map(rank => {
              const choiceKey = { 1: 'first', 2: 'second', 3: 'third' }[rank];
              const selected = Number(choice?.[choiceKey]) === focus.id;
              return (
                <MedalButton
                  active={selected}
                  rank={rank}
                  key={rank}
                  onClick={() => save('/update-schwerpunkt-wahl/', {
                    kid_id: kid.id,
                    swp_id: focus.id,
                    choice_rank: rank,
                  })}
                >
                  {rank}
                </MedalButton>
              );
            })}
          </span>
        );
      },
    })),
    {
      key: 'friends',
      label: 'Freunde',
      sortValue: kid => kid.choices.find(choice => choice.week === `w${week}`)?.friends || '',
      render: kid => {
        const friends = kid.choices.find(choice => choice.week === `w${week}`)?.friends || '';
        return (
          <>
            {friends || '---'}{' '}
            <Button
              className="size-7 bg-transparent p-0 shadow-none hover:bg-muted"
              variant="ghost"
              size="icon-sm"
              type="button"
              aria-label={`Freunde von ${kid.full_name} bearbeiten`}
              onClick={() => {
                const value = window.prompt('Freunde bearbeiten', friends);
                if (value !== null) save('/update_freunde/', { kid_id: kid.id, freunde: value, week });
              }}
            >
              ✏️
            </Button>
          </>
        );
      },
    },
    { key: 'age', label: 'Alter' },
    { key: 'budo_family', label: 'Familie', render: kid => displayOrPlaceholder(kid.budo_family) },
    { key: 'siblings', label: 'Geschwister', render: kid => displayOrPlaceholder(kid.siblings) },
  ];
  const overview = (
    <div className="flex w-full items-start gap-3 overflow-x-auto [&>.card]:m-0 [&>.card]:min-w-[min(20rem,80vw)] [&>.card]:flex-[1_0_20rem]" aria-label="SWP-Übersicht">
      {focuses.map(focus => (
        <AllocationCard focus={focus} kids={data.kids} showKids={showKids} key={focus.id} />
      ))}
    </div>
  );
  return (
    <main className="allocation-page flex min-w-0 flex-col [&_.table-sticky-controls]:sticky [&_.table-sticky-controls]:top-[var(--app-header-height,0px)] [&_.table-sticky-controls]:z-5" id="body-container">
      <Column id="right-column" className="allocation-table-column min-w-0 w-full min-[901px]:flex min-[901px]:min-h-[calc(100svh-var(--app-header-height,0px))] min-[901px]:flex-col min-[901px]:[&>[data-slot=table-scroll][data-vertical-scroll]]:h-0 min-[901px]:[&>[data-slot=table-scroll][data-vertical-scroll]]:min-h-[50vh] min-[901px]:[&>[data-slot=table-scroll][data-vertical-scroll]]:max-h-none min-[901px]:[&>[data-slot=table-scroll][data-vertical-scroll]]:flex-1 min-[901px]:[&_[data-slot=table]]:min-h-[50vh]">
        <DataTable columns={columns} rows={rows} showFilter beforeFilter={overview} stickyHeader stickyFirstColumn verticalScroll />
      </Column>
      <section className="allocation-print-pages" aria-label="SWP-Listen">
        {focuses.map(focus => (
          <article className="allocation-print-page" key={focus.id}>
            <div className="allocation-print-illustration" aria-hidden="true" />
            <h1>{focus.name}</h1>
            <ul>{data.kids.filter(kid => focus.kid_ids.includes(kid.id)).map(kid => <li key={kid.id}>{kid.full_name}</li>)}</ul>
          </article>
        ))}
      </section>
    </main>
  );
}

export const allocationRoutes = [{
  pattern: /^\/swp-einteilung-w([12])$/,
  page: 'allocation',
  title: 'SWP-Einteilung',
  domain: 'allocation',
  readContractKey: 'allocation',
  params: match => ({ week: match[1], title: `SWP-Einteilung Woche ${match[1]}` }),
  headerAction: (_data, { pageState = {}, setPageState }) => (
    <Button
      className="mobile-icon-action"
      type="button"
      aria-label={pageState.showAllocationKids === false ? 'Kinder anzeigen' : 'Kinder ausblenden'}
      aria-pressed={pageState.showAllocationKids !== false}
      onClick={() => setPageState?.(current => ({
        ...current,
        showAllocationKids: current.showAllocationKids === false,
      }))}
    >
      <span className="desktop-action-label">
        {pageState.showAllocationKids === false ? 'Kinder anzeigen' : 'Kinder ausblenden'}
      </span>
      {pageState.showAllocationKids === false
        ? <EyeIcon className="mobile-action-label" aria-hidden="true" />
        : <EyeOffIcon className="mobile-action-label" aria-hidden="true" />}
    </Button>
  ),
  render: ({ route, data, mutate, pageState = {} }) => (
    <AllocationPage
      data={data}
      week={route.week}
      mutate={mutate}
      showKids={pageState.showAllocationKids !== false}
    />
  ),
}];
