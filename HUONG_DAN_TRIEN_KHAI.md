# Hướng Dẫn Triển Khai Athena — Từng Bước

Hướng dẫn này đưa Athena từ mã nguồn trên máy lên **một trang web công khai
chạy thật**, không yêu cầu bạn có kinh nghiệm DevOps. Bạn sẽ dùng 5 dịch vụ
(đều có gói miễn phí):

| Dịch vụ | Vai trò | Lưu trữ gì |
|---|---|---|
| **GitHub** | mã nguồn | kho code của bạn |
| **Neon** | cơ sở dữ liệu | PostgreSQL (quyết định & bằng chứng) |
| **Upstash** | bộ nhớ đệm | Redis (dữ liệu tạm, tốc độ cao) |
| **Render** | backend | API Athena (FastAPI) |
| **Vercel** | frontend | giao diện web Athena (Next.js) |

> **Thứ tự rất quan trọng:** làm **Database và Redis trước**, rồi tới
> **Backend**, cuối cùng là **Frontend**. Mỗi bước nói rõ bạn bấm gì, copy gì.

> ⏱️ **Thời gian dự kiến:** khoảng **30–45 phút**, phần lớn là chờ hệ thống build.

> 💡 **Về chi phí:** tất cả dịch vụ dưới đây đều có gói miễn phí đủ để dùng thử.
> Gói miễn phí của Neon và Render sẽ "ngủ" khi không dùng, nên lần truy cập đầu
> tiên sau một lúc yên tĩnh sẽ mất thêm vài giây để "thức dậy". Đó là bình thường.

---

## Chuẩn bị trước khi bắt đầu

