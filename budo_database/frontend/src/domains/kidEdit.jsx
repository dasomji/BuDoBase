import { useMemo, useRef, useState } from 'react';

import { Card, Columns, ConfirmationDialog } from '../components';
import { Button } from '../components/ui/button';
import { Input, NativeSelect, Textarea } from '../components/ui/input';
import { useErrorToast, useSuccessToast } from '../components/ui/toast';
import { KID_EDIT_SECTIONS } from './kidEditFields';

const SECTIONS = KID_EDIT_SECTIONS.map(({ title, fields }) => [
  title,
  fields.map(({ name, label, kind }) => [name, label, kind]),
]);

const FIELD_NAMES = SECTIONS.flatMap(([, fields]) => fields.map(([name]) => name));
const FIELD_KIND = Object.fromEntries(SECTIONS.flatMap(([, fields]) => fields.map(([name, , kind]) => [name, kind])));
const FIELD_CARD = Object.fromEntries(SECTIONS.flatMap(([card, fields]) => fields.map(([name]) => [name, card])));
const encoded = value => JSON.stringify(value);

function requestId() {
  const alphabet = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
  const bytes = new Uint8Array(26);
  if (globalThis.crypto?.getRandomValues) globalThis.crypto.getRandomValues(bytes);
  else for (let index = 0; index < bytes.length; index += 1) bytes[index] = Math.floor(Math.random() * 256);
  return Array.from(bytes, value => alphabet[value % alphabet.length]).join('');
}

function EditField({ name, label, kind, value, options, errors, onChange, inputRef }) {
  const domName = name.replaceAll('.', '-');
  const id = `kid-edit-${domName}`;
  const errorId = `${id}-error`;
  const common = {
    id, name, ref: inputRef,
    value: value ?? '',
    required: name === 'first_name' || name === 'last_name',
    'aria-invalid': errors?.length ? 'true' : undefined,
    'aria-describedby': errors?.length ? errorId : undefined,
    onChange: event => onChange(name, event.target.value),
  };
  let control;
  if (kind === 'select') {
    control = (
      <NativeSelect {...common}>
        {(options || []).map(option => {
          const optionValue = encoded(option.target ?? option.value);
          return <option disabled={option.can_select === false} key={optionValue} value={optionValue}>{option.label}</option>;
        })}
      </NativeSelect>
    );
  } else if (kind === 'textarea') control = <Textarea {...common} rows={3} />;
  else control = <Input {...common} type={kind} />;
  return (
    <div className="min-w-0">
      <label className="mb-1 block font-medium" htmlFor={id}>{label}{common.required ? ' *' : ''}</label>
      {control}
      {errors?.length ? <p className="mt-1 text-sm text-destructive" id={errorId}>{errors.map(error => error.message).join(' ')}</p> : null}
    </div>
  );
}

function DiscardDialog({ cancel, discard }) {
  return (
    <ConfirmationDialog
      open
      title="Änderungen verwerfen?"
      confirmLabel="Verwerfen"
      cancelLabel="Weiter bearbeiten"
      onConfirm={discard}
      onCancel={cancel}
      destructive
    >
      <p>Nicht gespeicherte Änderungen gehen verloren.</p>
    </ConfirmationDialog>
  );
}

