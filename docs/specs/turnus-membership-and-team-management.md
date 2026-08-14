# Turnus membership and team management

## Problem Statement

BuDoBase currently stores one Turnus and one descriptive role directly on a person's profile. This prevents people from belonging to several Turnusse, conflates the Turnus being viewed with permission to view it, and cannot express Leitung authority per Turnus. Public registration is also protected by a shared passphrase, and there is no product interface for requesting, approving, switching, or managing Turnus membership.

This creates a serious privacy risk because Turnus data contains sensitive information about children. Merely creating an account, knowing a team's name, or submitting a plausible email address must never reveal Turnus data. A Leitung must explicitly approve membership after verifying the requester through a trusted, out-of-band contact path.

## Solution

Introduce approval-gated Turnus membership. Anyone may create an account without the shared registration passphrase, but a new account starts without Turnus access and sees an awaiting-membership dashboard. A person can request membership in a Turnus. Every Leitung of that Turnus receives an email, and the approval interface and email both instruct the Leitung to verify independently that the email address belongs to the named person and that the person actually made the request.

An approved membership connects one account to one Turnus and carries the functional role `Leitung` or `Teamer` plus a descriptive team label that may differ between Turnusse. Admin is global and maps to Django superuser status. A Leitung can browse registered users and add or remove Teamers only in Turnusse they lead. Only Admins assign Leitung authority. Admins can browse all Turnusse grouped by year and inspect who belongs to each team.

Users with multiple approved memberships can select the Turnus they are currently working with. Selection changes context but never grants access. All existing Turnus-scoped reads, writes, searches, media, real-time channels, exports, and audit behavior must resolve through an approved membership.

The selected master-detail prototype becomes the production direction: year-grouped Turnus navigation, selected-team requests and membership management, accessible pencil-icon member actions, and a responsive single-column mobile layout. A new reusable translucent-card component will reproduce the prototype's opacity treatment without changing the existing Card component, allowing other screens to migrate explicitly later.

## User Stories

