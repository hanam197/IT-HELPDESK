# Validation record

Kiểm chứng ngày 2026-09-20 trong workspace hiện tại.

| Hạng mục | Kết quả |
|---|---|
| TypeScript + Vite production build | PASS |
| PostgreSQL 16 migration `upgrade head` | PASS |
| PostgreSQL migration `downgrade base` → `upgrade head` trên DB test riêng | PASS |
| Demo seed trên PostgreSQL 16 | PASS |
| Backend integration suite trên PostgreSQL | 9/9 PASS |
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

## Browser scenarios

1. Đăng nhập, tìm `192.168.20.80`, mở PRN-012, xem Network/Location/Tickets/History.
2. Quick Create ticket, tìm ticket vừa tạo, mở detail và ghi timeline.
3. Tải toàn bộ module chính, không có JavaScript error; điều hướng mobile.
4. Tạo asset, move, assign, return, tạo maintenance; xác nhận status Repair và assignment history.

Hai cảnh báo deprecation từ Starlette TestClient/httpx/anyio không làm fail test. Frontend production output đã tách vendor chunks; build không còn cảnh báo chunk lớn hơn 500 kB.

Các test chưa thay thế UAT với dữ liệu và quy trình thật. README nêu các giới hạn V1: metadata lookup chưa phân trang, login limiter trong một process, notification chưa push/email, Photo dùng URL, chưa benchmark tải lớn.
