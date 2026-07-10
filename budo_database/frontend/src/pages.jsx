import { useMemo, useState } from 'react';
import {
  Card,
  Column,
  Columns,
  CsrfInput,
  FieldList,
  findById,
  MapCard,
  NativeForm,
  RestForm,
  SearchTable,
} from './components';

const displayOrPlaceholder = value => value ?? '---';
const yesNo = value => value ? 'Ja' : 'Nein';
const money = value => `${Number(value || 0).toFixed(2)} €`;
const linkKid = kid => <a href={`/kid_details/${kid.id}`}>{kid.full_name}{!kid.present && ' ❌'}</a>;
const TrustedHtml = ({ value }) => value ? <span dangerouslySetInnerHTML={{ __html: value }} /> : '---';

export function AuthPage({ kind, data }) {
  if (kind === 'registered') {
    return <Columns><Column id="single-column"><Card title="Registrieren"><p>Du bist bereits registriert.</p></Card></Column></Columns>;
  }
  const register = kind === 'register';
  return (
    <Columns>
      <Column id="single-column">
        <Card title={register ? 'Registrieren' : 'Login'}>
          <NativeForm token={data.csrf_token} action={register ? '/register/' : '/login/'} fields={register ? [
            { name: 'username', label: 'Username', required: true },
            { name: 'email', label: 'E-Mail', type: 'email', required: true },
            { name: 'password1', label: 'Passwort', type: 'password', required: true },
            { name: 'password2', label: 'Passwort bestätigen', type: 'password', required: true },
            { name: 'passphrase', label: 'Geheime Zugangskennung', type: 'password', required: true },
          ] : [
            { name: 'username', label: 'Username', required: true },
            { name: 'password', label: 'Password', type: 'password', required: true },
          ]} submit={register ? 'Register' : 'Login'} />
        </Card>
      </Column>
    </Columns>
  );
}

