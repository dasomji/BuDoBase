import { Card, Column, Columns, FieldList } from '../components';
import { formatGermanDate, formatKidBirthday, linkKid, money } from './shared';

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
        <Card title="Notizen" id="db-notizen"><ul>{activity.notes.map(note => <li key={note.id}><p><strong>{note.author}</strong> am {formatGermanDate(note.date)}: <a href={`/kid_details/${note.kid_id}`}>{note.kid}</a></p><p>{note.text}</p></li>)}</ul></Card>
        <Card title="Taschengeld-Transaktionen" id="db-geld"><ul>{activity.transactions.map(item => <li key={item.id}><p><strong>{item.author}</strong> am {formatGermanDate(item.date)}: <a href={`/kid_details/${item.kid_id}`}>{item.kid}</a></p><p>Betrag: {money(item.amount)}</p></li>)}</ul></Card>
      </Column>
      <Column id="right-column">
        <Card title={`Erstes Mal im BuDO: ${firstTimers.length}/${totals.kids}`} id="db-ersties" initiallyClosed>{kidList(firstTimers)}</Card>
        <Card title={`Einwöchige: ${oneWeek.length}`} id="db-einwöchig" initiallyClosed>{kidList(oneWeek)}</Card>
        <Card title="Gesundheitliches" id="db-gesundheit" initiallyClosed>{kidList(health)}</Card>
        <Card title="Essen & Allergien" id="db-essen" initiallyClosed>{food.map(kid => <div className="print-nobreak" key={kid.id}><p>{linkKid(kid)}: {kid.age}</p><p>{kid.food} · {kid.special_food}</p></div>)}</Card>
        <Card title={`Geburtstagskinder: ${birthdays.length}`} id="db-geburtstagskinder">{birthdays.map(kid => <p key={kid.id}>{linkKid(kid)}: {formatKidBirthday(kid)}</p>)}</Card>
        <Card title={`Verabschiedungsliste: ${goodbyes.length}`} id="db-sechzehner">{goodbyes.map(kid => <p key={kid.id}>{linkKid(kid)}: {kid.age} – {formatKidBirthday(kid)}</p>)}</Card>
      </Column>
    </Columns>
  );
}

export const dashboardRoutes = [{
  pattern: /^\/$|^\/dashboard$/,
  page: 'dashboard',
  title: 'BuDo Dashboard',
  domain: 'dashboard',
  readContractKey: 'dashboard',
  render: ({ data }) => <DashboardPage data={data} />,
}];
