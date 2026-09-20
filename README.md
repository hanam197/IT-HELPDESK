# IT Helpdesk & Asset Management System

Ứng dụng nội bộ end-to-end: **React + TypeScript + Vite → FastAPI → PostgreSQL**. Kiến trúc modular monolith, Asset là bản ghi trung tâm; vị trí và người chịu trách nhiệm là hai lịch sử độc lập.

## Chạy bằng Docker Compose

Yêu cầu Docker Engine và Docker Compose v2.

```bash
cp .env.example .env
# Sửa POSTGRES_PASSWORD, SECRET_KEY và SEED_PASSWORD trong .env.
# Có thể sinh secret bằng: openssl rand -hex 32
# POSTGRES_PASSWORD dùng ký tự chữ/số để dùng an toàn trong connection URL.
docker compose up --build -d
# Chỉ chạy lệnh dưới cho môi trường demo, database đang trống:
docker compose exec backend python -m app.seed
```

Truy cập **http://localhost:8080**. Các tài khoản demo `admin`, `manager`, `support`, `viewer` dùng mật khẩu `SEED_PASSWORD` bạn vừa cấu hình. Seed có kiểm tra database và không ghi đè dữ liệu đã tồn tại. Không tự seed khi khởi động server.

API và PostgreSQL chỉ ở mạng Docker nội bộ; Nginx là entry point. Migration chạy trước Uvicorn. Database và attachments có named volumes. Đặt `FRONTEND_URL` đúng URL thực tế để QR hoạt động trên máy khác.

Cho production, **không chạy demo seed**:

```bash
docker compose exec backend python -m app.bootstrap
```

Lệnh này hỏi tên tài khoản và mật khẩu, tạo admin đầu tiên và vocabulary cần thiết; không tạo thiết bị giả. Sau đó vào Settings tạo Asset Types, Locations và Users. Triển khai sau reverse proxy HTTPS và đặt `SECURE_COOKIE=true`. Không bật giá trị này khi chỉ chạy HTTP local vì trình duyệt sẽ không gửi cookie.

## Chạy trực tiếp để phát triển

Yêu cầu Python 3.12+, Node.js 22+, PostgreSQL 16+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
npm ci --prefix frontend
cp backend/.env.example backend/.env
# Sửa backend/.env: DATABASE_URL, SECRET_KEY, SEED_PASSWORD.
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/python -m app.seed
../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal thứ hai:

```bash
npm run dev --prefix frontend -- --port 5173
```

Mở **http://localhost:5173**. Vite proxy `/api` tới backend cổng 8000; frontend không có dữ liệu giả hoặc fallback demo. Có thể dùng `DATABASE_URL=sqlite:///./helpdesk.db` để phát triển nhanh, nhưng PostgreSQL là database triển khai và cần dùng để kiểm thử concurrency.

Swagger: **http://localhost:8000/docs**, OpenAPI: `/openapi.json`. Đăng nhập qua UI trước; các request ghi cần header `X-Requested-With: Helpdesk`.

## Chức năng

