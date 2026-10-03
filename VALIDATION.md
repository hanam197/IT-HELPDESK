# Validation record

Kiểm chứng ngày 2026-09-20 trong workspace hiện tại.

| Hạng mục | Kết quả |
|---|---|
| TypeScript + Vite production build | PASS |
| PostgreSQL 16 migration `upgrade head` | PASS |
| PostgreSQL migration `downgrade base` → `upgrade head` trên DB test riêng | PASS |
| Demo seed trên PostgreSQL 16 | PASS |
| Backend integration suite | 10/10 PASS |
| Chromium end-to-end suite với Vite → FastAPI → PostgreSQL | 4/4 PASS |
| Desktop 1440 px / mobile 390 px | Đã xem screenshot; bảng cuộn ngang, sidebar mobile đóng/mở |
| Chromium end-to-end suite trên bản production build | 4/4 PASS |
| Compose YAML parsing | PASS |
| Docker image build / Docker Compose startup | Chưa chạy: môi trường không có Docker |
| Load test / production deployment | Chưa thực hiện |

## Backend scenarios

1. Authentication, backend RBAC, cookie session, CSRF header, bảo vệ users và password hash.
2. Hai lần move, current-location uniqueness, assign/transfer/return, giữ history và audit.
3. Asset capability, retired asset, duplicate code/serial/IP, invalid MAC/IP/subnet, location cycle, immutable audit/history.
4. Ticket → internal/public comment → file upload/download → maintenance → asset restoration → resolution → linked KB.
5. Search asset/IP/MAC, trace VLAN/location/switch port, QR PNG, CSV/XLSX, dashboard, pagination, invalid filter.
6. Sáu ticket tạo đồng thời, không trùng số tự động.
7. Tìm IPAM theo MAC/asset/switch/port; overdue KPI khớp drill-down; lọc location; report cost và average resolution.
8. Return asset trong lúc sửa chữa, hoàn tất bảo trì, cấp lại, sửa ghi chú bảo trì cũ không làm sai trạng thái asset.

9. Tạo article từ ticket: failure không tạo bài mồ côi, success liên kết bài và ghi timeline trong cùng transaction.
10. Asset registration bắt buộc location, upload/đọc ảnh thật, từ chối file giả, tải template và import XLSX tạo location history.

## Browser scenarios

1. Đăng nhập, tìm `192.168.20.80`, mở PRN-012, xem Network/Location/Tickets/History.
2. Quick Create ticket, tìm ticket vừa tạo, mở detail và ghi timeline.
3. Tải toàn bộ module chính, không có JavaScript error; điều hướng mobile.
4. Kiểm tra Asset chỉ giữ XLSX, mở import, tạo Asset với location bắt buộc, Record Overview mới, move, assign, return và tạo maintenance; xác nhận status Repair và assignment history.

Hai cảnh báo deprecation từ Starlette TestClient/httpx/anyio không làm fail test. Frontend production output đã tách vendor chunks; build không còn cảnh báo chunk lớn hơn 500 kB.

Các test chưa thay thế UAT với dữ liệu và quy trình thật. README nêu các giới hạn V1: metadata lookup chưa phân trang, login limiter trong một process, notification chưa push/email và chưa benchmark tải lớn.

## Warehouse / Station — 2026-09-22

- Backend: 15 tests passed, including mandatory warehouse receipts, asset issue to user/station, returns, immutable stock quantity, insufficient-stock rejection, recipients, issue dates, role restrictions, station fields and photo upload.
- Frontend: TypeScript + Vite production build passed.
- Chromium: warehouse consumable receipt/issue and Station desktop/mobile workflow passed; serialized asset receipt → station issue → move → assignment → return → maintenance workflow passed. Browser tests used an isolated SQLite database on ports 8001/5174.
- Migration 0004: upgrade → downgrade to 0003 → upgrade on a copy of the existing SQLite database passed; all 8 existing assets retained and foreign-key check empty. Applied upgrade to the local development database after backup.
- Existing browser tests involving Tickets are not currently green: the pre-existing frontend configuration lacks `tickets` and `ticket-articles` entries. This change does not restore that module.
- PostgreSQL concurrency and migration were not re-run for this change.

## Shared Station UI theme — 2026-09-22

