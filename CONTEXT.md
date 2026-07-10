# BuDoBase Context

## Glossary

### Behavioral parity

The rewritten BuDoBase must preserve what the current working application does from a user's point of view. Existing workflows, data meanings, permissions, side effects, imports/exports, and operational outcomes are treated as the reference unless an explicit exception is documented.

### UI functional parity

The rewritten interface must preserve the current application's workflows, information, labels where they carry domain meaning, and operational affordances, but it does not need to copy the old templates pixel-for-pixel. Visual implementation may use new components as long as the resulting experience remains recognisably BuDoBase and supports the same user tasks.

### Layout/visual parity

A stricter UI parity rule for frontend porting: React screens should match the Django screen structure, information hierarchy, labels, colors, spacing rhythm, and overall look closely enough that users perceive the interface as the same BuDoBase workflow. Layout/visual parity is not pixel-perfect matching; small differences from rendering engines or component internals are acceptable when they do not change the perceived interface or task flow.

### Porting slice

A bounded piece of the rewrite that transfers one user-visible workflow or closely related set of screens from the current application into the new application, including the domain behavior needed for that workflow.

### Greenfield data start

The rewritten BuDoBase starts with new accounts, new teams, and new operational data. Legacy production records from previous Turnusse do not need to be migrated into the new system, although the old application remains the reference for behavior and workflows.

### Excel intake

The primary way a team receives children data for a new Turnus. The rewrite must preserve the ability to import the camp Excel data for each new Turnus and export/update Excel-compatible outputs used by the team.

### Observable parity

A compatibility rule for the rewrite: what users can see, do, import, export, and rely on must remain equivalent to the current application, while the internal implementation may use a different model when that model preserves the same observable outcomes. Observable parity applies to product behavior, not to migration of old production data.

### Account management

The part of BuDoBase where authorised people manage users, team membership, roles, invitations, and access to camp data. Account management is part of the product surface and must exist in the rewritten application rather than being handled only through developer or database administration.

### Invitation

A time-limited email-based way for a person to join BuDoBase. An invitation is sent to an email address, can be accepted by the recipient, and expires after seven days if not accepted. After expiry, an authorised person must send a new invitation.

### Admin

A person with unrestricted BuDoBase management capability across all Turnusse. Admins can manage accounts, assign roles, and grant leadership/access across Turnusse.

### Leitung

A person responsible for one or more specific Turnusse. A Leitung can invite and manage people only within the Turnusse where they have been assigned leadership by an Admin.

### Teamer

A person who belongs to a Turnus team without Admin or Leitung management authority. Teamers can view their assigned Turnus data and perform day-to-day operational child workflows, but they cannot manage accounts, import Excel, configure Turnusse, or perform admin planning/setup by default.

### Team label

An informational label on a person's Turnus profile, such as Betreuer:in, Küche, Organisator, or Freiwillige:r. Team labels describe responsibilities or context but do not grant permissions by themselves.

### Turnus

A camp session/period that scopes children, team membership, planning, operational records, and most camp-specific access. A person may have access to multiple Turnusse. BuDoBase access is modeled around users and Turnusse, not around multiple customer organisations.
