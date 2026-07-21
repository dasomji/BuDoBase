import { useState } from 'react';
import { Card, Column, Columns, FieldList, findById, RestForm, SearchTable } from '../components';
import { FirstAidEntry, NoteEntry } from './first-aid';
import { FirstAidGallery } from './first-aid-gallery';
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

function interactionModeCookie() {
  if (typeof document === 'undefined') return null;
  const cookie = document.cookie.split('; ').find(item => item.startsWith('interaction-bar='));
  return cookie?.split('=')[1] || null;
}

const interactionModes = {
  'erste-hilfe-form': 'first_aid',
  'geld-form': 'amount',
  'notiz-form': 'notiz',
};

function saveInteractionMode(field) {
  const value = Object.entries(interactionModes).find(([, mode]) => mode === field)?.[0] || 'notiz-form';
  document.cookie = `interaction-bar=${value}; Max-Age=2592000; Path=/; SameSite=Lax`;
}

export function KidInteractionForm({ kid, token, onSaved }) {
  const [field, setField] = useState(() => interactionModes[interactionModeCookie()] || 'notiz');
  const [notePhotoCount, setNotePhotoCount] = useState(0);
  const [firstAidPhotoCount, setFirstAidPhotoCount] = useState(0);
  const handleSaved = onSaved
    ? async result => {
        await onSaved(result);
        setNotePhotoCount(0);
        setFirstAidPhotoCount(0);
      }
    : undefined;
  const show = name => event => {
    event.preventDefault();
    setField(name);
    saveInteractionMode(name);
  };
  return (
    <div id="interaction-bar">
      <div id="interaction-input">
        <RestForm target={`/kid_details/${kid.id}`} token={token} encType="multipart/form-data" onSuccess={handleSaved} resetOnSuccess>
          <div id="notiz-form" className={field === 'notiz' ? '' : 'hidden'}>
            <p className="note-input-field">
              <label htmlFor="id_notiz" onClick={show('amount')} title="Zu Taschengeld wechseln">Notiz</label>
              <textarea className="interaction-textarea" id="id_notiz" name="notiz" placeholder="Notiz..." rows="2" />
              <label className="attachment-button" htmlFor="id_notiz_fotos">
                <span className="sr-only">Notiz-Fotos</span><span aria-hidden="true">+</span>
                {notePhotoCount > 0 && <span className="attachment-count" aria-hidden="true">{notePhotoCount}</span>}
              </label>
              <input id="id_notiz_fotos" className="attachment-input" aria-label="Notiz-Fotos" name="notiz_fotos" type="file" accept=".jpg,.jpeg,.png,.webp,.heic,.heif,image/jpeg,image/png,image/webp,image/heic,image/heif" multiple disabled={field !== 'notiz'} onChange={event => setNotePhotoCount(event.target.files?.length || 0)} />
            </p>
          </div>
          <div id="geld-form" className={field === 'amount' ? '' : 'hidden'}>
            <p><label htmlFor="id_amount" onClick={show('first_aid')} title="Zu Erste Hilfe wechseln">Taschengeld</label><input id="id_amount" name="amount" type="number" min="0" step="0.01" placeholder="Taschengeld..." /></p>
          </div>
          <div id="erste-hilfe-form" className={field === 'first_aid' ? '' : 'hidden'}>
            <p className="first-aid-input-field">
              <label htmlFor="id_erste_hilfe_beschreibung" onClick={show('notiz')} title="Zu Notiz wechseln">Erste Hilfe</label>
              <textarea className="interaction-textarea" id="id_erste_hilfe_beschreibung" name="erste_hilfe_beschreibung" placeholder="Erste-Hilfe-Maßnahme..." rows="2" required disabled={field !== 'first_aid'} />
              <label className="attachment-button" htmlFor="id_erste_hilfe_fotos">
                <span className="sr-only">EH-Fotos</span><span aria-hidden="true">+</span>
                {firstAidPhotoCount > 0 && <span className="attachment-count" aria-hidden="true">{firstAidPhotoCount}</span>}
              </label>
              <input
                id="id_erste_hilfe_fotos"
                className="attachment-input"
                name="erste_hilfe_fotos"
                type="file"
                accept=".jpg,.jpeg,.png,.webp,.heic,.heif,image/jpeg,image/png,image/webp,image/heic,image/heif"
                multiple
                disabled={field !== 'first_aid'}
                onChange={event => setFirstAidPhotoCount(event.target.files?.length || 0)}
              />
            </p>
          </div>
          {field === 'amount'
            ? <><button className="money-action money-withdraw" type="submit" name="money_action" value="withdraw">Abbuchen</button><button className="money-action money-topup" type="submit" name="money_action" value="topup">Aufladen</button></>
            : <button className="interaction-send-button" type="submit" name={field === 'first_aid' ? 'interaction_kind' : undefined} value={field === 'first_aid' ? 'first_aid' : undefined} aria-label={field === 'first_aid' ? 'EH-Eintrag senden' : undefined}><img src="/static/img/send-button.svg" alt={field === 'first_aid' ? '' : 'Senden'} /></button>}
        </RestForm>
      </div>
    </div>
  );
}

