# Read-contract test ownership

Each route-data migration ticket owns one package below and should add its
authenticated Django HTTP tests there. Domain tickets should not add their
contract tests to a shared module or change central dispatch tests.

| Package | Contract keys |
| --- | --- |
| `allocation` | `allocation` |
| `attendance` | `check-in`, `check-out`, `train-arrival`, `train-departure` |
| `dashboard` | `dashboard` |
| `focuses` | `focus-create`, `focus-dashboard`, `focus-detail`, `focus-meals`, `focus-update` |
| `kids` | `kid-detail`, `kids-directory` |
| `kitchen` | `kitchen` |
| `maintenance` | `special-upload`, `turnus-list`, `turnus-upload` |
| `profiles` | `profile`, `teamer` |
| `places` | `place-create`, `place-detail`, `place-images`, `place-update`, `places-list` |
| `reports` | `birthdays`, `families`, `kid-count`, `murder-game`, `serial-letter`, `special-families` |