- All available module pages now use the shared dark sidebar, blue primary actions, typography, spacing, cards, tables, forms and breadcrumb.
- Chromium smoke review covered 23 desktop routes, including Dashboard, Assets/detail, Warehouse, Stations, Network/IPAM, Maintenance, Knowledge Base, Reports, Settings and administration pages. No JavaScript errors or page error messages were recorded.
- Six mobile pages (390 px) and the mobile navigation were checked; no document-level horizontal overflow. Wide tables and tab bars scroll within their containers.
- Sign-in and the asset receipt drawer were visually reviewed. Review used the isolated database and did not alter live inventory.
- TypeScript and Vite production build passed. Reports now filters unavailable resource configurations instead of crashing on an absent Tickets configuration.

## Inventory and centralized History refactor — 2026-09-22

- Renamed Consumables and parts to Inventory; Assets in warehouse custody, Consumables and warehouse History tabs moved out of Warehouse.
- Asset types now appears under Settings. Removed Ticket UI and standalone Asset operations navigation; historical database records and APIs retained.
- Unified operation, stock movement, location, assignment and audit history with read-only details and legacy route redirects.
- Backend: 16 tests passed, including stock custody filtering and history search by linked asset serial.
- Frontend: TypeScript/Vite build passed; all 5 Playwright workflows passed on isolated test data, including desktop/mobile navigation and real receipt/issue/return flows. Obsolete Ticket UI tests were replaced by Inventory and History routing checks.
- `git diff --check` passed.

## Asset workspace and contextual stock actions — 2026-09-22

- Asset detail redesigned with Overview / Network / History, Model as heading, four overview cards, and Quick actions above the photo/QR sidebar. Asset create/edit forms no longer expose Name, Source, Warranty Expiry or Notes.
- Received by / Handed over by derive from immutable warehouse transaction actors. The recipient remains a separate field; historical missing actors are not invented.
- Per-asset lifecycle combines warehouse receipts/issues, location changes, assignments/returns, maintenance audit transitions, record changes and retirement. Retire records a reason, prevents retiring assigned/in-repair assets, closes the current location and removes warehouse custody.
- Removed standalone History navigation. Stations is a direct sidebar link. Stock history remains under Inventory and audit logs under Settings.
- Assets list/detail and Inventory list/detail open a shared stock dialog locally, with record and warehouse preselected for row actions. Asset detail also supports return-to-warehouse locally.
- Backend: all 18 tests passed, including full lifecycle, actor attribution, retirement restrictions and permissions. Frontend: production build passed; all 6 Playwright workflows passed. Dedicated asset desktop/mobile screenshots reviewed; mobile sidebar transition check and overflow check passed.
- Browser writes used the isolated test database. Existing development data and ticket records preserved; no schema migration required.

## Compact Asset Overview — 2026-09-24

- Removed the Warehouse field from Location & responsibility; Assign now sits beside Assigned To and opens the stock issue dialog for warehouse assets.
- Moved contextual actions into the same command row as Print label / Edit record. Reduced card spacing and photo/QR dimensions; kept responsive wrapping.
- Production build and 5 relevant Playwright workflows passed, including inline Assign, issue/return, maintenance, retirement and mobile layout. Desktop screenshot reviewed; diff whitespace check passed.


## Vòng đời tài sản và Việt hóa — 2026-09-25

- Backend: 23 kiểm thử đạt, bao gồm migration Alembic thực tế từ schema 0004, bảo toàn lịch sử cũ, một sự kiện cho mỗi thao tác, chuyển người phụ trách nguyên tử, khôi phục trạng thái sau bảo trì, chặn thao tác trên tài sản ngừng sử dụng và phân quyền.
- Frontend: TypeScript và Vite production build đạt. Bảy kịch bản Playwright đã đạt trên database SQLite riêng: chi tiết tài sản, nhập/xuất kho, vật tư, trạm, tìm kiếm mạng, điều hướng các module, mobile và popup/lọc lịch sử chuyển người phụ trách. Kiểm tra popup bằng chuột và bàn phím Enter/Escape.
- Giao diện tiếng Việt bao gồm sidebar, tiêu đề, tab, bảng, biểu mẫu, nút, trạng thái/sự kiện, lỗi nghiệp vụ, ngày giờ và tiêu đề tài liệu xuất. Mã kỹ thuật API và nội dung dữ liệu do người dùng nhập được giữ nguyên.
- Migration thử trên bản sao database local bảo toàn số lượng tài sản, cấp phát, lịch sử vị trí, giao dịch kho và audit; kiểm tra khóa ngoại không có lỗi. Migration giữ bản ghi lịch sử gốc và tạo sự kiện chuẩn để hiển thị bảng History.
- Hai cảnh báo deprecation của Starlette/httpx/anyio vẫn còn; không ảnh hưởng kết quả. Chưa kiểm tra lại migration/concurrency trên PostgreSQL trong đợt này.