export function DashboardPage({ data }) {
  const { profile, team, totals, kids, focuses, activity } = data;
  const firstTimers = kids.filter(kid => kid.budo_experience === false);
  const oneWeek = kids.filter(kid => kid.weeks === 1);
  const health = kids.filter(kid => kid.drugs || kid.illness);
  const food = kids.filter(kid => kid.special_food);
  const birthdays = kids.filter(kid => kid.birthday_during_turnus);
  const goodbyes = kids.filter(kid => kid.age > 14.8).sort((a, b) => a.age - b.age);
  const profileFocuses = focuses.filter(focus => profile.focus_ids.includes(focus.id));
  const kidList = list => <>{list.map(kid => <div className="print-nobreak" key={kid.id}><p><span className="label">{linkKid(kid)}</span>: {kid.age}</p>{kid.illness && <p>Krankheiten: {kid.illness}</p>}{kid.drugs && <p>Medikamente: {kid.drugs}</p>}</div>)}</>;
  return (
    <Columns>
      <Column id="left-column">
        <Card title="Mein Profil" id="db-profil"><FieldList items={[
          ['Rolle', profile.role_display], ['Turnus', data.turnus?.label], ['Essen', profile.food_display],
          ['Allergien', profile.allergies], ['Kaffee', profile.coffee], ['Email', <a href={`mailto:${profile.email}`}>{profile.email}</a>],
          ['Mobil', <a href={`tel:${profile.phone}`}>{profile.phone}</a>],
        ]} /><p><span className="label">Meine Schwerpunkte</span>:</p><ul>{profileFocuses.map(focus => <li key={focus.id}><a href={`/schwerpunkt/${focus.id}/`}>{focus.name}</a></li>)}</ul><a className="button" href="/profil/">Informationen aktualisieren</a></Card>
        <Card title="Team" id="db-team">{team.map(member => <div key={member.id}><p><span className="label"><a href={`/teamer/${member.id}/`}>{member.rufname}</a></span>: {member.food_display}</p>{member.allergies && <li>Allergien: {member.allergies}</li>}<p><span className="label">Geld</span>: {money(member.money_total)}</p></div>)}</Card>
        <Card title="Finanzen" id="db-finanzübersicht"><FieldList items={[["Taschengeld eingezahlt", money(totals.pocket_money_paid)], ["Taschengeld aktuell", money(totals.pocket_money)], ["Betreuerinnen-Geld", money(totals.team_money)]]} /></Card>
      </Column>
      <Column id="center-column">
        <Card title={`Kinder: ${totals.checked_in}`} id="db-kinderübersicht"><FieldList items={[
          ['Eingecheckt', `${totals.checked_in}/${totals.kids}`],
          ['Geschlechter', `${kids.filter(k => k.sex === 'männlich').length} ♂ // ${kids.filter(k => k.sex === 'weiblich').length} ♀ // ${kids.filter(k => !['männlich', 'weiblich'].includes(k.sex)).length} ⚧`],
          ['Kids mit Budo-Erfahrung', kids.filter(k => k.budo_experience).length], ['Zuganreise', totals.train_arrival], ['Zugabreise', totals.train_departure],
        ]} /></Card>
        <Card title="Speziallisten" id="db-spezial"><p><a href="/serienbrief">Serienbrief</a></p><p><a href="/murdergame">Mörderspiel Liste</a></p><p><a href="/zugabreise">Zugabreise</a></p><p><a href="/zuganreise">Zuganreise</a></p><p><a href="/upload/">Turnis</a></p><p><a href="/download-updated-excel/">Aufenthalts-Doku</a></p><p><a href="/swp-einteilung-w1">SWP-Einteilung Woche 1</a></p><p><a href="/swp-einteilung-w2">SWP-Einteilung Woche 2</a></p><p><a href="/happy-cleaning/">Happy Cleaning</a></p><p><a href="/budo_familien/">Budo-Familien</a></p><p><a href="/spezial_familien/">Spezialfamilien</a></p><p><a href="/upload_spezialfamilien/">Spezialfamilien hochladen</a></p><p><a href="/kindergeburtstage/">Kindergeburtstage</a></p></Card>
        <Card title="Notizen" id="db-notizen"><ul>{activity.notes.map(note => <li key={note.id}><p><strong>{note.author}</strong> am {note.day}: <a href={`/kid_details/${note.kid_id}`}>{note.kid}</a></p><p>{note.text}</p></li>)}</ul></Card>
        <Card title="Taschengeld-Transaktionen" id="db-geld"><ul>{activity.transactions.map(item => <li key={item.id}><p><strong>{item.author}</strong> am {item.day}: <a href={`/kid_details/${item.kid_id}`}>{item.kid}</a></p><p>Betrag: {money(item.amount)}</p></li>)}</ul></Card>
      </Column>
      <Column id="right-column">
        <Card title={`Erstes Mal im BuDO: ${firstTimers.length}/${totals.kids}`} id="db-ersties" initiallyClosed>{kidList(firstTimers)}</Card>
        <Card title={`Einwöchige: ${oneWeek.length}`} id="db-einwöchig" initiallyClosed>{kidList(oneWeek)}</Card>
        <Card title="Gesundheitliches" id="db-gesundheit" initiallyClosed>{kidList(health)}</Card>
        <Card title="Essen & Allergien" id="db-essen" initiallyClosed>{food.map(kid => <div className="print-nobreak" key={kid.id}><p>{linkKid(kid)}: {kid.age}</p><p>{kid.food} · {kid.special_food}</p></div>)}</Card>
        <Card title={`Geburtstagskinder: ${birthdays.length}`} id="db-geburtstagskinder">{birthdays.map(kid => <p key={kid.id}>{linkKid(kid)}: {kid.birthday}</p>)}</Card>
        <Card title={`Verabschiedungsliste: ${goodbyes.length}`} id="db-sechzehner">{goodbyes.map(kid => <p key={kid.id}>{linkKid(kid)}: {kid.age} – {kid.birthday}</p>)}</Card>
      </Column>
    </Columns>
  );
}