export const kidColumns = [
  { key: 'name', label: 'Name', render: linkKid },
  { key: 'budo_family', label: 'Familie', render: row => displayOrPlaceholder(row.budo_family) },
  { key: 'special_family', label: 'Haus', render: row => displayOrPlaceholder(row.special_family) },
  { key: 'sex_short', label: '⚧' },
  { key: 'age', label: 'Alter', className: 'number-cell', render: row => <>{row.birthday_during_turnus && '🥳 '}{displayOrPlaceholder(row.age)}</> },
  { key: 'weeks', label: 'Wochen' },
  { key: 'focus_w1', label: 'SWP 1' },
  { key: 'focus_w2', label: 'SWP 2' },
  { key: 'siblings', label: 'Geschwister', render: row => displayOrPlaceholder(row.siblings) },
  { key: 'tent_request', label: 'Zeltwunsch', render: row => displayOrPlaceholder(row.tent_request) },
  { key: 'food', label: 'Ernährung' },
  { key: 'drugs', label: 'Medikamente', render: row => displayOrPlaceholder(row.drugs) },
  { key: 'illness', label: 'Gesundheitliches', render: row => displayOrPlaceholder(row.illness) },
  { key: 'note', label: 'Anmerkungen', render: row => <TrustedHtml value={row.note} /> },
  { key: 'booking_note', label: 'Anmerkungen (Buchung)', render: row => <TrustedHtml value={row.booking_note} /> },
];

export function KidsPage({ data }) {
  const rows = data.kids.map(kid => ({ ...kid, filterText: kid.full_name }));
  return <main className="table-only" id="body-container"><SearchTable columns={kidColumns} rows={rows} showFilter /></main>;
}

export function KidDetailPage({ data, id, mutate, onSaved }) {
  const kid = findById(data.kids, id);
  if (!kid) return <NotFoundPage />;
  const deposit = action => mutate('/update_pfand/', { id: kid.id, action });
  return (
    <FirstAidGallery entries={[...(kid.notes || []), ...(kid.first_aid_entries || [])]} childName={kid.full_name}>
      <Columns className="kid-detail-grid">
        <Column id="left-column">
          <Card title={`${kid.full_name}${kid.present ? '' : ' ❌'}`} id="kinderinfos"><FieldList items={[["Geschlecht", kid.sex], ["Alter", kid.age], ["Geburtstag", formatKidBirthday(kid)], ["Aufenthaltsdauer", `${kid.weeks}-wöchig`], ["Geschwister", kid.siblings], ["Zeltwunsch", kid.tent_request], ["War schon mal im Bunten Dorf", yesNo(kid.budo_experience)]]} /></Card>
          <Card title="BuDo" id="budo-container"><FieldList items={[["Turnus", data.turnus?.label], ["Budo Familie", kid.budo_family], ["Haus", kid.special_family], ["SWP 1", kid.focus_w1], ["SWP 2", kid.focus_w2]]} /><div className="react-actions"><a className="button" href={`/${kid.present ? 'check_out' : 'check_in'}/${kid.id}`}>{kid.present ? 'Auschecken' : 'Einchecken'}</a></div></Card>
        </Column>
        <Column id="center-column">
          <Card title="Gesundheitsinfos" id="health_info"><FieldList items={[["Sozialversicherungsnummer", kid.social_security_number], ["Krankheiten", displayOrPlaceholder(kid.illness)], ["Medikamente", displayOrPlaceholder(kid.drugs)], ["Vegetarisch", kid.vegetarian], ["Ernährungsvorgaben", kid.special_food], ["Schwimmkenntnisse", kid.swimmer], ["Einverständnis für ärztliche Behandlung", requiredHealthYesNo(kid.consent)], ["Rezeptfreie Medikamente", requiredHealthValue(kid.over_the_counter_medication)], ["Medikamente auf Rezept", requiredHealthValue(kid.prescription_medication)], ["Tetanusimpfung", requiredHealthValue(kid.tetanus)], ["Zeckenimpfung", requiredHealthValue(kid.tick_vaccine)]]} /></Card>
          <Card title="Familie" id="family_info"><FieldList items={[["Organisation", kid.organization], ["Anmelder:in", kid.registrant_name], ["Anmelder:in Email", <a href={`mailto:${kid.registrant_email}`}>{kid.registrant_email}</a>], ["Anmelder:in Mobil", <a href={`tel:${kid.registrant_phone}`}>{kid.registrant_phone}</a>], ["Hauptversichert bei", kid.insured_with], ["Notfallkontakte", kid.emergency_contacts]]} /></Card>
        </Column>
        <Column id="right-column">
          <Card title="Notizen" id="notizen"><FieldList items={[["Anmerkungen (Buchung)", <TrustedHtml value={kid.booking_note} />], ["Anmerkungen", <TrustedHtml value={kid.note} />]]} /><ul>{kid.notes.length ? kid.notes.map(note => <NoteEntry entry={note} childName={kid.full_name} key={note.id} />) : <li>Noch keine Notizen.</li>}</ul></Card>
          <Card title="Erste Hilfe" id="erste-hilfe"><ul>{kid.first_aid_entries?.length ? kid.first_aid_entries.map(entry => <FirstAidEntry entry={entry} childName={kid.full_name} key={entry.id} />) : <li>Noch keine EH-Einträge.</li>}</ul></Card>
          <Card title={`Taschengeld: ${money(kid.remaining_money)}${kid.remaining_money < 5 ? ' 🚨' : ''}`} id="taschengeld"><ul>{kid.transactions.length ? kid.transactions.map(item => <li key={item.id}>{item.author} am {formatGermanDate(item.date)}: {money(item.amount)}</li>) : <li>Dieses Kind ist arm.</li>}</ul></Card>
          <Card title={`Pfand: ${kid.deposit}`} id="pfand"><div className="react-actions deposit-actions"><button className="button" type="button" onClick={() => deposit('increase')}>+ Pfand</button><button className="button" type="button" onClick={() => deposit('decrease')}>− Pfand</button></div></Card>
        </Column>
      </Columns>
      <KidInteractionForm kid={kid} token={data.csrf_token} onSaved={onSaved} />
    </FirstAidGallery>
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
    render: ({ route, data, mutate, refresh }) => <KidDetailPage data={data} id={route.id} mutate={mutate} onSaved={refresh} />,
  },
];