## Unified asset return — 2026-09-25

- One “Thu hồi” action opens warehouse selection and return condition; confirmation ends assignment and receives the asset into that warehouse atomically.
- The legacy `/api/assets/{id}/return` endpoint now requires `warehouse_id` and uses the stock receipt flow. Active maintenance blocks return.
- Backend: 24 tests passed, including missing/invalid warehouse rollback, alternate warehouse receipt, duplicate return rejection and a single RETURNED event.
- TypeScript + Vite production build passed.
- Chromium: asset detail station issue → return to a different warehouse → retirement, and asset create → move → user assignment → return → maintenance both passed against an isolated SQLite database.

## Required return condition — 2026-09-25

- Returns require an explicit choice with no preselection: AVAILABLE (Sẵn sàng sử dụng) or REPAIR_NEEDED (Cần sửa chữa). Both return the asset to the selected warehouse; repair-needed stock cannot be issued.
- API rejects missing/unsupported return status; return history preserves the selected state. Cancelling repair preserves REPAIR_NEEDED; completing repair restores availability.
- Backend: 25 tests passed, including migration and return/repair lifecycle. TypeScript + Vite build passed. Two Chromium workflows passed against an isolated SQLite database.
- Migration 0006 adds the repair-needed vocabulary for existing databases. Applying migration and restarting the running local backend remain pending: automatic approval review rejected these operational actions without explicit authorization.

## Shared five-state return selector — 2026-09-25

- Return selection now uses the same five canonical asset states via `/meta` (`asset-statuses`), with names read from the asset-status vocabulary. Both return APIs validate against the shared STATUS_CODES rather than a separate two-value list.
- No state is preselected. All five choices close the assignment, receive the asset into the selected warehouse and preserve the chosen state in history, including IN_USE, MAINTENANCE and RETIRED.
- Removed the accidental REPAIR_NEEDED entry from event labels.
- Validation: 26 backend tests passed, TypeScript/Vite build passed, and both asset-detail and asset-create Chromium workflows passed on an isolated database.
- The previous operational approval block remains: migration 0006 and restart of the existing local backend have not been performed.

## Asset Status Flow — 2026-09-26

### Review findings and fixes

- Vocabulary included `REPAIR_NEEDED`, while master-data validation still allowed only four codes; `DISPOSED` was absent. Active metadata, defaults, model validation, filters, labels and dashboard now use exactly AVAILABLE / IN_USE / MAINTENANCE / RETIRED / DISPOSED.
- Creation disabled Status and both API/service layers silently forced AVAILABLE. Status is now required and selectable in the form with AVAILABLE preselected; explicit selections survive registration and Excel import. Missing API/Excel status retains the backward-compatible AVAILABLE default; explicit null/invalid input is rejected.
- Retirement blocked assigned or maintained assets. Retirement now atomically closes the active assignment and maintenance record, preserves repair results, clears active custody and emits the before/after event.
- There was no disposal operation. Added authenticated `/api/assets/{id}/dispose`, available only for RETIRED, with required reason, history and terminal-state guards.
- Return previously accepted IN_USE or any shared status, creating assets marked in use inside warehouse custody. Return now accepts AVAILABLE / MAINTENANCE / RETIRED and prevents skipping retirement to DISPOSED.
- History already stored snapshots but omitted a visible status transition in the list. The list now displays Old Status → New Status and supports the DISPOSED event; actor, timestamp and detailed popup remain.
- Migration 0007 normalizes obsolete repair-status aliases in assets, maintenance previous status and event snapshots. Original audit records, event timestamps, actors and repair descriptions remain. Retired assets are not automatically disposed. Database checks/triggers prevent obsolete current statuses.

### Verification

