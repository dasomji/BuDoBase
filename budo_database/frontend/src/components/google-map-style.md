# Google Maps cloud style

[`google-map-style.json`](./google-map-style.json) is the source-controlled
basemap style used by the [`GoogleMap`](./google-map.jsx) component. The JSON is
not loaded by the frontend bundle. It must be imported into Google Cloud and
associated with the map ID supplied to the component as `mapId`.

## What the style does

The map is intended for a children's summer camp, so it favors camp-useful
places over local-business and road-label clutter.

- Hides all Google point-of-interest labels by default.
- Restores labels for:
  - emergency services;
  - food and drink, including restaurants and cafés;
  - recreation, including parks and trailheads;
  - restrooms; and
  - transit.
- Hides highway names, route shields, and road signs.
- Keeps the road geometry visible.
- Does not affect BuDoBase's own place markers.

The parent `pointOfInterest` rule hides POI labels. The more specific child
rules override that inherited visibility for the categories that should remain.
Google does not provide dedicated JSON feature IDs for every kind of business,
such as barbers or ice-cream shops. Ice-cream venues should normally be covered
by the restored `pointOfInterest.foodAndDrink` category.

## Import into Google Cloud Console

Use the Google Cloud project that owns the map ID configured as
`GOOGLE_MAPS_MAP_ID` in BuDoBase.

### Create a style from this JSON

1. Open [Google Maps Platform → Map Styles][cloud-map-styles].
2. Select the correct Google Cloud project.
3. Click **Create style**.
4. Select the **JSON** tab.
5. Either paste the contents of `google-map-style.json` or choose
   **Upload JSON File** and upload it.
6. Resolve any validation errors shown by Google. When the preview is valid,
   click **Customize**.
7. Review the preview at the zoom levels and locations used by the camp.
8. Click **Save**, provide a style name such as `BuDoBase camp map`, and save
   the style. Google automatically publishes a newly created style.

### Associate the style with BuDoBase's map ID

1. Open [Google Maps Platform → Map Management][cloud-map-management].
2. Select the map ID whose value is configured as `GOOGLE_MAPS_MAP_ID`.
3. Edit the map ID and select the newly created map style.
4. Save the association.

No frontend deployment is needed when the existing map ID remains unchanged.
Google notes that published style changes can take a few hours to propagate.

## Update the style later

Treat `google-map-style.json` as the source of truth:

1. Change and validate the JSON in this directory.
2. In Google Cloud Console, open the associated style and click **Customize**.
3. Open the **JSON** tab, paste or upload the updated file, and click **Apply**.
4. Check the preview, then click **Save**.
5. Existing styles save changes as a draft. Click **Publish** to make the draft
   live for associated map IDs.

For a production change, Google recommends duplicating the style, publishing
and testing the copy with a staging map ID, and only then applying the approved
style to the production map ID.

## JSON structure and maintenance notes

Google's current cloud-style schema uses:

- a top-level `variant` (`light` or `dark`);
- a `styles` array;
- an `id` on each rule selecting a feature from Google's taxonomy;
- `geometry` for polygons and lines; and
- `label` for text, icons, and pins.

Setting `label.visible` to `false` hides only a feature's label. It does not hide
its geometry. This distinction is why the highway rule removes highway names
without removing the roads themselves.

Feature IDs are hierarchical. A rule on a parent applies to its children unless
a child rule overrides that property. Keep the broad POI rule before the
explicitly restored child categories so the intent remains easy to read.

Google's **POI density** control cannot be represented in exported/imported
JSON. If further decluttering is needed, set it separately using the gear icon
beside **Map features** in the visual style editor. That console-only value must
be reselected when importing a style.

## Sources

- [Use JSON with cloud-based maps styling][json-guide] — importing, editing,
  applying, exporting, saving, and publishing JSON styles.
- [JSON reference for cloud-based maps styling][json-reference] — top-level
  properties, rule schema, feature IDs, `geometry` and `label` elements,
  stylers, inheritance, and JSON limitations.
- [What you can style on the map][taxonomy] — map-feature taxonomy and the
  available styling controls for polygons, lines, icons, text labels, and pins.
- [Understand map style inheritance and hierarchy][inheritance] — parent/child
  inheritance and child overrides.
- [Create and use map styles][map-styles] — style lifecycle and map-ID
  association.
- [Test style updates][test-style-updates] — Google's recommended staging flow
  for production style changes.

[cloud-map-styles]: https://console.cloud.google.com/google/maps-apis/studio/styles
[cloud-map-management]: https://console.cloud.google.com/google/maps-apis/studio/maps
[json-guide]: https://developers.google.com/maps/documentation/maps-static/cloud-customization/json
[json-reference]: https://developers.google.com/maps/documentation/maps-static/cloud-customization/json-reference
[taxonomy]: https://developers.google.com/maps/documentation/maps-static/cloud-customization/taxonomy
[inheritance]: https://developers.google.com/maps/documentation/maps-static/cloud-customization/map-hier
[map-styles]: https://developers.google.com/maps/documentation/maps-static/cloud-customization/map-styles
[test-style-updates]: https://developers.google.com/maps/documentation/maps-static/cloud-customization/test-style-updates