Bạn cần tài khoản ở: [github.com](https://github.com),
[neon.tech](https://neon.tech), [upstash.com](https://upstash.com),
[render.com](https://render.com), [vercel.com](https://vercel.com).

👉 **Mẹo:** Với 4 dịch vụ cuối (Neon, Upstash, Render, Vercel) hãy **đăng nhập
bằng chính tài khoản GitHub** của bạn — như vậy việc kết nối kho code chỉ còn
một cú bấm.

Mở sẵn một file ghi chú (Notepad) để dán tạm các "chuỗi bí mật" (secret) mà bạn
sẽ copy giữa các dịch vụ. **Tuyệt đối không đưa các secret này vào code.**

**Tạo sẵn một secret ngay bây giờ** (bạn sẽ cần cho backend). Trên máy Mac/Linux
mở Terminal và chạy:

```bash
openssl rand -hex 32
```

Copy dòng dài nó in ra — đó là `JWT_SECRET` của bạn. (Nếu dùng Windows không có
`openssl`, bạn có thể dùng bất kỳ chuỗi ngẫu nhiên ≥ 32 ký tự nào.)

---

## Bước 1 — Đưa code lên GitHub

Nếu code đã ở trên GitHub rồi, bỏ qua sang Bước 2. Nếu chưa, trong Terminal tại
thư mục dự án:

```bash
git init
git add .
git commit -m "Athena"
git branch -M main
git remote add origin https://github.com/<ten-cua-ban>/athena.git
git push -u origin main
```

Thay `<ten-cua-ban>` bằng tên tài khoản GitHub của bạn. Tải lại trang kho code
trên GitHub — bạn sẽ thấy tất cả các file.

---

## Bước 2 — Tạo cơ sở dữ liệu (Neon)

1. Vào [neon.tech](https://neon.tech) và đăng nhập.
2. Bấm **New Project**. Đặt tên `athena`. Chọn khu vực (region) gần bạn nhất
   (ví dụ Singapore). Bấm **Create**.
3. Ở trang dự án, tìm mục **Connection string**. Chọn kiểu
   **"Direct connection"** (KHÔNG chọn "Pooled") và copy. Nó trông như thế này:

   ```
   postgresql://alex:AbCd1234@ep-cool-name-123.ap-southeast-1.aws.neon.tech/athena?sslmode=require
   ```

4. **Sửa nhẹ một chỗ** để driver của Athena hiểu được: đổi phần đầu từ
   `postgresql://` thành `postgresql+psycopg://`. Kết quả:

   ```
   postgresql+psycopg://alex:AbCd1234@ep-cool-name-123.ap-southeast-1.aws.neon.tech/athena?sslmode=require
   ```

5. Dán chuỗi này vào Notepad, ghi nhãn **DATABASE_URL**. Giữ nguyên phần
   `?sslmode=require` ở cuối — Neon bắt buộc phải có.

> ✅ Bạn **không cần** tự tạo bảng nào cả. Athena tự động tạo toàn bộ bảng khi
> khởi động lần đầu.

---

## Bước 3 — Tạo bộ nhớ đệm (Upstash Redis)

1. Vào [upstash.com](https://upstash.com), đăng nhập, mở tab **Redis**.
2. Bấm **Create Database**. Đặt tên `athena`. Chọn region gần bạn. Giữ **TLS**
   bật (mặc định đã bật). Bấm **Create**.
3. Ở trang database, kéo xuống mục **Connect** và tìm chuỗi kết nối bắt đầu bằng
   `rediss://` (chú ý **hai chữ "s"** — nghĩa là bảo mật). Nó trông như:

   ```
   rediss://default:AxYz...@sunny-cat-12345.upstash.io:6379
   ```

4. Copy vào Notepad, ghi nhãn **REDIS_URL**.

---

## Bước 4 — Triển khai Backend (Render)

Athena đã có sẵn file `render.yaml` — bản "thiết kế" (blueprint) mô tả cho Render
biết cách build và chạy backend, nên bước này gần như chỉ bấm **Approve**.

1. Vào [render.com](https://render.com) và đăng nhập bằng GitHub.
2. Bấm **New → Blueprint**.
3. Chọn kho **athena** của bạn. Render sẽ tự tìm thấy `render.yaml` và hiện một
   dịch vụ tên **athena-api**. Bấm **Apply / Create**.
4. Render sẽ yêu cầu bạn điền các giá trị bí mật cần thiết. Điền từ Notepad:

   | Ô cần điền | Giá trị |
   |---|---|
   | `DATABASE_URL` | chuỗi Neon ở Bước 2 |
   | `REDIS_URL` | chuỗi Upstash ở Bước 3 |
   | `JWT_SECRET` | chuỗi `openssl rand -hex 32` ở phần Chuẩn bị |
   | `ATHENA_SEED_ADMIN_EMAIL` | email bạn muốn dùng cho tài khoản admin đầu tiên |
   | `ATHENA_SEED_ADMIN_PASSWORD` | mật khẩu (≥ 8 ký tự) cho admin đó |

   (Ô tùy chọn `ALPHAVANTAGE_API_KEY` có thể để trống — Athena vẫn hiển thị dữ
   liệu thị trường mẫu, có ghi rõ là "mẫu", khi chưa có key.)

5. Bấm **Create / Deploy**. Render bắt đầu build backend (vài phút). Mở tab
   **Logs** — bạn sẽ thấy lần lượt:

   ```
   [start] Applying database migrations (alembic upgrade head)…
   [start] Running idempotent seed…
   [start] Created initial ADMIN user: <email của bạn>
   [start] Launching uvicorn on 0.0.0.0:10000 …
   ```

   Nghĩa là: các bảng dữ liệu đã được tạo và tài khoản admin đã được thiết lập
   **tự động**.

6. Khi hiện chữ **Live**, copy URL công khai của backend ở đầu trang, dạng
   `https://athena-api.onrender.com`. Lưu vào Notepad, ghi nhãn **ATHENA_API_URL**.

7. Kiểm tra nhanh: mở `https://athena-api.onrender.com/health` trên trình duyệt.
   Bạn phải thấy `{"status":"ok"}`.

---

## Bước 5 — Triển khai Frontend (Vercel)

1. Vào [vercel.com](https://vercel.com), đăng nhập bằng GitHub.
2. Bấm **Add New → Project** và chọn (import) kho **athena** của bạn.
3. **Quan trọng — đặt thư mục gốc:** trong màn hình import, tìm mục **Root
   Directory** và đặt là **`web`** (giao diện web nằm trong thư mục con này).
   Vercel sẽ tự nhận diện Next.js và lấy cấu hình build từ `vercel.json` có sẵn.
4. Mở mục **Environment Variables** và thêm một biến:

   | Tên | Giá trị |
   |---|---|
   | `ATHENA_API_URL` | URL Render ở Bước 4 (vd `https://athena-api.onrender.com`) |

5. Bấm **Deploy**. Vercel build trang web (vài phút) rồi hiện cho bạn một địa
   chỉ công khai dạng `https://athena.vercel.app`.

6. Mở địa chỉ đó — bạn sẽ thấy màn hình đăng nhập của Athena.

---

## Bước 6 — Đăng nhập và xác nhận

1. Ở màn hình đăng nhập, dùng **email và mật khẩu admin** bạn đặt ở Bước 4.
2. Bạn sẽ vào **Dashboard**. Thử bấm vào **Market**, mở một công ty, xem
   **Portfolio** và **Reports** — toàn bộ ứng dụng đã chạy thật.

🎉 **Athena đã được triển khai.** Địa chỉ công khai của bạn chính là URL Vercel
ở Bước 5.

---

## Vận hành hằng ngày (nên biết)

- **Cập nhật ứng dụng:** chỉ cần `git push` lên nhánh `main`. Render và Vercel
  tự động triển khai lại. Việc chạy migration cơ sở dữ liệu diễn ra tự động mỗi
  lần deploy backend — bạn không cần làm thủ công.
- **Lần truy cập đầu sau khi "ngủ" hơi chậm:** gói miễn phí của Neon và Render
  ngủ khi không dùng; yêu cầu đầu tiên đánh thức chúng trong vài giây, sau đó
  nhanh bình thường.
- **Kiểm tra sức khỏe hệ thống:** `https://<url-render>/health` phải luôn trả về
  `{"status":"ok"}`. Xem chi tiết hơn ở `/health/full`.
- **Dữ liệu an toàn trên máy chủ:** các quyết định và bằng chứng nằm trong Neon
  (cơ sở dữ liệu của bạn). Một số tùy chọn (ghi chú, watchlist, giao diện) được
  lưu trong trình duyệt ở bản thử nghiệm này.

---

## Nếu gặp trục trặc

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Log backend: *"JWT_SECRET is the development default"* | Chưa đặt `JWT_SECRET` (hoặc quá ngắn) | đặt secret ≥ 32 ký tự trong Render → Environment, deploy lại |
| Log backend: lỗi kết nối database | `DATABASE_URL` sai hoặc thiếu `?sslmode=require` | copy lại chuỗi **direct** của Neon, giữ `postgresql+psycopg://` và `?sslmode=require` |
| `/health/full` báo `redis: unavailable` | `REDIS_URL` sai | copy lại chuỗi `rediss://` của Upstash |
| Web mở được nhưng gọi dữ liệu lỗi | `ATHENA_API_URL` trên Vercel sai | đặt đúng URL Render, deploy lại trên Vercel |
| Không đăng nhập được | Chưa đặt biến seed admin khi deploy lần đầu | đặt `ATHENA_SEED_ADMIN_EMAIL`/`PASSWORD` trong Render rồi deploy lại, hoặc bấm Register để tạo tài khoản mới |

---

## Tư thế an toàn (không thay đổi, theo thiết kế)

Athena **không bao giờ** đặt lệnh giao dịch, **không** kết nối với công ty chứng
khoán, và **bắt buộc bạn** phê duyệt mọi quyết định. Trong ứng dụng không hề có
đường dẫn nào để giao dịch hay chuyển tiền.

---

*Athena hỗ trợ; bạn là người quyết định.*
