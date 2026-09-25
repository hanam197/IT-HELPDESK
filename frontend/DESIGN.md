# Workspace UI

The Station interface is the visual reference for the whole application.
Shared styling lives in `src/theme.css`, loaded after the layout rules in
`src/styles.css`. Theme rules also cover dialogs rendered through portals.

## Tokens

- Primary action, selected tab and active navigation: `--color-primary`.
- Main text: `--color-text`; labels and supporting text: `--color-text-secondary`.
- Canvas, cards and table headers: `--color-canvas`, `--color-surface`,
  `--color-surface-muted`.
- Borders: `--color-border` and `--color-border-soft`.
- Spacing: 4, 8, 12, 16, 20 and 24 px through `--space-*`.
- Type: 28 px page title, 15 px section title, 13 px body, 12 px labels,
  11 px captions. Mobile page titles use 25 px.
- Standard controls: 40 px minimum height; cards: 10 px corner radius.

Green, amber and red indicate status or feedback, not primary navigation.
Keep the text label with each status; do not communicate status through color alone.

## Page structure

Use the shared breadcrumb from `App`, a page heading, then the page's content.
Place the main action alongside the heading on desktop and below it on mobile.
Use `Button`, `DataTable` and `Editor` for shared controls and forms.
Tables scroll inside their card on narrow screens; the page itself should not
scroll horizontally. Related detail fields belong in titled cards.

Use visible keyboard focus, accessible names on icon buttons, clear required
field markers and disabled states. Respect reduced-motion preferences.
