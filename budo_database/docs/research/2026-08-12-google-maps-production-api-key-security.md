# Google Maps production API capabilities and API-key security

_Date checked: 2026-08-12_

## Repository usage

BuDoBase has two distinct Google Maps clients and should use two distinct keys:

1. **Browser key** (`GOOGLE_MAPS_BROWSER_API_KEY`)
   - Exposed to the authenticated React client by `budo_app/read_contracts/bootstrap.py`.
   - `frontend/src/components/google-map.jsx` loads the `maps`, `marker`, and `core` libraries through Maps JavaScript API.
   - Required enabled API/API restriction: **Maps JavaScript API only**.
   - The marker/core libraries and the configured map ID do not imply Places, Geocoding, Routes, Directions, or Distance Matrix access.

2. **Server key** (`GOOGLE_MAPS_API_KEY`)
   - Kept server-side and used by `budo_app/google_maps_gateway.py`.
   - Calls `maps.googleapis.com/maps/api/geocode/json` for reverse geocoding.
   - Calls `routes.googleapis.com/directions/v2:computeRoutes` for driving/walking duration.
   - Required enabled APIs/API restrictions: **Geocoding API** and **Routes API** only.

Google Maps directions URLs generated in `frontend/src/domains/places.jsx` are ordinary Maps URLs and do not use an API key. Expanding an allowlisted Google short URL is also an ordinary HTTP redirect request and needs no Google Cloud API.

## Recommended production configuration

### Browser key

Create a dedicated key such as `budo-prod-browser-maps`:

- **Application restriction:** Websites (HTTP referrers).
- Allow only the exact production origin/host represented by `APP_URL`, normally both the host and all paths (for example `https://maps.example.org` and `https://maps.example.org/*`). Add a separate exact hostname only if production is genuinely served there; do not allow broad domains such as `*.railway.app/*` unless unavoidable.
- **API restriction:** Maps JavaScript API only.
- Do not add Generative Language API / Gemini API, Places API, Geocoding API, Routes API, Directions API, or Distance Matrix API.

The browser key is intentionally observable in browser traffic. Authentication around the app does not make this key secret. Its security boundary is the combination of website restriction and, critically, the Maps-JavaScript-only API restriction.

### Server key

Create a different key such as `budo-prod-server-maps`:

- **Application restriction:** IP addresses, restricted to the production service's fixed outbound public IP/CIDR.
- **API restrictions:** Geocoding API and Routes API only.
- Store only in the production secret/environment configuration as `GOOGLE_MAPS_API_KEY`; never send it to the browser or commit it.

If the hosting service has dynamic outbound IPs, Google notes that IP restrictions can be impractical. The safe options are to provision a static egress IP/proxy, or—if that is not currently possible—retain the strict two-API restriction, keep the key secret, use conservative quotas, and alert on usage/cost. Do not put website restrictions on this server key: Google permits only one application-restriction type per key, and server calls do not carry a trustworthy browser referrer.

Using one server key for Geocoding and Routes is reasonable because both calls originate from the same server application and can share the same IP restriction. Splitting those into two keys gives finer quotas/rotation but is not necessary for the current application.

### Project/API hygiene

- Disable APIs the project does not use, especially **Generative Language API**, unless there is a separate intentional Gemini workload.
- Prefer a dedicated Maps project, or at minimum never place Gemini workloads and public browser Maps keys in the same project. Google's May 2026 guidance recommends standalone projects and least-privilege API/application restrictions.
- Apply quotas to Maps JavaScript API, Geocoding API, and Routes API based on expected production traffic. Configure Cloud Billing budgets/alerts and API-usage alerts. A budget alert notifies; it is not a hard spending cap.
- Review per-key usage in Metrics Explorer, rotate suspicious keys, and delete unused keys.
- Roll restrictions out while checking Maps JavaScript browser-console/API errors. Google warns that restriction changes can take time to propagate.

Google's general guidance explicitly recommends both an application restriction and API restrictions, separate keys per app/client type, Websites restrictions for Maps JavaScript API, and IP-address restrictions for server-side Geocoding/Routes web-service calls.[1][2]

## Gemini incident: current status

### What happened

Truffle Security reported on 2025-11-21 and disclosed publicly on 2026-02-25 that standard `AIza...` Google API keys used as public identifiers for products such as Maps could also authenticate to Gemini when the Generative Language API was enabled in the same project. Existing unrestricted keys could thereby gain access without an explicit key-level permission change. Researchers reported 2,863 live exposed keys and demonstrated access to Gemini file/cache-related resources and billable model usage.[3]

This was particularly dangerous because a Maps browser key must be visible client-side. The fundamental mitigation was always a key-level **API restriction** allowing only the intended Maps API(s); a referrer restriction alone is not an adequate substitute for service scoping.

### Is it fixed now (2026-08-12)?

**Mostly, with a final transition still pending:**

- Google's current Gemini documentation says Gemini now rejects **unrestricted standard API keys**. Standard keys with explicit restrictions can still work until September 2026.[4]
- New keys created in Google AI Studio are authorization keys bound to a service account and restricted to Generative Language API by default, with leaked-key enforcement.[4]
- Google states that in **September 2026** Gemini will reject all standard API keys; Gemini users must migrate to authorization keys.[4]
- Truffle Security describes the June 2026 change as fixing the reported cross-service privilege-escalation root cause, while noting the full standard-key shutdown is scheduled for September.[5]

Therefore, an unrestricted legacy key should be audited immediately rather than relying only on Google's transition. For BuDoBase, a browser key whose API restriction is **Maps JavaScript API only** cannot call Gemini, regardless of whether Generative Language API is enabled in the project. The server key should likewise list only Geocoding API and Routes API. This least-privilege setup protects the application independently of Gemini's rollout state.

## Production checklist

- [ ] Enable Maps JavaScript API, Geocoding API, and Routes API.
- [ ] Confirm no other Google API is needed by this codebase.
- [ ] Browser key: exact production website referrer(s) + Maps JavaScript API only.
- [ ] Server key: fixed outbound production IP(s) + Geocoding API and Routes API only.
- [ ] Ensure the two environment variables contain different keys.
- [ ] Confirm Generative Language API is disabled in this Maps project, unless intentionally needed elsewhere.
- [ ] Verify there are no unrestricted legacy keys in Credentials.
- [ ] Configure per-API quotas, billing budget alerts, and usage monitoring.
- [ ] Test map rendering, reverse geocoding, and drive/walk duration after restrictions propagate.

## Sources

1. [Google Maps Platform security guidance](https://developers.google.com/maps/api-security-best-practices?hl=en)
2. [Google Cloud: Adding restrictions to API keys](https://docs.cloud.google.com/api-keys/docs/add-restrictions-api-keys)
3. [Truffle Security: Google API Keys Weren't Secrets. But then Gemini Changed the Rules](https://trufflesecurity.com/blog/google-api-keys-werent-secrets-but-then-gemini-changed-the-rules)
4. [Google AI for Developers: Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key)
5. [Truffle Security: Google Fixes the Gemini API Key Privilege Escalation Issue](https://trufflesecurity.com/blog/google-fixes-the-gemini-api-key-privilege-escalation-issue)
6. [Google Cloud Blog: Securing Your Gemini and Google API Keys](https://cloud.google.com/blog/topics/developers-practitioners/api-keys-are-open-secrets)
