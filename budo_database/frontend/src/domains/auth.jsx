import { Card, Column, Columns, NativeForm } from '../components';

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

export const authRoutes = [
  {
    pattern: /^\/login$/,
    page: 'login',
    title: 'Login',
    domain: 'auth',
    readContractKey: null,
    render: ({ data }) => <AuthPage kind="login" data={data} />,
  },
  {
    pattern: /^\/register$/,
    page: 'register',
    title: 'Registrieren',
    domain: 'auth',
    readContractKey: null,
    render: ({ data }) => <AuthPage kind={data.authenticated ? 'registered' : 'register'} data={data} />,
  },
];