1. As a visitor, I want to register without a shared secret, so that I can create my own BuDoBase account.
2. As a newly registered user, I want to land on an awaiting-membership dashboard, so that I understand why no Turnus data is visible yet.
3. As a user without membership, I want to see available Turnusse without seeing their children or operational data, so that I can request the correct team safely.
4. As a user, I want to request membership in a Turnus, so that its Leitung can verify and admit me.
5. As a requester, I want a clear pending state, so that I know my request has not yet granted access.
6. As a requester, I want duplicate pending requests prevented, so that Leitungen do not receive repeated notifications.
7. As a requester, I want to request another Turnus independently, so that I can belong to several teams.
8. As a requester, I want a rejection to remain distinct from a pending request, so that the outcome is understandable without granting access.
9. As a Leitung, I want an email for every new request in my Turnus, so that I can respond promptly.
10. As one of several Leitungen, I want every Leitung of the Turnus notified, so that approval does not depend on one person being available.
11. As a Leitung, I want the email to identify the requester and requested Turnus, so that I know what needs verification.
12. As a Leitung, I want the email to tell me to contact the person through a known independent channel, so that a plausible name or similar email address is not accepted blindly.
13. As a Leitung, I want the approval interface to repeat the verification warning, so that the security check is visible at the moment of approval.
14. As a Leitung, I want approval to require an explicit action, so that opening a request cannot admit someone accidentally.
15. As a Leitung, I want to approve a verified requester as a Teamer, so that they gain access to exactly my Turnus.
16. As a Leitung, I want to reject an unverified or inappropriate request, so that it grants no access.
17. As a Leitung, I want to browse all registered users, so that I can add a known person without waiting for a join request.
18. As a Leitung, I want to add an available user as a Teamer in a Turnus I lead, so that planned team members can be admitted directly.
19. As a Leitung, I want to remove a Teamer from a Turnus I lead, so that former members immediately lose that Turnus access.
20. As a Leitung, I want management controls limited to Turnusse I lead, so that I cannot manage another Leitung's team.
21. As a Leitung, I want to see pending requests and current members together for a selected Turnus, so that team management has one clear workspace.
22. As a Leitung, I want to see each member's descriptive team label, so that responsibilities are clear without confusing labels with permissions.
23. As a Leitung, I want to edit a Teamer's descriptive label for my Turnus, so that the label matches their responsibility there.
24. As a keyboard or screen-reader user, I want member edit icons to have person-specific accessible names, so that icon-only actions remain understandable.
25. As an Admin, I want unrestricted access to account and membership management across all Turnusse, so that I can administer the whole application.
26. As an Admin, I want Turnusse grouped by year, so that current and historical teams remain easy to scan.
27. As an Admin, I want translucent year containers with Turnus cards and member summaries, so that the information hierarchy matches the approved design.
28. As an Admin, I want to search Turnusse and people, so that I can quickly find where someone belongs.
29. As an Admin, I want to assign or remove Leitung authority per Turnus, so that leadership remains an explicit global-admin decision.
30. As an Admin, I want to see who is Leitung and who is Teamer in every Turnus, so that authority is auditable at a glance.
31. As a Teamer, I want my descriptive label to differ between Turnusse, so that one team's responsibility does not overwrite another's.
32. As a user with one membership, I want that Turnus selected automatically when appropriate, so that I can begin work without unnecessary navigation.
33. As a user with several memberships, I want a Turnus switcher in the application chrome or dashboard, so that I can change working context quickly.
34. As a user, I want the switcher to list only approved memberships, so that it cannot be used to gain access.
35. As a user, I want my selected Turnus remembered across requests and sign-ins, so that the application stays in the intended context.
36. As a user whose selected membership is removed, I want the application to fall back safely to another approved membership or the awaiting dashboard, so that stale selection never leaks data.
37. As a mobile Leitung, I want year-grouped Turnusse in a horizontally scrollable selector, so that I can switch teams without a desktop sidebar.
38. As a mobile Leitung, I want requests and members stacked in one readable column, so that approval and management work on a phone.
39. As a desktop Admin or Leitung, I want a master-detail layout, so that I can keep team context visible while managing its people.
40. As a user, I want translucent surfaces to preserve readable contrast and visible focus states, so that the approved visual treatment remains accessible.
41. As a developer, I want translucent cards to be a separate shared component, so that existing Card screens remain stable and can migrate intentionally later.
42. As a security-conscious operator, I want every Turnus-scoped endpoint to reject users without approved membership, so that UI hiding is never the access boundary.
43. As a security-conscious operator, I want media, exports, audit records, search results, and real-time subscriptions scoped to approved membership, so that secondary paths cannot leak Turnus data.
44. As an operator, I want membership approvals, rejections, additions, removals, role changes, and Turnus switches audited, so that sensitive access changes can be investigated.
45. As a current user, I want my existing single Turnus assignment converted safely into membership and selection, so that deployment does not unexpectedly remove current access.

## Implementation Decisions

- Keep personal information on the global profile. Replace the profile's use as the source of Turnus authority with a many-to-many relationship represented by explicit Turnus membership records.
- A Turnus membership is unique per account and Turnus. It stores the functional Turnus role (`Leitung` or `Teamer`) and the descriptive team label. The label grants no permission.
- Admin is global and maps to Django `is_superuser`. Django `is_staff` remains Django-administration access and is not the product-level Admin definition.
- Only an approved Turnus membership grants Turnus access. Registration, a join request, visibility in the user directory, or a stored selected Turnus does not grant access.
- A join request has an explicit lifecycle sufficient to distinguish pending, approved, rejected, and cancelled/superseded outcomes. Only one pending request may exist for the same account and Turnus.
- Approving a request and creating membership is one atomic operation. Concurrent approval attempts must not create duplicate membership.
- Every current Leitung of the requested Turnus receives the notification email. Email delivery is triggered only after the request transaction commits.
- The notification and approval UI use explicit identity-verification copy: verify through a known independent channel that the email belongs to the person and that the person made the request.
- A Leitung can list all registered accounts, approve or reject requests, add Teamers, remove Teamers, and edit team labels only for Turnusse they lead.
- A Leitung cannot grant or remove Leitung authority. Admins manage Leitung memberships across all Turnusse.
- The selected Turnus is stored separately from membership and is valid only while a corresponding approved membership exists. Server-side resolution validates membership on every request.
- Existing request helpers, read contracts, commands, media delivery, exports, audit queries, search bootstrap, and real-time authorization migrate from the profile's single Turnus to the validated selected membership.
- The current single-Turnus field remains temporarily during an expand-and-contract migration. Existing assignments create equivalent memberships and initial selection before callers migrate; the obsolete authority path is removed only after all consumers move.
- Public registration removes the shared passphrase field and validation. New accounts still receive their profile but no membership.
- The awaiting-membership dashboard reveals only safe account state, available Turnus identity needed to request access, and the user's request states. It contains no child, team-private, operational, search, media, audit, or export data.
- The management interface follows approved prototype Variant C: desktop master-detail navigation, year grouping, pending requests above membership, person-specific pencil icon actions, and mobile horizontal Turnus selection with a single-column detail view.
- Introduce a new reusable `TranslucentCard`-style component alongside the existing Card. It owns the approved translucent surface, boundary, elevation, contrast, focus, and expansion behavior by composing or sharing the existing Card contract. Existing Card consumers do not change in this feature.
- The approved translucency is an explicit, scoped exception to the current design-system guidance. It must use semantic tokens and meet contrast/focus requirements; the feature does not restyle unrelated screens.
- Team-management mutations use CSRF-protected server endpoints, explicit authorization checks, atomic domain operations, and action-level feedback through the existing application mutation/toast conventions.
- Membership-management and selection changes emit audit events without placing sensitive personal data in generic logs.

