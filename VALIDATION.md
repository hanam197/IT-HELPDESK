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
