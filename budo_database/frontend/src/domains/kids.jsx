import { useEffect, useState } from 'react';
import { Pencil } from 'lucide-react';
import { Card, Column, DataTable, FieldList, findById, ResponsiveCardGrid, RestForm } from '../components';
import { AttachmentInputBar } from '../components/attachment-input-bar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { useErrorToast } from '../components/ui/toast';
import { useIsMobile } from '../hooks/use-mobile';
import { FirstAidEntry, NoteEntry } from './first-aid';
import { entryPhotoKinds, EntryPhotoGallery } from './entry-photo-gallery';
import {
  displayOrPlaceholder,
  formatGermanDate,
  formatKidBirthday,
  linkKid,
  money,
  NotFoundPage,
  requiredHealthValue,
  requiredHealthYesNo,
  TrustedHtml,
  yesNo,
} from './shared';

const photoAccept = '.jpg,.jpeg,.png,.webp,.heic,.heif,image/jpeg,image/png,image/webp,image/heic,image/heif';
const activityCookieName = 'kid-detail-activity';
const activityCookieValues = new Set(['notes', 'first_aid', 'money']);

function savedActivity() {
  if (typeof document === 'undefined') return undefined;
  const value = document.cookie
    .split('; ')
    .find(item => item.startsWith(`${activityCookieName}=`))
    ?.split('=')[1];
  if (value === 'closed') return null;
  return activityCookieValues.has(value) ? value : undefined;
}

function defaultActivity(mobile) {
  const saved = savedActivity();
  return saved === undefined ? (mobile ? null : 'notes') : saved;
}

function saveActivity(activity) {
  document.cookie = `${activityCookieName}=${activity || 'closed'}; Max-Age=2592000; Path=/; SameSite=Lax`;
}

const transactionColumns = [
  { key: 'author', label: 'Author' },
  {
    key: 'date',
    label: 'Datum',
    render: transaction => formatGermanDate(transaction.date)?.slice(0, 5),
  },
  {
    key: 'amount',
    label: 'Betrag',
    render: transaction => money(transaction.amount),
    sortValue: transaction => Number(transaction.amount),
  },
];

export function KidInteractionForm({ kid, token, onSaved, kind = 'note' }) {
  if (kind === 'money') {
    return (
      <RestForm className="kid-interaction-form mb-3 flex min-w-0 flex-wrap items-center gap-2" target={`/kid_details/${kid.id}`} token={token} onSuccess={onSaved} resetOnSuccess>
        <label className="sr-only" htmlFor="id_amount">Taschengeld</label>
        <Input className="min-w-24 flex-1" id="id_amount" name="amount" type="number" min="0" step="0.01" placeholder="Taschengeld..." />
        <Button className="shrink-0" variant="success" type="submit" name="money_action" value="withdraw">Abbuchen</Button>
        <Button className="shrink-0" variant="destructive" type="submit" name="money_action" value="topup">Aufladen</Button>
      </RestForm>
    );
  }

  const firstAid = kind === 'first_aid';
  const photoLabel = firstAid ? 'EH-Fotos' : 'Notiz-Fotos';
  return (
    <AttachmentInputBar
      className="kid-interaction-form mb-3"
      target={`/kid_details/${kid.id}`}
      token={token}
      onSuccess={onSaved}
      textId={firstAid ? 'id_erste_hilfe_beschreibung' : 'id_notiz'}
      textName={firstAid ? 'erste_hilfe_beschreibung' : 'notiz'}
      textLabel={firstAid ? 'Was ist passiert und welche Maßnahme wurde getroffen?' : 'Notiz'}
      textLabelVisible={firstAid}
      placeholder={firstAid ? 'Erste-Hilfe-Maßnahme...' : 'Notiz...'}
      required={firstAid}
      photoId={firstAid ? 'id_erste_hilfe_fotos' : 'id_notiz_fotos'}
      photoName={firstAid ? 'erste_hilfe_fotos' : 'notiz_fotos'}
      photoLabel={photoLabel}
      photoButtonLabel={firstAid ? 'Fotos für Erste Hilfe auswählen' : 'Fotos zur Notiz auswählen'}
      photoAccept={photoAccept}
      submitLabel={firstAid ? 'EH-Eintrag senden' : 'Notiz senden'}
      submitName={firstAid ? 'interaction_kind' : undefined}
      submitValue={firstAid ? 'first_aid' : undefined}
    />
  );
}