- **Dashboard:** 10 KPI, phân bố ticket/asset, hoạt động 7 ngày, attention và audit gần đây; liên kết drill-down.
- **Assets:** tạo/sửa thiết bị, serial/code unique, loại thiết bị có capability flags, Overview / Network / Location / Assignment / Tickets / Maintenance / History / Ports. QR mở `/assets/{id}` và in nhãn bằng trình duyệt.
- **Operations:** move, assign, transfer, return; chuyển vị trí không thay đổi người chịu trách nhiệm. Assignment không làm thay đổi location. Thu hồi ghi tình trạng trả; lịch sử luôn được giữ lại.
- **Helpdesk:** số `INC-YYYY-XXXXX`, status/priority/category từ database, người báo/người xử lý, hạn xử lý, timeline, comment/note nội bộ, attachments tối đa 10 MB, liên kết asset/location/KB, tạo maintenance và tạo KB từ ticket.
- **Network/IPAM:** VLAN, subnet IPv4/IPv6, gateway/DNS, interface/MAC/hostname, IP, switch port, native/tagged VLAN. Tìm IP/MAC/hostname/asset/switch/port. Một IP có duy nhất một bản ghi; V1 không cho phép gán trùng IP bằng override.
- **Maintenance:** liên kết ticket, diagnosis/action/parts/cost/vendor; đưa thiết bị vào Repair, khôi phục trạng thái phù hợp khi hoàn tất hoặc hủy; bảo toàn trường hợp thiết bị được trả trong lúc đang sửa.
- **Knowledge Base:** nội dung Markdown, category, draft/published/archived, liên kết ticket. Markdown không render HTML tùy ý.
- **Reports:** bảng có filter, grouping, CSV/XLSX; inventory, assignments/history, tickets, IP/subnet/port và maintenance. Có tổng chi phí, thời gian giải quyết trung bình và thống kê lỗi lặp lại. File export áp dụng cùng query/filter và trung hòa công thức spreadsheet.
- **Global search:** code/serial/IP/MAC/hostname/ticket/station/user/KB, truy tiếp asset và các liên kết. Phím tắt Ctrl/Cmd+K.
- **Administration:** local login, users/roles, master data, audit logs chỉ đọc, archive qua API cho các bản ghi không còn được tham chiếu.

Giao diện dùng Tailwind, Lucide, TanStack Query/Table và các component theo cấu trúc shadcn/ui với Radix Dialog/Slot. Các bảng có tìm kiếm, chọn cột, sort và phân trang. Trường Photo hiện nhận URL ảnh; file upload trực tiếp áp dụng cho ticket attachments.

## Phân quyền

| Role | Quyền ghi |
|---|---|
| ADMIN | Toàn bộ module; cấu hình users, master data, asset types, locations |
| IT_MANAGER | Assets, tickets, network, maintenance, KB, operations |
| IT_SUPPORT | Tickets, operations, maintenance, KB và liên kết KB |
| VIEWER | Chỉ đọc; không xem internal notes |

Backend kiểm tra quyền ở tất cả endpoint ghi; frontend ẩn thao tác tương ứng. JWT được lưu trong cookie HttpOnly/SameSite Strict, hết hạn sau 8 giờ; mật khẩu hash Argon2. Mỗi request kiểm tra lại user/role trong database. Đăng xuất xóa cookie. Không mở CORS, request ghi bắt buộc custom header để ngăn form CSRF. Có giới hạn thử đăng nhập trong tiến trình API.

## Database và tính toàn vẹn

```mermaid
erDiagram
    ASSET_TYPES ||--o{ ASSETS : categorizes
    ASSETS ||--o{ LOCATION_HISTORY : location
    LOCATIONS ||--o{ LOCATION_HISTORY : destination
    LOCATIONS o|--o{ LOCATIONS : parent
    ASSETS ||--o{ ASSIGNMENTS : responsibility
    USERS ||--o{ ASSIGNMENTS : receives
    ASSETS ||--o{ INTERFACES : network
    INTERFACES o|--o{ IP_ADDRESSES : allocation
    VLANS ||--o{ SUBNETS : network
    SUBNETS ||--o{ IP_ADDRESSES : contains
    ASSETS ||--o{ SWITCH_PORTS : ports
    ASSETS o|--o{ TICKETS : incidents
    ASSETS ||--o{ MAINTENANCE : service
    TICKETS o|--o{ MAINTENANCE : repair
    TICKETS ||--o{ TICKET_ACTIVITIES : timeline
    TICKETS ||--o{ TICKET_ARTICLES : references
    ARTICLES ||--o{ TICKET_ARTICLES : knowledge
```