export function KidEditPage({ data, mutate, navigate }) {
  const { kid } = data;
  const initial = useMemo(() => ({
    ...kid.fields,
    ...Object.fromEntries(kid.swp_periods.map(period => [`swp.${period.id}`, encoded(period.target)])),
    happy_cleaning_number: kid.happy_cleaning_number.value,
    ...Object.fromEntries(kid.happy_cleaning_events.map(event => [`happy_cleaning.${event.id}`, encoded(event.target)])),
  }), [kid]);
  const [values, setValues] = useState(initial);
  const [errors, setErrors] = useState({});
  const [expanded, setExpanded] = useState(Object.fromEntries(SECTIONS.map(([name]) => [name, true])));
  const [discarding, setDiscarding] = useState(false);
  const controls = useRef({});
  const showError = useErrorToast();
  const showSuccess = useSuccessToast();
  const dynamicNames = [
    ...kid.swp_periods.map(period => `swp.${period.id}`),
    'happy_cleaning_number',
    ...kid.happy_cleaning_events.map(event => `happy_cleaning.${event.id}`),
  ];
  const controlOrder = [...FIELD_NAMES, ...dynamicNames];
  const fieldErrors = Object.fromEntries(Object.entries(errors).filter(([name]) => controlOrder.includes(name)));
  const firstInvalid = controlOrder.find(name => fieldErrors[name]);
  const dirty = JSON.stringify(values) !== JSON.stringify(initial);
  const cardFor = name => FIELD_CARD[name] || 'BuDo';
  const update = (name, raw) => {
    let value = raw;
    if (name === 'happy_cleaning_number') value = raw === '' ? null : Number(raw);
    else if (FIELD_KIND[name] === 'select') value = JSON.parse(raw);
    setValues(current => ({ ...current, [name]: value }));
    setErrors(current => {
      const next = { ...current };
      delete next[name];
      return next;
    });
  };
  const submit = async event => {
    event.preventDefault();
    setErrors({});
    const payload = {
      request_id: requestId(),
      expected_edit_version: kid.edit_version,
      field_baselines: { ...kid.field_baselines },
      fields: Object.fromEntries(FIELD_NAMES.map(name => [name, values[name]])),
      swp: kid.swp_periods.map(period => ({ period_id: period.id, baseline: period.baseline, target: JSON.parse(values[`swp.${period.id}`]) })),
      happy_cleaning_number: values.happy_cleaning_number,
      expected_number_version: kid.happy_cleaning_number.version,
      happy_cleaning: kid.happy_cleaning_events.map(eventItem => ({
        event_id: eventItem.id,
        expected_assignment_version: eventItem.assignment_version,
        target: JSON.parse(values[`happy_cleaning.${eventItem.id}`]),
      })),
    };
    try {
      const result = await mutate(`/api/kids/${kid.id}/edit/`, payload);
      showSuccess('Alle Daten und Einteilungen wurden gespeichert.');
      navigate(result.redirect || `/kid_details/${kid.id}`);
    } catch (caught) {
      const incoming = caught?.payload?.errors || {};
      const addressed = Object.fromEntries(Object.entries(incoming).filter(([name]) => controlOrder.includes(name)));
      if (Object.keys(addressed).length) {
        setErrors(addressed);
        setExpanded(current => ({ ...current, ...Object.fromEntries(Object.keys(addressed).map(name => [cardFor(name), true])) }));
        const first = controlOrder.find(name => addressed[name]);
        window.setTimeout(() => controls.current[first]?.focus(), 0);
      } else showError('Die Änderungen konnten nicht gespeichert werden.');
    }
  };
  const title = name => {
    const count = Object.keys(fieldErrors).filter(field => cardFor(field) === name).length;
    return count ? `${name} · ${count} Fehler` : name;
  };
  return (
    <Columns className="kid-edit-page min-w-0">
      <form aria-label="Kind bearbeiten" noValidate onSubmit={submit}>
        {Object.keys(fieldErrors).length ? (
          <div className="mb-4 rounded-lg border border-destructive bg-popover p-3" role="alert">
            <strong>Nichts gespeichert</strong> · {Object.keys(fieldErrors).length} Fehler
            <Button className="ml-2" size="sm" type="button" variant="outline" onClick={() => controls.current[firstInvalid]?.focus()}>Zum ersten Fehler</Button>
          </div>
        ) : null}
        <p className="mb-3 text-sm text-muted-foreground">* kennzeichnet Pflichtfelder</p>
        <div className="grid min-w-0 grid-cols-1 items-start gap-4 min-[901px]:grid-cols-2">
          {SECTIONS.map(([section, fields]) => (
            <Card className="min-w-0" expanded={expanded[section]} key={section} onExpandedChange={open => setExpanded(current => ({ ...current, [section]: open }))} title={title(section)}>
              <div className="grid min-w-0 gap-3">
                {fields.map(([name, label, kind]) => (
                  <EditField errors={fieldErrors[name]} inputRef={element => { controls.current[name] = element; }} key={name} kind={kind} label={label} name={name} onChange={update} options={kid.field_options[name]} value={kind === 'select' ? encoded(values[name]) : values[name]} />
                ))}
                {section === 'BuDo' ? (
                  <>
                    <h3 className="mt-2 text-lg font-semibold">Schwerpunkte</h3>
                    {kid.swp_periods.map(period => <EditField errors={fieldErrors[`swp.${period.id}`]} inputRef={element => { controls.current[`swp.${period.id}`] = element; }} key={period.id} kind="select" label={period.label} name={`swp.${period.id}`} onChange={update} options={period.options} value={values[`swp.${period.id}`]} />)}
                    <h3 className="mt-2 text-lg font-semibold">Happy Cleaning</h3>
                    <EditField errors={fieldErrors.happy_cleaning_number} inputRef={element => { controls.current.happy_cleaning_number = element; }} kind="number" label="Happy Cleaning Nummer" name="happy_cleaning_number" onChange={update} value={values.happy_cleaning_number} />
                    {kid.happy_cleaning_events.map(eventItem => <EditField errors={fieldErrors[`happy_cleaning.${eventItem.id}`]} inputRef={element => { controls.current[`happy_cleaning.${eventItem.id}`] = element; }} key={eventItem.id} kind="select" label={eventItem.label} name={`happy_cleaning.${eventItem.id}`} onChange={update} options={eventItem.options} value={values[`happy_cleaning.${eventItem.id}`]} />)}
                  </>
                ) : null}
              </div>
            </Card>
          ))}
        </div>
        <div aria-label="Bearbeitungsaktionen" className="sticky bottom-0 z-10 mt-4 flex flex-wrap justify-end gap-2 border-t border-border bg-background/95 py-3" role="region">
          <Button type="button" variant="secondary" onClick={() => dirty ? setDiscarding(true) : navigate(`/kid_details/${kid.id}`)}>Abbrechen</Button>
          <Button type="submit">Alle Änderungen speichern</Button>
        </div>
      </form>
      {discarding ? <DiscardDialog cancel={() => setDiscarding(false)} discard={() => navigate(`/kid_details/${kid.id}`)} /> : null}
    </Columns>
  );
}

export const kidEditRoutes = [{
  pattern: /^\/kid_details\/(\d+)\/edit$/,
  page: 'kid-edit', title: 'Kind bearbeiten', domain: 'kids', readContractKey: 'kid-edit',
  params: match => ({ id: match[1] }),
  resolveTitle: (_route, data) => `${data.kid.full_name} bearbeiten`,
  render: ({ data, mutate, navigate }) => <KidEditPage data={data} mutate={mutate} navigate={navigate || (path => window.location.assign(path))} />,
}];