export const kidColumns = [
  { key: 'name', label: 'Name', render: linkKid },
  { key: 'budo_family', label: 'Familie', render: row => displayOrPlaceholder(row.budo_family) },
  { key: 'sex_short', label: '⚧', priority: 'low' },
  { key: 'age', label: 'Alter', className: 'number-cell', render: row => <>{row.birthday_during_turnus && '🥳 '}{displayOrPlaceholder(row.age)}</> },
  { key: 'weeks', label: 'Wochen', priority: 'low' },
  { key: 'focus_w1', label: 'SWP 1' },
  { key: 'focus_w2', label: 'SWP 2' },
  { key: 'siblings', label: 'Geschwister', priority: 'low', render: row => displayOrPlaceholder(row.siblings) },
  { key: 'tent_request', label: 'Zeltwunsch', priority: 'low', render: row => displayOrPlaceholder(row.tent_request) },
  { key: 'food', label: 'Ernährung' },
  { key: 'drugs', label: 'Medikamente', render: row => displayOrPlaceholder(row.drugs) },
  { key: 'illness', label: 'Gesundheitliches', render: row => displayOrPlaceholder(row.illness) },
  { key: 'note', label: 'Anmerkungen', priority: 'low', render: row => <TrustedHtml value={row.note} /> },
  { key: 'booking_note', label: 'Anmerkungen (Buchung)', priority: 'low', render: row => <TrustedHtml value={row.booking_note} /> },
];

export function KidsPage({ data }) {
  const rows = data.kids.map(kid => ({ ...kid, filterText: kid.full_name }));
  return <main className="all-kids-page table-only" id="body-container"><DataTable columns={kidColumns} rows={rows} showFilter stickyHeader stickyFirstColumn verticalScroll /></main>;
}