## Testing Decisions

- Tests verify public behavior at stable seams rather than model internals, private helpers, class lists, or implementation-specific call sequences.
- The agreed highest seams are registration/navigation responses, route-data and mutation HTTP contracts, notification email output, rendered React behavior, and representative protected Turnus resources.
- Registration coverage proves public signup succeeds without a passphrase and produces the awaiting-membership experience.
- Access-control coverage proves an authenticated account without approved membership cannot read or mutate Turnus data through representative read, command, media, export, audit, search, and real-time boundaries.
- Join-request coverage proves submission, duplicate-pending prevention, safe request-state visibility, and absence of access before approval.
- Notification coverage proves every Leitung receives one message containing the requester, Turnus, and independent identity-verification warning.
- Approval coverage proves only the relevant Leitung or an Admin can approve/reject, that approval atomically grants one membership, and that cross-Turnus management is denied.
- Membership-management coverage proves Leitungen can browse accounts and manage Teamers only in their own Turnusse, while only Admins can manage Leitung authority.
- Selection coverage proves only approved memberships are selectable, data changes scope after switching, and removal of the selected membership fails closed.
- Label coverage proves labels vary by membership and never affect authorization.
- Rendered-DOM coverage proves the master-detail and mobile workflows, year grouping, request warning, accessible person-specific pencil actions, and switcher behavior.
- Shared-component coverage proves the new translucent card preserves Card interaction, keyboard behavior, responsive expansion, focus visibility, and readable semantic surfaces without changing existing Card output.
- Existing examples include authentication tests, profile/team route-data contract tests, active-Turnus isolation tests, sensitive child-edit authorization tests, audit-policy tests, media authorization tests, real-time authorization tests, and shared rendered-DOM component tests.
- Each implementation ticket follows red-green-review-fix: a test-writing agent adds one failing externally observable test slice, a separate implementation agent makes it pass, a third agent reviews standards and spec compliance, and a fix agent addresses valid findings.

## Out of Scope

- Replacing Django's built-in account model or introducing a separate customer/organisation tenancy model.
- Automatic admission based on email domain, name similarity, invitation knowledge, or possession of a join-request link.
- Automated identity verification. The product reminds Leitungen to verify out of band but does not claim to perform that verification.
- Allowing Leitungen to promote or demote other Leitungen.
- Password reset, email verification, multi-factor authentication, social login, and broader account-security redesign.
- Changing the permissions of ordinary Teamer operational workflows beyond replacing the Turnus access source.
- Redesigning unrelated BuDoBase pages with translucent cards. The new component enables later migration, but those migrations require separate work.
- Migrating historical production records beyond the explicit compatibility migration needed for current database assignments.
- Building or changing the seven-day email invitation workflow described elsewhere in the account-management domain.

## Further Notes

- The selected prototype and screenshots live under the frontend prototype area and are design evidence, not production code. Production implementation must be rewritten through shared components, contracts, authorization, and tests; delete the throwaway prototype after the accepted design is absorbed.
- The identity warning is a deliberate defense against social impersonation, not a guarantee. Approval remains a trusted human decision by Leitung or Admin.
- The translucent card is intentionally isolated from the existing Card API so teams can compare and migrate other surfaces later without a broad visual regression.
- The implementation should be organized into small vertical tickets with explicit blockers so independent frontier tickets can run concurrently.