- 37 distinct backend tests passed: the complete 36-test suite plus the additional migration fixture test. Coverage includes all five creation states, defaults/required validation, invalid legacy codes, status filters, reports, Excel rollback, retirement from IN_USE/MAINTENANCE, disposal authorization, forbidden transitions, immutable terminal states and both legacy migrations.
- All 8 Playwright scenarios passed on a separate seeded SQLite database at ports 8001/5174. Covered creation selection/required default, maintenance completion, warehouse issue/return, movement, reassignment, retirement, disposal, status history/filter, inventory and desktop/mobile navigation. Existing tests expecting a disabled Status or REPAIR_NEEDED were updated.
- TypeScript and Vite production build passed; git diff whitespace check passed.
- Migration tested on a copy of the live SQLite database, then applied to the live database after stopping the backend and taking a fresh backup: `backend/backups/asset-status-0007-20260926-140813.db`. Foreign-key check passed, active metadata has exactly five states, and backend health is OK after restart.
- PostgreSQL-specific migration/concurrency was not exercised in this environment. SQLite upgrade uses triggers to avoid rebuilding the widely referenced assets table; newly created databases use the model CHECK constraint.
- Compatibility decision: retain IN_USE → AVAILABLE for returns and AVAILABLE → MAINTENANCE / RETIRED for existing warehouse workflows. Details are in `asset-lifecycle.md`.

## Maintenance issue workflow — 2026-09-27

- Review and business/API rules: `docs/maintenance-flow.md`.
- Maintenance creation/progress updates no longer stop assets. Explicit `POST /api/maintenance/{id}/stop-asset` keeps station, assignee and custody while switching to MAINTENANCE. Completing an open repair restores operational state according to current custody; cancellation does not imply repair success.
- RETURN → AVAILABLE now completes the active issue in the same transaction; RETURN/RETIRED history includes full repair snapshots. Updates to closed issues cannot resurrect an asset. Critical repair details, technician, dates, cost, parts and notes are recorded in Asset History.
- Reused type_id/master-data for six issue categories. Removed ticket_id and the Ticket activity/detail dependency. Kept existing due_at data without exposing it in the new form/list/detail; added no business table/column.
- 49 distinct backend tests passed (37 existing tests and 12 new tests). New coverage exercises all four requested flows for both station-only and user-assigned assets, unchanged custody, old/new state, actor/time, complete repair snapshots, dates, invalid costs/categories, forbidden Ticket payloads, permissions and terminal-state guards.
- All 12 distinct browser scenarios passed on isolated SQLite data, including four new Maintenance flows, friendly labels, create/edit/list/detail/history, warehouse RETURN, disposal and mobile overflow checks. Browser runs were split/restarted to respect the existing 10-login rate limit; test locators were refined to distinguish Problem/Issue Category and Diagnosis/status option labels.
- TypeScript + Vite build and git diff whitespace check passed.
- Migration 0008 tested from older migrations, on fixtures with an actual Ticket FK, and on a copy of the live database. Legacy categories map to Other with the old name retained in Note; historical Ticket numbers are retained as text before dropping the FK/column. Upgrade does not change asset state or create new events.
- Applied 0008 to the running SQLite database after stopping the backend and creating `backend/backups/maintenance-0008-20260927-103814.db`. Verified exact preservation of assets, assignments, location_history, asset_operations, inventory_transactions, audit_logs and tickets; all maintenance fields except normalized type_id/note and removed ticket_id were unchanged. Foreign-key check passed. Backend/frontend restarted.
- Updated architecture export: 24 model tables, 284 columns, 57 FKs, revision 0008; no missing/extra model columns compared with the live schema. PostgreSQL migration/concurrency was not run in this environment.


## 2026-09-27 — Thu hồi tạo bảo trì và popup

- Thêm nguyên nhân thu hồi vào form; lưu bằng note của giao dịch và description của History, không thêm cột DB.
- Thu hồi kèm tạo phiếu bảo trì là một transaction; kiểm tra rollback khi kỹ thuật viên không hợp lệ, từ chối trạng thái không phù hợp/phiếu trùng; xác nhận sửa xong AVAILABLE và xuất lại IN_USE.
- History tiếp tục dạng bảng; 5 trạng thái không đổi; Diagnosis hiển thị Nguyên nhân / Chẩn đoán; editor/kho chuyển popup giữa màn hình.
- Backend: `cd backend && ../.venv/bin/python -m pytest tests -q` — 51 passed.
- Frontend: `npm run build` — passed.
- Playwright trên DB test riêng: `maintenance-flow.spec.ts`, `return-maintenance.spec.ts` — 5 passed; bốn flow cũ và luồng mới, vị trí popup desktop/mobile, History dạng bảng.