export function KidDetailPage({ data, id, mutate, onSaved }) {
  const showError = useErrorToast();
  const mobile = useIsMobile();
  const [openActivity, setOpenActivity] = useState(() => defaultActivity(mobile));
  useEffect(() => setOpenActivity(defaultActivity(mobile)), [mobile]);
  const changeOpenActivity = (activity, expanded) => {
    const nextActivity = expanded ? activity : null;
    saveActivity(nextActivity);
    setOpenActivity(nextActivity);
  };
  const kid = findById(data.kids, id);
  if (!kid) return <NotFoundPage />;
  const focusItems = kid.focus_assignments?.length
    ? kid.focus_assignments.map(period => [
      period.label,
      period.focuses.length
        ? period.focuses.map(focus => focus.label).join(', ')
        : '---',
    ])
    : [['Schwerpunkte', '---']];
  const happyCleaningItems = kid.happy_cleaning_assignments?.length
    ? kid.happy_cleaning_assignments.map(assignment => [
      assignment.label,
      assignment.target.label,
    ])
    : [['Happy Cleaning', '---']];
  const deposit = async action => {
    try {
      await mutate('/update_pfand/', { id: kid.id, action });
    } catch {
      showError('Das Pfand konnte nicht gespeichert werden.');
    }
  };
  return (
    <>
      <ResponsiveCardGrid independentColumns>
        <Column id="left-column" className="min-w-0 gap-4">
          <Card title={`${kid.full_name}${kid.present ? '' : ' ❌'}`} id="kinderinfos"><FieldList items={[["Geschlecht", kid.sex], ["Alter", kid.age], ["Geburtstag", formatKidBirthday(kid)], ["Aufenthaltsdauer", `${kid.weeks}-wöchig`], ["Geschwister", kid.siblings], ["Zeltwunsch", kid.tent_request], ["War schon mal im Bunten Dorf", yesNo(kid.budo_experience)]]} /></Card>
          <Card title="BuDo" id="budo-container" actions={<Button href={`/${kid.present ? 'check_out' : 'check_in'}/${kid.id}`}>{kid.present ? 'Auschecken' : 'Einchecken'}</Button>}><FieldList items={[["Turnus", data.turnus?.label], ["Budo Familie", kid.budo_family], ...focusItems, ["Happy Cleaning Nummer", displayOrPlaceholder(kid.happy_cleaning_number)], ...happyCleaningItems]} /></Card>
        </Column>
        <Column id="center-column" className="min-w-0 gap-4">
          <Card title="Gesundheitsinfos" id="health_info"><FieldList items={[["Sozialversicherungsnummer", kid.social_security_number], ["Krankheiten", displayOrPlaceholder(kid.illness)], ["Medikamente", displayOrPlaceholder(kid.drugs)], ["Vegetarisch", kid.vegetarian], ["Ernährungsvorgaben", kid.special_food], ["Schwimmkenntnisse", kid.swimmer], ["Einverständnis für ärztliche Behandlung", requiredHealthYesNo(kid.consent)], ["Rezeptfreie Medikamente", requiredHealthValue(kid.over_the_counter_medication)], ["Medikamente auf Rezept", requiredHealthValue(kid.prescription_medication)], ["Tetanusimpfung", requiredHealthValue(kid.tetanus)], ["Zeckenimpfung", requiredHealthValue(kid.tick_vaccine)]]} /></Card>
          <Card title="Familie" id="family_info"><FieldList items={[["Organisation", kid.organization], ["Anmelder:in", kid.registrant_name], ["Anmelder:in Email", <a href={`mailto:${kid.registrant_email}`}>{kid.registrant_email}</a>], ["Anmelder:in Mobil", <a href={`tel:${kid.registrant_phone}`}>{kid.registrant_phone}</a>], ["Hauptversichert bei", kid.insured_with], ["Notfallkontakte", kid.emergency_contacts]]} /></Card>
        </Column>
        <Column id="right-column" className="min-w-0 gap-4">
          <EntryPhotoGallery entries={kid.notes} childName={kid.full_name} photoKind={entryPhotoKinds.notes}>
            <Card title="Notizen" id="notizen" expanded={openActivity === 'notes'} onExpandedChange={expanded => changeOpenActivity('notes', expanded)}>
              <FieldList items={[["Anmerkungen (Buchung)", <TrustedHtml value={kid.booking_note} />], ["Anmerkungen", <TrustedHtml value={kid.note} />]]} />
              <KidInteractionForm kid={kid} token={data.csrf_token} onSaved={onSaved} kind="note" />
              <ul>{kid.notes.length ? kid.notes.map(note => <NoteEntry entry={note} childName={kid.full_name} key={note.id} />) : <li>Noch keine Notizen.</li>}</ul>
            </Card>
          </EntryPhotoGallery>
          <EntryPhotoGallery entries={kid.first_aid_entries} childName={kid.full_name}>
            <Card title="Erste Hilfe" id="erste-hilfe" expanded={openActivity === 'first_aid'} onExpandedChange={expanded => changeOpenActivity('first_aid', expanded)}>
              <KidInteractionForm kid={kid} token={data.csrf_token} onSaved={onSaved} kind="first_aid" />
              <ul>{kid.first_aid_entries?.length ? kid.first_aid_entries.map(entry => <FirstAidEntry entry={entry} childName={kid.full_name} key={entry.id} />) : <li>Noch keine EH-Einträge.</li>}</ul>
            </Card>
          </EntryPhotoGallery>
          <Card title={`Taschengeld: ${money(kid.remaining_money)}${kid.remaining_money < 5 ? ' 🚨' : ''}`} id="taschengeld" expanded={openActivity === 'money'} onExpandedChange={expanded => changeOpenActivity('money', expanded)}>
            <div className="mb-3 flex flex-wrap items-center gap-2" aria-label="Pfand">
              <span>Pfand:</span>
              <Button className="gap-1" size="sm" type="button" variant="secondary" aria-label="Pfand verringern" onClick={() => deposit('decrease')}><span aria-hidden="true">−</span><span className="max-[900px]:hidden">Pfand</span></Button>
              <strong>{kid.deposit} ({money(kid.deposit * 0.25)})</strong>
              <Button className="gap-1" size="sm" type="button" aria-label="Pfand erhöhen" onClick={() => deposit('increase')}><span aria-hidden="true">+</span><span className="max-[900px]:hidden">Pfand</span></Button>
            </div>
            <KidInteractionForm kid={kid} token={data.csrf_token} onSaved={onSaved} kind="money" />
            <DataTable columns={transactionColumns} rows={kid.transactions} empty="Dieses Kind ist arm." />
          </Card>
        </Column>
      </ResponsiveCardGrid>
    </>
  );
}

export const kidRoutes = [
  {
    pattern: /^\/all_kids$/,
    page: 'kids',
    title: 'Alle Kinder',
    domain: 'kids',
    readContractKey: 'kids-directory',
    render: ({ data }) => <KidsPage data={data} />,
  },
  {
    pattern: /^\/kid_details\/(\d+)$/,
    page: 'kid',
    title: 'Kind',
    domain: 'kids',
    readContractKey: 'kid-detail',
    params: match => ({ id: match[1] }),
    resolveTitle: (route, data) => findById(data.kids, route.id)?.full_name || route.title,
    resolveHeaderTitle: (route, data, title) => data.permissions?.change_kids
      ? <a href={`/admin/budo_app/kinder/${route.id}/change/`}>{title}</a>
      : title,
    headerAction: (_data, { route }) => (
      <Button
        className="mobile-icon-action"
        size="responsive-icon"
        href={`/kid_details/${route.id}/edit`}
        aria-label="Bearbeiten"
      >
        <span className="desktop-action-label">Bearbeiten</span>
        <Pencil className="mobile-action-label" aria-hidden="true" />
      </Button>
    ),
    render: ({ route, data, mutate, refresh }) => <KidDetailPage data={data} id={route.id} mutate={mutate} onSaved={refresh} />,
  },
];