const kidColumns = [
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

export function KidsPage({ data, query }) {
  const rows = data.kids.map(kid => ({ ...kid, searchText: Object.values(kid).join(' ') }));
  return <main className="table-only" id="body-container"><SearchTable columns={kidColumns} rows={rows} query={query} /></main>;
}

export function KidDetailPage({ data, id, mutate }) {
  const kid = findById(data.kids, id);
  if (!kid) return <NotFoundPage />;
  const deposit = action => mutate('/update_pfand/', { id: kid.id, action });
  return (
    <>
      <Columns>
        <Column id="left-column">
          <Card title={kid.full_name} id="kinderinfos"><FieldList items={[["Geschlecht", kid.sex], ["Alter", kid.age], ["Geburtstag", kid.birthday], ["Aufenthaltsdauer", `${kid.weeks}-wöchig`], ["Geschwister", kid.siblings], ["Zeltwunsch", kid.tent_request], ["War schon mal im Bunten Dorf", yesNo(kid.budo_experience)]]} /></Card>
          <Card title="BuDo" id="budo-container"><FieldList items={[["Turnus", data.turnus?.label], ["Budo Familie", kid.budo_family], ["Haus", kid.special_family], ["SWP 1", kid.focus_w1], ["SWP 2", kid.focus_w2]]} /></Card>
        </Column>
        <Column id="center-column">
          <Card title="Gesundheitsinfos" id="health_info"><FieldList items={[["Sozialversicherungsnummer", kid.social_security_number], ["Krankheiten", displayOrPlaceholder(kid.illness)], ["Medikamente", displayOrPlaceholder(kid.drugs)], ["Vegetarisch", kid.vegetarian], ["Ernährungsvorgaben", kid.special_food], ["Schwimmkenntnisse", kid.swimmer]]} /></Card>
          <Card title="Familie" id="family_info"><FieldList items={[["Organisation", kid.organization], ["Anmelder:in", kid.registrant_name], ["Anmelder:in Email", <a href={`mailto:${kid.registrant_email}`}>{kid.registrant_email}</a>], ["Anmelder:in Mobil", <a href={`tel:${kid.registrant_phone}`}>{kid.registrant_phone}</a>], ["Hauptversichert bei", kid.insured_with], ["Notfallkontakte", kid.emergency_contacts]]} /></Card>
        </Column>
        <Column id="right-column">
          <Card title="Notizen" id="notizen"><FieldList items={[["Anmerkungen (Buchung)", <TrustedHtml value={kid.booking_note} />], ["Anmerkungen", <TrustedHtml value={kid.note} />]]} /><ul>{kid.notes.length ? kid.notes.map(note => <li key={note.id}>{note.author} am {note.day}: {note.text}</li>) : <li>Noch keine Notizen.</li>}</ul></Card>
          <Card title={`Taschengeld: ${money(kid.remaining_money)}${kid.remaining_money < 5 ? ' 🚨' : ''}`} id="taschengeld"><ul>{kid.transactions.length ? kid.transactions.map(item => <li key={item.id}>{item.author} am {item.day}: {money(item.amount)}</li>) : <li>Dieses Kind ist arm.</li>}</ul></Card>
          <Card title={`Pfand: ${kid.deposit}`} id="pfand"><div className="react-actions"><button className="button" type="button" onClick={() => deposit('increase')}>+ Pfand</button><button className="button" type="button" onClick={() => deposit('decrease')}>− Pfand</button></div></Card>
        </Column>
      </Columns>
      <div id="interaction-bar"><RestForm target={`/kid_details/${kid.id}`} token={data.csrf_token}><input name="notiz" placeholder="Notiz..." /><input name="amount" type="number" step="0.01" placeholder="Taschengeld..." /><button type="submit">➤</button></RestForm></div>
    </>
  );
}

export function CheckPage({ data, id, checkout = false }) {
  const kid = findById(data.kids, id);
  if (!kid) return <NotFoundPage />;
  const fields = checkout ? [
    { name: 'early_abreise_date', label: 'Abreisedatum', type: 'date', value: new Date().toISOString().slice(0, 10), required: true },
    { name: 'notiz', label: 'Notiz' },
    { name: 'amount', label: 'Taschengeld', type: 'number', step: '0.01', value: -kid.pocket_money },
  ] : [
    { name: 'check_in_date', label: 'Check-in Datum', type: 'date', value: new Date().toISOString().slice(0, 10), required: true },
    { name: 'ausweis', label: 'Ausweis', type: 'checkbox', value: kid.id_card },
    { name: 'e_card', label: 'E-Card', type: 'checkbox', value: kid.e_card },
    { name: 'einverstaendnis_erklaerung', label: 'Einverständniserklärung', type: 'checkbox', value: kid.consent },
    { name: 'notiz', label: 'Notiz' },
    { name: 'amount', label: 'Taschengeld', type: 'number', step: '0.01' },
  ];
  return <Columns><Column id="single-column"><Card title={`${checkout ? 'Check-Out' : 'Check-In'}: ${kid.full_name}`}><p style={{ color: checkout ? 'green' : 'red' }}>{kid.full_name} ist {checkout ? 'anwesend.' : 'noch nicht eingecheckt!'}</p>{checkout && <><p>Wir hatten vom Kind folgendes:</p><ul>{kid.e_card && <li>E-Card</li>}{kid.id_card && <li>Ausweis</li>}{kid.consent && <li>Einverständniserklärung</li>}{kid.pocket_money > 0 && <li>Taschengeld: {money(kid.pocket_money)}</li>}</ul></>}<NativeForm token={data.csrf_token} action={`/${checkout ? 'check_out' : 'check_in'}/${kid.id}`} fields={fields} submit={checkout ? 'Auschecken' : 'Einchecken'} /></Card></Column></Columns>;
}

export function TrainPage({ data, query, departure, mutate }) {
  const source = departure ? [...data.kids].sort((a, b) => Number(b.train_departure) - Number(a.train_departure)) : data.kids.filter(kid => kid.train_arrival);
  const rows = source.map(kid => ({ ...kid, searchText: `${kid.full_name} ${kid.registrant_name} ${kid.registrant_phone} ${kid.siblings}` }));
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
  return <><div className="print_only"><h1>{departure ? 'Zugabreise' : 'Zuganreise'}</h1><p>Kinder: {rows.length}</p></div><main className="table-only" id="body-container"><SearchTable columns={columns} rows={rows} query={query} /></main></>;
}

export function SerialLetterPage({ data }) {
  return <main>{data.kids.map(kid => <div className="serienbrief-kid" key={kid.id}><div className="serienbrief_name">{kid.full_name}</div><div className="serienbrief-container"><div className="serienbrief">E-Card: {yesNo(kid.e_card)}</div><div className="serienbrief">Ausweis: {yesNo(kid.id_card)}</div></div><div className="serienbrief-container"><div className="serienbrief">Einverständnis für ärztliche Behandlung: {yesNo(kid.consent)}</div><div className="serienbrief">Rezeptfreie Medikamente: {displayOrPlaceholder(kid.over_the_counter_medication)}</div><div className="serienbrief">Medikamente auf Rezept: {displayOrPlaceholder(kid.prescription_medication)}</div></div><div className="serienbrief-container"><div className="serienbrief">Tetanusimpfung: {displayOrPlaceholder(kid.tetanus)}</div><div className="serienbrief">Zeckenimpfung: {displayOrPlaceholder(kid.tick_vaccine)}</div></div><div className="serienbrief-container"><div className="serienbrief">Krankheit: {displayOrPlaceholder(kid.illness)}</div><div className="serienbrief">Medikamente: {displayOrPlaceholder(kid.drugs)}</div><div className="serienbrief">Ernährung: {displayOrPlaceholder(kid.special_food)}</div></div></div>)}</main>;
}

export function MurderPage({ data }) {
  return <main><h2 className="murder_name">Mörderspiel: Kids & Team</h2><div className="murder-container">{data.kids.filter(kid => kid.present).map(kid => <div className="murder_name" key={`kid-${kid.id}`}>{kid.full_name}</div>)}{data.team.map(member => <div className="murder_name" key={`team-${member.id}`}>{member.role_display} {member.rufname}</div>)}</div></main>;
}

const focusKidColumns = kidColumns.filter(column => ['name', 'budo_family', 'sex_short', 'age', 'food', 'drugs', 'illness'].includes(column.key));

export function FocusDashboardPage({ data }) {
  const group = week => data.focuses.filter(focus => focus.week === week);
  const columns = [{ key: 'name', label: 'Name', render: focus => <a href={`/schwerpunkt/${focus.id}/`}>{focus.name}</a> }, { key: 'place', label: 'Ort', render: focus => focus.place || '---' }, { key: 'carers', label: 'Betreuende', render: focus => focus.carers || '---' }, { key: 'off_site', label: 'Auslagern', render: focus => yesNo(focus.off_site) }, { key: 'kids', label: 'Kinder', render: focus => focus.kid_ids.length }, { key: 'meals', label: 'Essenseinteilung', render: focus => focus.meal_items.some(meal => meal.choice) ? 'Ja' : 'Nein' }, { key: 'actions', label: 'Aktionen', render: focus => <a href={`/schwerpunkt/${focus.id}/update`}>✏️</a> }];
  const tables = [['u', 'Unklar Wann'], ['w1', 'Woche 1'], ['w2', 'Woche 2']].filter(([week]) => group(week).length || week !== 'u');
  return <Columns><Column id="left-column"><MapCard places={data.focuses.filter(focus => focus.coordinates).map(focus => ({ id: focus.id, name: focus.name, coordinates: focus.coordinates, href: `/schwerpunkt/${focus.id}/` }))} /></Column><Column id="right-column" className="normal-column">{tables.map(([week, title]) => <Card title={title} className="transparent" key={week}><SearchTable columns={columns} rows={group(week).map(focus => ({ ...focus, searchText: focus.name }))} />{week !== 'u' && <div className="react-actions"><a className="button" href={`/swp-einteilung-${week}`}>Kinder einteilen</a></div>}</Card>)}</Column></Columns>;
}

export function FocusDetailPage({ data, id }) {
  const focus = findById(data.focuses, id);
  if (!focus) return <NotFoundPage />;
  const kids = data.kids.filter(kid => focus.kid_ids.includes(kid.id)).map(kid => ({ ...kid, searchText: kid.full_name }));
  return <Columns><Column id="left-column"><Card title={focus.name}><FieldList items={[["Beschreibung", focus.description], ["Kinder", kids.length], ["Ort", focus.place], ["Auslagern", yesNo(focus.off_site)], ["Betreuende", focus.carers], ["Wann", focus.time], ["Beginnt am", focus.start]]} /><MealTable focus={focus} /><div className="react-actions"><a className="button" href={`/schwerpunkt/${focus.id}/update`}>SWP bearbeiten</a><a className="button" href={`/swpmeals/${focus.id}`}>Essen bearbeiten</a></div></Card><MapCard places={focus.place_id ? data.places.filter(place => place.id === focus.place_id) : []} /></Column><Column id="right-column"><SearchTable columns={focusKidColumns} rows={kids} /></Column></Columns>;
}

function MealTable({ focus }) {
  return <div className="card-table-container"><table className="card-table"><thead><tr><th /><th>Frühstück</th><th>Mittagessen</th><th>Abendessen</th></tr></thead><tbody>{Object.entries(focus.meals).map(([day, meals]) => <tr key={day}><td>Tag {day}</td><td>{displayOrPlaceholder(meals.breakfast)}</td><td>{displayOrPlaceholder(meals.lunch)}</td><td>{displayOrPlaceholder(meals.dinner)}</td></tr>)}</tbody></table></div>;
}

export function FocusFormPage({ data, id }) {
  const focus = id ? findById(data.focuses, id) : null;
  const fields = [
    { name: 'swp_name', label: 'Schwerpunktname', value: focus?.name, required: true },
    { name: 'ort', label: 'Ort', type: 'select', value: focus?.place_id, options: [{ value: '', label: '---------' }, ...data.places.map(item => ({ value: item.id, label: item.name }))] },
    { name: 'betreuende', label: 'Betreuende', type: 'select', multiple: true, value: focus?.carer_ids, options: data.team.map(item => ({ value: item.id, label: item.rufname })) },
    { name: 'beschreibung', label: 'Beschreibung', type: 'textarea', value: focus?.description },
    { name: 'schwerpunktzeit', label: 'Schwerpunktzeit', type: 'select', value: focus?.time_id, options: data.focus_times.map(item => ({ value: item.id, label: item.label })) },
    { name: 'auslagern', label: 'Auslagern', type: 'checkbox', value: focus?.off_site },
    { name: 'geplante_abreise', label: 'Geplante Abreise', type: 'datetime-local', value: focus?.departure?.slice(0, 16) },
    { name: 'geplante_ankunft', label: 'Geplante Ankunft', type: 'datetime-local', value: focus?.arrival?.slice(0, 16) },
  ];
  return <Columns><Column id="single-column"><Card title={`Schwerpunkt ${focus ? 'updaten' : 'erstellen'}`}><NativeForm token={data.csrf_token} action={focus ? `/schwerpunkt/${focus.id}/update` : '/schwerpunkt/create'} fields={fields} /></Card></Column></Columns>;
}

export function MealsPage({ data, id }) {
  const focus = findById(data.focuses, id);
  if (!focus) return <NotFoundPage />;
  const entries = focus.meal_items;
  return <Columns><Column id="single-column"><Card title="Wann esst ihr wo?"><RestForm target={`/swpmeals/${focus.id}`} token={data.csrf_token} className="form-grid"><input type="hidden" name="form-TOTAL_FORMS" value={entries.length} /><input type="hidden" name="form-INITIAL_FORMS" value={entries.length} />{entries.map((meal, index) => <label key={meal.id}>Tag {meal.day} · {{ breakfast: 'Frühstück', lunch: 'Mittagessen', dinner: 'Abendessen' }[meal.type]}<input type="hidden" name={`form-${index}-id`} value={meal.id} /><select name={`form-${index}-meal_choice`} defaultValue={meal.choice}><option value="">---------</option><option value="box">Box</option><option value="budo">Im BuDo</option><option value="warm">Warm geliefert</option></select></label>)}<input className="button" type="submit" value="Speichern" /></RestForm></Card></Column></Columns>;
}

export function PlacesPage({ data, query }) {
  const rows = data.places.map(place => ({ ...place, searchText: `${place.name} ${place.city} ${place.state}` }));
  const columns = [
    { key: 'name', label: 'Name', render: row => <a href={`/auslagerorte/${row.id}/`}>{row.name}</a> },
    { key: 'maps_link', label: 'Wo', render: row => row.maps_link ? <a href={row.maps_link}>Google Maps</a> : '---' },
    { key: 'parking_link', label: 'Parkspot', render: row => row.parking_link ? <a href={row.parking_link}>Google Maps</a> : '---' },
    { key: 'actions', label: 'Aktionen', render: row => <><a href={`/auslagerorte/${row.id}/update`}>✏️</a> <a href={`/auslagerorte/${row.id}/`}>👁️</a></> },
  ];
  return <Columns><Column id="left-column" className="normal-column"><SearchTable columns={columns} rows={rows} query={query} /></Column><Column id="right-column"><MapCard places={data.places} /></Column></Columns>;
}

export function PlaceDetailPage({ data, id }) {
  const place = findById(data.places, id);
  if (!place) return <NotFoundPage />;
  return <><Columns className="auslagerorte-detail"><Column id="left-column"><Card title={place.name}><FieldList items={[["Name", place.name], ["Beschreibung", place.description], ["Koordinaten", place.coordinates], ["Google Maps Link", place.maps_link && <a href={place.maps_link}>Link</a>], ["Google Maps Link Parkspot", place.parking_link && <a href={place.parking_link}>Link</a>], ["Koordinaten Parkspot", place.parking_coordinates], ["Straße", place.street], ["Stadt", place.city], ["Bundesland", place.state], ["Postleitzahl", place.postal_code], ["Land", place.country]]} /><a className="button" href={`/auslagerorte/${place.id}/update`}>Ort bearbeiten</a></Card><Card title="Kommentare"><ul>{place.notes.map(note => <li key={note.id}><strong>{note.author}</strong> am {note.day}: {note.text}</li>)}</ul></Card></Column><Column id="right-column"><Card title="Bilder"><div className="gallery-container">{place.images.map((src, index) => <div className="gallery-item" key={src}><img src={src} alt={`${place.name} ${index + 1}`} /></div>)}</div><a className="button" href={`/auslagerorte/${place.id}/upload-image/`}>Bilder hochladen</a></Card><MapCard places={[place]} /></Column></Columns><div id="interaction-bar"><RestForm target={`/auslagerorte/${place.id}/`} token={data.csrf_token}><input name="notiz" placeholder="Kommentar..." /><button type="submit">➤</button></RestForm></div></>;
}

export function PlaceFormPage({ data, id }) {
  const place = id ? findById(data.places, id) : null;
  const keys = { name: 'name', strasse: 'street', ort: 'city', bundesland: 'state', postleitzahl: 'postal_code', land: 'country', maps_link: 'maps_link', beschreibung: 'description', maps_link_parkspot: 'parking_link' };
  const fields = [['name', 'Name'], ['strasse', 'Straße'], ['ort', 'Stadt'], ['bundesland', 'Bundesland'], ['postleitzahl', 'Postleitzahl'], ['land', 'Land'], ['maps_link', 'Google Maps Link'], ['beschreibung', 'Beschreibung', 'textarea'], ['maps_link_parkspot', 'Google Maps Link Parkspot']].map(([name, label, type]) => ({ name, label, type, value: place?.[keys[name]] }));
  return <Columns><Column id="single-column"><Card title={`Auslagerort ${place ? 'updaten' : 'erstellen'}`}><NativeForm token={data.csrf_token} action={place ? `/auslagerorte/${place.id}/update` : '/auslagerorte/create'} fields={fields} /></Card></Column></Columns>;
}

export function ImageUploadPage({ data, id }) {
  const place = findById(data.places, id);
  return <Columns><Column id="single-column"><Card title={`Upload Images for ${place?.name || ''}`}><NativeForm token={data.csrf_token} action={`/auslagerorte/${id}/upload-image/`} encType="multipart/form-data" fields={[{ name: 'images', label: 'Select multiple images', type: 'file', multiple: true }]} submit="Upload" /></Card></Column></Columns>;
}

export function KitchenPage({ data }) {
  const weeks = ['w1', 'w2'];
  return <Columns><Column id="left-column">{weeks.map(week => <Card title={`Menüplan Woche ${week === 'w1' ? 1 : 2}`} key={week}><WeekMealPlan focuses={data.focuses.filter(focus => focus.week === week)} /></Card>)}</Column><Column id="center-column"><Card title="Essen & Allergien">{data.kids.filter(kid => kid.special_food).map(kid => <div className="print-nobreak" key={kid.id}><p>{linkKid(kid)} · {kid.food}</p><p>{kid.special_food}</p></div>)}</Card><Card title="Team">{data.team.map(member => <p key={member.id}>{member.rufname}: {member.food_display}{member.allergies && ` · ${member.allergies}`}</p>)}</Card></Column><Column id="right-column">{weeks.map(week => <Card title={`Schwerpunktinfos Woche ${week === 'w1' ? 1 : 2}`} key={week}>{data.focuses.filter(f => f.week === week).map(focus => <div key={focus.id}><h2>{focus.name}</h2><FieldList items={[["Kinder", focus.kid_ids.length], ["Betreuende", focus.carers], ["Ort", focus.place]]} /><MealTable focus={focus} /></div>)}</Card>)}</Column></Columns>;
}

function WeekMealPlan({ focuses }) {
  const maxDays = Math.max(0, ...focuses.map(focus => focus.duration));
  const types = [['breakfast', 'Frühstück'], ['lunch', 'Mittagessen'], ['dinner', 'Abendessen']];
  const cell = (day, type, choice) => focuses.filter(focus => focus.meal_items.some(meal => meal.day === day && meal.type === type && meal.choice === choice)).map(focus => `${focus.name} (${focus.kid_ids.length})`);
  return <>{Array.from({ length: maxDays }, (_, index) => index + 1).map(day => <div className="print-nobreak" key={day}><h2>Tag {day}</h2><table className="meal-table"><thead><tr><th>Essen</th><th>Box</th><th>BuDo</th><th>Warm</th><th>Kochportionen</th></tr></thead><tbody>{types.map(([type, label]) => { const budo = cell(day, type, 'budo'); const warm = cell(day, type, 'warm'); const portions = focuses.filter(focus => [...budo, ...warm].some(value => value.startsWith(`${focus.name} (`))).reduce((sum, focus) => sum + focus.kid_ids.length, 0); return <tr key={type}><td>{label}</td><td>{cell(day, type, 'box').join(', ') || '---'}</td><td>{budo.join(', ') || '---'}</td><td>{warm.join(', ') || '---'}</td><td>{portions || '---'}</td></tr>; })}</tbody></table></div>)}</>;
}

export function AllocationPage({ data, week, query, mutate }) {
  const focuses = data.focuses.filter(focus => focus.week === `w${week}`);
  const rows = data.kids.map(kid => ({ ...kid, searchText: `${kid.full_name} ${kid.choices.map(c => c.friends).join(' ')}` }));
  const columns = [
    { key: 'name', label: 'Name', render: linkKid },
    { key: 'assigned', label: 'Einteilung', render: kid => <select value={kid.focus_ids.find(id => focuses.some(f => f.id === id)) || ''} onChange={event => event.target.value && mutate('/update-schwerpunkt-wahl/', { kid_id: kid.id, swp_id: Number(event.target.value), choice_rank: null })}><option value="">Nicht zugeordnet</option>{focuses.map(focus => <option value={focus.id} key={focus.id}>{focus.name}</option>)}</select> },
    ...focuses.map(focus => ({ key: `focus-${focus.id}`, label: focus.name, render: kid => { const choice = kid.choices.find(item => item.week === `w${week}`); return <span className="swp-choice">{['1', '2', '3'].map(rank => <button className={Number(choice?.[{ 1: 'first', 2: 'second', 3: 'third' }[rank]]) === focus.id ? 'active' : ''} type="button" key={rank} onClick={() => mutate('/update-schwerpunkt-wahl/', { kid_id: kid.id, swp_id: focus.id, choice_rank: rank })}>{rank}</button>)}</span>; } })),
    { key: 'friends', label: 'Freunde', render: kid => { const friends = kid.choices.find(c => c.week === `w${week}`)?.friends || ''; return <>{friends || '---'} <button type="button" onClick={() => { const value = window.prompt('Freunde bearbeiten', friends); if (value !== null) mutate('/update_freunde/', { kid_id: kid.id, freunde: value }); }}>✏️</button></>; } },
    { key: 'age', label: 'Alter' },
    { key: 'siblings', label: 'Geschwister', render: kid => displayOrPlaceholder(kid.siblings) },
  ];
  return <Columns><Column id="left-column">{focuses.map(focus => <Card title={`${focus.name}: ${focus.kid_ids.length}`} key={focus.id}><ul>{data.kids.filter(kid => focus.kid_ids.includes(kid.id)).map(kid => <li key={kid.id}>{linkKid(kid)}</li>)}</ul></Card>)}</Column><Column id="right-column"><SearchTable columns={columns} rows={rows} query={query} /></Column></Columns>;
}

export function FamiliesPage({ data, special = false }) {
  const groups = useMemo(() => data.kids.reduce((result, kid) => { const key = special ? kid.special_family : kid.budo_family; if (key) (result[key] ||= []).push(kid); return result; }, {}), [data.kids, special]);
  return <Columns>{Object.entries(groups).map(([name, kids]) => <Column key={name}><Card title={`${name} (${kids.length})`}><ul>{kids.map(kid => <li key={kid.id}>{linkKid(kid)} – {kid.age}</li>)}</ul></Card></Column>)}</Columns>;
}

function svBirthday(kid) {
  const cleaned = (kid.social_security_number || '').replace(/\D/g, '');
  if (cleaned.length < 10) return null;
  const part = cleaned.slice(-6); const year = Number(part.slice(4)) < 50 ? 2000 + Number(part.slice(4)) : 1900 + Number(part.slice(4));
  const value = `${year}-${part.slice(2, 4)}-${part.slice(0, 2)}`;
  return Number.isNaN(Date.parse(value)) ? null : value;
}

export function BirthdaysPage({ data, query }) {
  const rows = data.kids.map(kid => ({ ...kid, sv: svBirthday(kid), searchText: `${kid.full_name} ${kid.birthday}` }));
  const columns = [
    { key: 'name', label: 'Name', render: linkKid },
    { key: 'birthday', label: 'DB-Geburtstag', render: row => displayOrPlaceholder(row.birthday) },
    { key: 'sv', label: 'SV-Geburtstag', render: row => displayOrPlaceholder(row.sv) },
    { key: 'match', label: 'Check', render: row => row.birthday && row.sv ? row.birthday === row.sv ? '✅' : '❌' : '---' },
    { key: 'note', label: 'Notiz', render: row => <RestForm target="/kindergeburtstage/" token={data.csrf_token}><input type="hidden" name="kid_id" value={row.id} /><input name="notiz" placeholder="Notiz..." /><button className="button" type="submit">Speichern</button></RestForm> },
  ];
  return <main className="table-only" id="body-container"><SearchTable columns={columns} rows={rows} query={query} /></main>;
}

export function TeamerPage({ data, id }) {
  const profile = findById(data.team, id);
  if (!profile) return <NotFoundPage />;
  return <Columns><Column id="left-column"><Card title={profile.rufname}><FieldList items={[["Rolle", profile.role_display], ["Turnus", data.turnus?.label], ["Essen", profile.food_display], ["Allergien", profile.allergies], ["Kaffee", profile.coffee], ["Email", <a href={`mailto:${profile.email}`}>{profile.email}</a>], ["Mobil", <a href={`tel:${profile.phone}`}>{profile.phone}</a>]]} /></Card></Column><Column id="center-column"><Card title={`Abrechnung: ${money(profile.money_total)}`}><ul>{profile.money_items.length ? profile.money_items.map(item => <li key={item.id}>{profile.rufname} am {item.day}: {item.what} – {money(item.amount)}</li>) : <li>Keine Transaktionen bisher...</li>}</ul><NativeForm token={data.csrf_token} action={`/teamer/${profile.id}/`} fields={[{ name: 'amount', label: 'Betrag in €', type: 'number', step: '0.01' }, { name: 'what', label: 'Beschreibung' }]} /></Card></Column></Columns>;
}

export function ProfilePage({ data }) {
  const profile = data.profile;
  return <Columns><Column id="single-column"><Card title="Profil"><NativeForm token={data.csrf_token} action="/profil/" fields={[
    { name: 'rufname', label: 'Rufname', value: profile.rufname },
    { name: 'allergien', label: 'Allergien', value: profile.allergies },
    { name: 'coffee', label: 'Kaffee', value: profile.coffee },
    { name: 'rolle', label: 'Rolle', type: 'select', value: profile.role, options: [{ value: 'b', label: 'Betreuer:in' }, { value: 'k', label: 'Küche' }, { value: 'o', label: 'Organisator' }, { value: 'f', label: 'Freiwillige:r' }] },
    { name: 'essen', label: 'Essen', type: 'select', value: profile.food, options: [{ value: 'ft', label: 'Flexitarisch' }, { value: 'vt', label: 'Vegetarisch' }, { value: 'vn', label: 'Vegan' }] },
    { name: 'telefonnummer', label: 'Telefonnummer', value: profile.phone },
    { name: 'turnus', label: 'Turnus', type: 'select', value: data.turnus?.id, options: data.turnuses.map(item => ({ value: item.id, label: item.label })) },
  ]} /></Card></Column></Columns>;
}

export function TurnusUploadPage({ data, id }) {
  const turnus = id ? findById(data.turnuses, id) : null;
  return <Columns><Column id="single-column"><Card title={turnus ? `Excel-Datei hochladen für Turnus ${turnus.number}` : 'Turnis'}><NativeForm token={data.csrf_token} action={turnus ? `/upload_excel/${turnus.id}/` : '/upload/'} encType="multipart/form-data" fields={[{ name: 'turnus_nr', label: 'Turnus Nummer', type: 'number', value: turnus?.number, required: true }, { name: 'turnus_beginn', label: 'Beginn des Turnus', type: 'date', value: turnus?.start, required: true }, { name: 'uploadedFile', label: 'Excel-File', type: 'file' }]} submit={turnus ? 'Hochladen' : 'Turnus hinzufügen'} /></Card>{!turnus && <SearchTable columns={[{ key: 'label', label: 'Turnus' }, { key: 'id', label: 'ID' }, { key: 'start', label: 'Turnusbeginn' }, { key: 'actions', label: 'Aktionen', render: row => <a className="button" href={`/upload_excel/${row.id}/`}>Excel hochladen</a> }]} rows={data.turnuses.map(item => ({ ...item, searchText: item.label }))} />}</Column></Columns>;
}

export function SimpleUploadPage({ data }) {
  return <Columns><Column id="single-column"><Card title="Upload XLSX"><NativeForm token={data.csrf_token} action="/upload_spezialfamilien/" encType="multipart/form-data" fields={[{ name: 'csv_file', label: 'Datei', type: 'file', required: true }]} submit="Hochladen" /></Card></Column></Columns>;
}

export function KidCountPage({ data }) {
  return <main><h1 className="gesamtkinderzahl">{data.totals.checked_in}/{data.totals.kids}</h1></main>;
}

export function NotFoundPage() {
  return <Columns><Column id="single-column"><Card title="Seite nicht gefunden"><p>Für diese Adresse gibt es keine React-Seite.</p><a className="button" href="/dashboard/">Zum Dashboard</a></Card></Column></Columns>;
}
