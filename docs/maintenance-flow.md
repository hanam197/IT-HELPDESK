# Bảo trì / Sửa chữa

## Phiếu và trạng thái thiết bị

Phiếu bảo trì có hai trạng thái: **Mới** (`open`, màu vàng) và **Hoàn tất** (`completed`, màu xanh). Tạo phiếu mặc định Mới; có thể chọn Hoàn tất để ghi nhận việc đã xử lý. Phiếu đã hoàn tất chỉ được xem; API từ chối mọi chỉnh sửa hoặc mở lại.

Trạng thái thiết bị vẫn gồm AVAILABLE / IN_USE / MAINTENANCE / RETIRED / DISPOSED. Ghi nhận hoặc cập nhật vấn đề không tự dừng thiết bị, thay người sử dụng, vị trí hoặc kho.

Nhóm vấn đề: Phần cứng, Mạng, Phần mềm, Nguồn điện, Thiết bị ngoại vi, Khác. Nội dung lỗi cụ thể lưu trong `problem`.

## Các thao tác

- **Nhập trực tiếp:** phiếu Mới có ô nhập vấn đề, nguyên nhân, cách xử lý, kết quả, ghi chú, nhóm vấn đề và người xử lý ngay trên trang; dùng Lưu thay đổi để lưu nháp. Không cần mở popup chỉnh sửa.
- **Dừng thiết bị để sửa:** chỉ phiếu đang mở, thiết bị AVAILABLE hoặc IN_USE. Chuyển thiết bị sang MAINTENANCE, giữ người sử dụng/vị trí/kho.
- **Hoàn tất:** bắt buộc nguyên nhân, cách xử lý và kết quả. Đã khắc phục (`FIXED`) đưa thiết bị về AVAILABLE; Không khắc phục được (`UNREPAIRABLE`) đưa về RETIRED với nhãn Hư / Ngừng sử dụng. Kết thúc cấp phát nếu có, giữ nguyên vị trí và kho. Quy tắc này cũng áp dụng khi tạo phiếu đã hoàn tất ngay từ đầu.
- **Thu hồi về kho:** đóng cấp phát và cập nhật kho. Thu hồi về AVAILABLE hoàn tất phiếu mở; về MAINTENANCE giữ phiếu mở; về RETIRED đóng phiếu và giữ lý do trong ghi chú.
- **Thu hồi và tạo phiếu:** từ popup tạo bảo trì hoặc thao tác thu hồi, chọn kho, nguyên nhân, nhóm vấn đề và người xử lý. Thiết bị chuyển MAINTENANCE và phiếu Mới được tạo trong cùng giao dịch.
- **Ngừng sử dụng:** đóng phiếu mở, bổ sung lý do trong ghi chú và chuyển thiết bị RETIRED. Thanh lý là thao tác riêng.

Một tài sản chỉ có một phiếu mở. Phiếu mở không chặn cấp phát nếu tài sản AVAILABLE; tài sản MAINTENANCE không được cấp phát. Thời gian kết thúc không trước thời gian bắt đầu hoặc ở tương lai. Chi phí phải hữu hạn, không âm.

## Linh kiện

`replacement_asset_ids` lưu các ID tài sản được chọn. Chỉ chọn tài sản khác thiết bị đang sửa, có loại **Linh kiện** (tương thích tên Component/Components), trạng thái AVAILABLE và còn trong kho. Backend kiểm tra các điều kiện này và chặn trùng lặp.

Khi lưu lựa chọn mới, hệ thống tự tạo chứng từ ISSUE, chuyển linh kiện sang IN_USE, loại khỏi tồn kho và ghi lịch sử có liên kết phiếu/thiết bị nhận linh kiện trong cùng giao dịch. Yêu cầu quyền kho. Lưu lại cùng lựa chọn không tạo thêm chứng từ. Không xóa linh kiện đã xuất khỏi phiếu; dùng thao tác thu hồi kho để trả lại khi cần. Linh kiện đã lưu vẫn hiển thị sau khi chuyển khỏi kho. Nội dung `parts_replaced` cũ được giữ và hiển thị để bảo toàn lịch sử.

## Giao diện

Chi tiết desktop gồm tiêu đề/mã phiếu, trạng thái, thời gian, người xử lý và nhóm vấn đề; các ô Vấn đề / Nguyên nhân / Cách xử lý / Kết quả xử lý; linh kiện, ghi chú và thẻ thiết bị. Không hiển thị số thứ tự, khối Thông tin phiếu lặp lại hay thời gian kết thúc dự kiến.

Bố cục được kiểm tra ở 1366×768 và 1440×900, không cuộn trang với nội dung thông thường. Nội dung dài cuộn trong ô. Mobile xếp dọc, cho phép cuộn để đọc đầy đủ.

Các form dùng popup. Trường `due_at` và API `estimate_hours` được giữ để tương thích dữ liệu cũ, nhưng không xuất hiện trong form và chi tiết mới.

## Lịch sử và migration

Tạo phiếu, cập nhật nội dung, dừng thiết bị và hoàn tất đều ghi lịch sử tài sản với người thực hiện và thời gian. Snapshot chứa nội dung xử lý, linh kiện, chi phí và ghi chú. RETURN/RETIRED đóng phiếu trong cùng giao dịch và chứa snapshot phiếu trong sự kiện tương ứng.

Migration `0008` tách phiếu bảo trì khỏi Ticket, chuyển loại cũ sang nhóm vấn đề, giữ liên kết/loại cũ trong ghi chú.

Migration `0009` thêm `replacement_asset_ids`, chuẩn hóa phiếu đang mở về Mới và phiếu đã kết thúc về Hoàn tất. Khi đổi trạng thái cũ, tên trạng thái trước đó được giữ trong ghi chú. Danh mục trạng thái dư được lưu trữ; tạo loại Linh kiện nếu chưa có. Không thay trạng thái tài sản, cấp phát, giao dịch kho hoặc lịch sử cũ. Sao lưu trước nâng cấp; khôi phục bản sao nếu cần quay lại.

Migration `0010` thêm kết quả xử lý và khôi phục vị trí còn thiếu từ lịch sử ghi nhận gần nhất. Phiếu cũ chưa có kết quả tiếp tục hiển thị chưa ghi nhận, không tự suy đoán kết quả sửa chữa. Thiết bị chưa thanh lý phải có vị trí; ngừng sử dụng giữ vị trí/kho, thanh lý mới kết thúc vị trí. Xuất chỉ cho người dùng vẫn giữ vị trí đã ghi nhận gần nhất đến khi được điều chuyển.
