import { Card, Column, Columns } from '../components';

export const displayOrPlaceholder = value => value ?? '---';
export const yesNo = value => value ? 'Ja' : 'Nein';
export const requiredHealthValue = value => value === null || value === undefined || (typeof value === 'string' && !value.trim()) ? '❗' : value;
export const requiredHealthYesNo = value => value === null || value === undefined ? '❗' : yesNo(value);
export const money = value => `${Number(value || 0).toFixed(2)} €`;
export const linkKid = kid => <a href={`/kid_details/${kid.id}`}>{kid.full_name}{!kid.present && ' ❌'}</a>;
export const TrustedHtml = ({ value }) => value ? <span dangerouslySetInnerHTML={{ __html: value }} /> : '---';

export function formatGermanDate(value) {
  if (!value) return value;
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})(?:$|T)/);
  return match ? `${match[3]}.${match[2]}.${match[1]}` : value;
}

export function calculatedBirthdayFromSv(kid) {
  const cleaned = (kid.social_security_number || '').replace(/\D/g, '');
  if (cleaned.length < 10) return null;
  const part = cleaned.slice(-6);
  const day = Number(part.slice(0, 2));
  const month = Number(part.slice(2, 4));
  const shortYear = Number(part.slice(4));
  const year = shortYear < 50 ? 2000 + shortYear : 1900 + shortYear;
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

export function formatKidBirthday(kid) {
  const birthday = formatGermanDate(kid.birthday);
  if (!birthday) return birthday;
  const calculatedBirthday = calculatedBirthdayFromSv(kid);
  return `${birthday}${calculatedBirthday && calculatedBirthday !== kid.birthday ? ' ❗' : ''}`;
}

export function MealTable({ focus }) {
  return <div className="card-table-container"><table className="card-table"><thead><tr><th /><th>Frühstück</th><th>Mittagessen</th><th>Abendessen</th></tr></thead><tbody>{Object.entries(focus.meals).map(([day, meals]) => <tr key={day}><th className="meal-day" scope="row">Tag {day}</th><td>{displayOrPlaceholder(meals.breakfast)}</td><td>{displayOrPlaceholder(meals.lunch)}</td><td>{displayOrPlaceholder(meals.dinner)}</td></tr>)}</tbody></table></div>;
}

export function NotFoundPage() {
  return <Columns><Column id="single-column"><Card title="Seite nicht gefunden"><p>Für diese Adresse gibt es keine React-Seite.</p><a className="button" href="/dashboard/">Zum Dashboard</a></Card></Column></Columns>;
}

export const notFoundRoute = {
  page: 'not-found',
  title: 'Seite nicht gefunden',
  domain: 'not-found',
  readContractKey: null,
  render: () => <NotFoundPage />,
};
