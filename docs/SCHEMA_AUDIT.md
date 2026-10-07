# Schema review — 2026-10-07

Reviewed ORM columns against frontend forms/details, backend services/search/import/
export, migration paths and integration tests. Hidden UI alone does not establish
that a database field or table is unused.

| Decision | Data | Evidence / purpose |
| --- | --- | --- |
| Removed | assets.purchase_date, warranty_expiry | No active form, detail, validation or service consumer |
| Removed | assets.vendor, cost | No asset consumer; receipt source is inventory_transactions.source_vendor, repair vendor/cost are maintenance fields |
| Removed | assets.notes | Legacy generic API accepted it; active asset UI and business history use description instead; removed DTO field rejects old payload |
| Removed | asset_types.track_serial | No feature checks; asset model and S/N are always required by current API |
| Retained | users, master_data, asset_types, locations, warehouses | Configuration, role control and valid receipt prerequisites |
| Retained | assignments, location_history, asset_operations, inventory_transactions, audit_logs | Business state and immutable historical evidence; structures needed for future records |
| Retained | maintenance and repair fields | Current workflows, components, outcomes, reporting and history popups |
| Retained | articles.problem/symptoms/cause/commands/notes | Current knowledge editor and detail consume them |
| Retained | interfaces, ip_addresses.interface_id/status_id | Legacy asset network lookup, station network, search and import/export still reference these; direct IP assignment is the primary UI |
| Retained | switch port mode/status/VLAN fields | Backend validation, default master values, snapshot/export compatibility still reference them |
| Retained | tickets, ticket_activities, ticket_articles, attachments, asset_types.allow_ticket | Existing endpoints, file handling, permissions and tests still depend on them, although navigation is hidden |
| Retained | asset_types.allow_station | Warehouse recipient validation uses it |
| Retained | other configured asset type flags/prefix | Still exposed in configuration/detail or used by capability checks; no unproven deletion |

All business rows, including legacy ticket/interface/port rows, were deleted under
user authorization. The retained schemas let new business operations and migration
compatibility work. Removing entire legacy API contracts is a separate coordinated
change; it cannot safely be done by dropping their tables alone.

Revision 0017 drops confirmed obsolete fields. Revision 0018 corrects PostgreSQL
storage nullability for legacy identities to match SQLite and ORM; new API input
remains non-null and required. Unique event/document indexes now use the same named
index declarations in ORM and migrations. SQLite's historical VARCHAR(150) asset
name is intentionally accepted by schema comparison because SQLite never enforces
that length; PostgreSQL was migrated to VARCHAR(400) in revision 0012.

Backups preserve deleted values. Downgrading 0017 restores definitions only and
cannot recover old values. Use the full pre-cleanup backup and matching code to recover.