## 2026-09-27 — Maintenance estimate

- Input kết thúc thay bằng số giờ dự kiến; API chuyển estimate_hours sang due_at từ start_at, lưu History; end_at chỉ là thời điểm đóng thực tế.
- Bộ test Maintenance: 14 passed, gồm estimate giờ lẻ, chỉnh estimate, không tự đóng, từ chối số không dương/NaN/quá lớn và giữ hạn dự kiến khi hoàn tất.
- TypeScript/Vite build passed.
- Browser: maintenance-flow.spec.ts (onsite) — passed, nhập estimate rồi tạo/sửa/hoàn tất thành công. Live backend health OK, frontend phục vụ input mới.


## 2026-09-27 — Bảo trì nhanh / thu hồi tạo phiếu

- Form tạo trực tiếp hoàn tất nhanh, yêu cầu nguyên nhân và cách xử lý; không hiển thị estimate. Nhánh cần thời gian mở popup Thu hồi tạo bảo trì kèm estimate và kiểm soát quyền kho.
- Backend maintenance + warehouse: 26 passed. Có kiểm tra hoàn tất nhanh một lần lưu, giữ cấp phát/trạng thái/vị trí và snapshot.
- Browser: 6 passed (quick-maintenance, return-maintenance và bốn flow bảo trì đang mở); kiểm tra nhanh đóng ngay, chậm tạo phiếu mở, estimate và popup desktop/mobile.
- TypeScript/Vite build passed; không thay schema hoặc năm trạng thái Asset.


## 2026-09-27 — Popup lịch sử cho năm sự kiện

- Giữ DataTable, lọc sự kiện và điều hướng bàn phím của lịch sử. Nhập tài sản/Cấp phát/Thu hồi/Điều chuyển/Bảo trì có popup riêng theo thiết kế tham chiếu; các sự kiện còn lại giữ popup đầy đủ trước/sau.
- Popup dùng snapshot lịch sử, thông tin chứng từ kho chỉ đọc và nhãn danh mục loại; không lấy Model/Serial/vị trí hiện tại thay snapshot cũ. Không thêm ảnh minh họa hoặc trạng thái ngoài bộ năm trạng thái.
- Bảo trì hiển thị actor riêng với technician, thời gian sự kiện riêng với thời gian xử lý, dự kiến, vấn đề, nguyên nhân, cách xử lý, trạng thái phiếu, trạng thái Asset trước/sau và liên kết phiếu. Thu hồi có phiếu liên quan vẫn giữ chi tiết sửa chữa.
- `npm run build`: passed. Backend asset-events + maintenance-issue-flow: 19 passed. Browser history-popups + asset-events + maintenance-flow: 6 passed.
- Đã kiểm tra năm popup desktop/mobile, Enter/Escape, không tràn ngang, bản ghi nhập giữ Model cũ sau khi sửa hồ sơ. Đã xem ảnh chụp bảo trì desktop/mobile và điều chuyển desktop.


## 2026-09-28 — Trang chi tiết Bảo trì / Sửa chữa

- Refactor theo thiết kế: header số phiếu/trạng thái/thời gian/người xử lý, bốn bước Vấn đề–Nguyên nhân–Cách xử lý–Linh kiện và sidebar thiết bị/phiếu.
- Dùng ảnh thiết bị thật khi có; S/N, vị trí/người sử dụng hiện tại lấy API Asset. Thời gian xử lý = end_at - start_at; due_at hiển thị riêng. Không lấy created_at thay start_at.
- Phiếu mở có hoàn tất và menu thao tác theo quyền/trạng thái; phiếu đóng chỉ chỉnh sửa/xem lịch sử. Bảng linh kiện trình bày nội dung parts_replaced theo dòng; nhà cung cấp/chi phí là dữ liệu chung của phiếu. Chưa có liên kết vật tư/chứng từ kho, không tạo số lượng hoặc số phiếu xuất giả.
- TypeScript/Vite build: passed. Playwright maintenance-detail, maintenance-flow (4), quick-maintenance, return-maintenance: 7 distinct tests passed. Kiểm tra ảnh desktop/mobile và thời lượng 1 giờ 15 phút; test giao diện chạy lại sau chỉnh bảng linh kiện.
- Không thay model/API/schema hoặc năm trạng thái Asset.
