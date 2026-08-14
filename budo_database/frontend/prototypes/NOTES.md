# Turnus team-management prototype verdict

Variant C (master–detail) was selected for the production direction.

- Desktop: Turnusse are grouped by year in a left rail; the selected team's requests and members occupy the detail pane.
- Mobile: The rail becomes a horizontally scrollable, year-grouped Turnus selector above a single-column detail view.
- Per-member editing uses the existing accessible `PencilIcon` button pattern instead of written “Bearbeiten” links.
- Approval requests keep the out-of-band identity-verification warning prominent on both desktop and mobile.

The prototype remains throwaway code. Reimplement the selected behavior through the production route, read contract, shared components, and tests, then delete these prototype files.