- Foreign keys và unique constraints nằm trong database, không chỉ ở form.
- Partial unique index cho `location_history(asset_id) WHERE ended_at IS NULL` và `assignments(asset_id) WHERE returned_at IS NULL`.
- Move/assign/return/transfer khóa asset bằng `SELECT FOR UPDATE` trên PostgreSQL. Đóng record cũ và tạo record mới trong cùng transaction.
- Số ticket/maintenance/KB dùng counter upsert và atomic update, tránh cách `count + 1` có race condition.
- Lịch sử và audit không có endpoint sửa/xóa. Archive có kiểm tra tham chiếu; không xóa cứng lịch sử nghiệp vụ.
- Mọi mutation qua service lưu audit trong cùng transaction. Password hash và storage key không trả qua API/audit.
- Timestamp lưu UTC, normalize UTC khi trả API, UI hiển thị theo timezone trình duyệt. KPI “today” tính theo UTC.
- `MasterData(group, code)` là định danh ổn định. Admin đổi display name và thêm giá trị; không đổi code/group của record cũ. Các code hệ thống như `assigned`, `available`, `repair`, `completed`, `resolved` điều khiển vòng đời nên không được archive. Danh sách loại thiết bị, location và lựa chọn trạng thái được đọc từ database.

## Cấu trúc code

```text
backend/
  app/
    database.py       Settings, SQLAlchemy engine/session
    models.py         Relational entities + database constraints
    schemas.py        Typed Pydantic DTOs + operational schemas
    security.py       Passwords, JWT cookie, RBAC, login limiter
    services.py       Validation, transactions, lifecycle, audit
    main.py           REST routes, queries, search, dashboard, export
    integrations.py   Protocol cho network inventory adapters tương lai
    defaults.py       Vocabulary khởi tạo
    bootstrap.py      Tạo production admin
    seed.py           Demo data idempotent
  alembic/versions/   Frozen schema migrations
  tests/             Integration tests
frontend/
  src/
    App.tsx           Layout, authentication, global search
    Dashboard.tsx     KPI, charts, attention, recent activity
    Resources.tsx     Resource tables, filters, reports
    Detail.tsx        Asset/ticket/KB details và timeline
    config.ts         Form definitions; giá trị tham chiếu lấy từ API
    components/      Reusable table, drawer editor, UI primitives
  tests/             Playwright end-to-end tests
compose.yaml          PostgreSQL + FastAPI + Nginx
```

SQLAlchemy Session đóng vai trò unit-of-work/repository; service giữ business rules. `NetworkInventoryProvider` chỉ là interface cho tích hợp tương lai, chưa có discovery/SNMP/vendor API.

## Kiểm thử

```bash
cd backend
../.venv/bin/python -m pytest -q
# PostgreSQL test database phải RIÊNG, có thể xóa toàn bộ schema:
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost/helpdesk_test \
  ../.venv/bin/python -m pytest -q
```

**Không trỏ TEST_DATABASE_URL vào database đang sử dụng:** fixture tạo và xóa các bảng test. Mặc định dùng SQLite tạm riêng.

Với backend/frontend đang chạy và demo seed đã tạo:

```bash
cd frontend
npx playwright install chromium
DEMO_PASSWORD='your_seed_password' npx playwright test
npm run build
```

Test bao gồm: login/RBAC/CSRF, location và assignment history, transfer/return, duplicate code/serial/IP, MAC/IP validation, asset capability, ticket → maintenance → resolution → KB, attachment, search, export, concurrent ticket numbers, timezone drill-down, repair/return state restoration; trình duyệt kiểm tra module navigation, tìm IP tới asset, tạo ticket/timeline và lifecycle thiết bị.

## Vận hành và phạm vi

- Backup PostgreSQL và volume `attachments` cùng thời điểm; test restore trước khi dùng production.
- Dùng một tiến trình API trong V1; login limiter hiện ở memory, cần shared store nếu scale nhiều worker.
- Metadata cho dropdown được tải chung; cần bổ sung lookup phân trang cho inventory lớn. Các truy vấn dashboard/report hiện hướng tới quy mô nội bộ V1, chưa benchmark tải lớn.
- Notifications lấy từ attention query; chưa có push/email notification.
- Không có discovery, SNMP, monitoring thời gian thực, vendor API, chatbot, native mobile, microservices hoặc Kubernetes.
- Docker Compose chưa chạy được trong môi trường xây dựng vì không cài Docker; migration/seed/test và browser đã chạy với PostgreSQL 16 native. Xem [VALIDATION.md](VALIDATION.md) để biết bằng chứng kiểm chứng.
