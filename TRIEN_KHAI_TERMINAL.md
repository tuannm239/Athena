# Triển Khai Athena Bằng Terminal — Từng Lệnh

Hướng dẫn này làm toàn bộ bằng dòng lệnh (CLI), copy–dán chạy được. Mỗi dịch vụ
cần **đăng nhập một lần** (mở trình duyệt để xác thực tài khoản của bạn) — đó là
phần duy nhất không thể tự động hóa.

> Yêu cầu máy có sẵn: `git`, `node` + `npm` (≥ 18), và `curl`.
> Ký hiệu `# 👉` = bước sẽ mở trình duyệt để bạn đăng nhập.

---

## 0. Cài các CLI cần dùng (một lần duy nhất)

```bash
# GitHub CLI  (macOS: brew install gh | Windows: winget install GitHub.cli)
#   Linux: xem https://github.com/cli/cli/blob/trunk/docs/install_linux.md
npm  install -g vercel              # Vercel CLI (frontend)
npm  install -g neonctl             # Neon CLI (database)
npm  install -g @upstash/cli        # Upstash CLI (redis)
# Render CLI (macOS): brew install render
#   Khác: tải tại https://render.com/docs/cli
```

Tạo sẵn một secret cho backend và lưu vào biến shell để dùng ở các bước sau:

```bash
export JWT_SECRET="$(openssl rand -hex 32)"
export ADMIN_EMAIL="admin@athena.local"       # đổi thành email bạn muốn
export ADMIN_PASSWORD="DoiMatKhauNay123"       # đổi thành mật khẩu ≥ 8 ký tự
echo "JWT_SECRET = $JWT_SECRET"                # copy lại, phòng khi cần
```

---

## 1. GitHub — đưa code lên

```bash
cd /duong-dan/toi/Athena          # vào thư mục dự án
gh auth login                     # 👉 đăng nhập GitHub (chọn HTTPS, mở trình duyệt)

git init 2>/dev/null; git add -A
git commit -m "Athena" 2>/dev/null || echo "đã có commit"
git branch -M main

# Tạo repo và đẩy code lên trong một lệnh:
gh repo create athena --private --source=. --remote=origin --push
```

Kiểm tra: `gh repo view --web` sẽ mở kho code trên trình duyệt.

---

## 2. Neon — tạo PostgreSQL và lấy DATABASE_URL

```bash
neonctl auth                                   # 👉 đăng nhập Neon (mở trình duyệt)

# Tạo project (mặc định có 1 database tên "neondb"):
neonctl projects create --name athena

# Lấy chuỗi kết nối TRỰC TIẾP (không pooled):
neonctl connection-string --database-name neondb
```

Lệnh trên in ra chuỗi dạng `postgresql://...neon.tech/neondb?sslmode=require`.
**Đổi phần đầu** `postgresql://` → `postgresql+psycopg://` rồi lưu lại:

```bash
# Dán chuỗi Neon vào đây (đã đổi scheme thành postgresql+psycopg://):
export DATABASE_URL="postgresql+psycopg://USER:PWD@ep-xxx.aws.neon.tech/neondb?sslmode=require"
```

> Không cần tạo bảng — Athena tự chạy migration khi khởi động.

---

## 3. Upstash — tạo Redis và lấy REDIS_URL

```bash
upstash auth login                             # 👉 nhập email + API key Upstash

# Tạo database Redis (đổi region gần bạn, vd: ap-northeast-1):
upstash redis create --name athena --region ap-northeast-1

# Xem chi tiết để lấy endpoint + password:
upstash redis get athena
```

Từ kết quả, ghép chuỗi TLS `rediss://` (chú ý hai chữ "s"):

```bash
# Dạng: rediss://default:<PASSWORD>@<ENDPOINT>:6379
export REDIS_URL="rediss://default:AxYz...@sunny-cat-12345.upstash.io:6379"
```

---

## 4. Render — triển khai backend từ render.yaml

Repo đã có sẵn `render.yaml`. Có 2 cách; cách A là terminal thuần.

### Cách A — Render CLI

```bash
render login                                   # 👉 đăng nhập Render (mở trình duyệt)

# Tạo service theo blueprint render.yaml trong repo:
render blueprint launch
```

CLI sẽ hỏi các biến bí mật (đánh dấu `sync: false` trong render.yaml). Dán vào:

```
DATABASE_URL              -> giá trị $DATABASE_URL ở Bước 2
REDIS_URL                 -> giá trị $REDIS_URL   ở Bước 3
JWT_SECRET                -> giá trị $JWT_SECRET  ở Bước 0
ATHENA_SEED_ADMIN_EMAIL   -> $ADMIN_EMAIL
ATHENA_SEED_ADMIN_PASSWORD-> $ADMIN_PASSWORD
```

> Nếu bản Render CLI của bạn chưa có `blueprint launch`, dùng **Cách B**:
> mở https://dashboard.render.com → **New → Blueprint** → chọn repo `athena`
> → điền đúng 5 biến trên → **Apply**. (Đây là cú bấm chuột duy nhất.)

Theo dõi log tới khi thấy `Launching uvicorn ...` rồi lấy URL backend:

```bash
export ATHENA_API_URL="https://athena-api.onrender.com"   # đổi thành URL Render thật của bạn
curl -s "$ATHENA_API_URL/health"     # phải trả về {"status":"ok"}
```

---

## 5. Vercel — triển khai frontend

Frontend nằm trong thư mục `web/`, nên ta chạy Vercel **từ trong `web/`** để nó
lấy `web` làm gốc.

```bash
cd web
vercel login                                   # 👉 đăng nhập Vercel (mở trình duyệt)
vercel link --yes                              # liên kết thư mục web với 1 project mới

# Khai báo URL backend cho môi trường Production:
printf '%s' "$ATHENA_API_URL" | vercel env add ATHENA_API_URL production

# Build & deploy production, lấy URL công khai:
vercel --prod
cd ..
```

`vercel --prod` in ra địa chỉ công khai, dạng `https://athena-xxxx.vercel.app`.

---

## 6. Kiểm tra toàn hệ thống (từ terminal)

```bash
# Backend sống & thành phần phụ:
curl -s "$ATHENA_API_URL/health"          ; echo
curl -s "$ATHENA_API_URL/health/full"     ; echo   # database & redis phải "ok"

# Tư thế an toàn (không giao dịch, bắt buộc phê duyệt):
curl -s "$ATHENA_API_URL/pilot/status"    ; echo

# Đăng nhập bằng tài khoản admin đã seed tự động:
curl -s -X POST "$ATHENA_API_URL/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" ; echo
```

Nếu lệnh login trả về `access_token` → mọi thứ đã chạy. Mở URL Vercel ở Bước 5
trên trình duyệt và đăng nhập bằng chính email/mật khẩu đó.

🎉 **Xong.** Địa chỉ công khai của bạn là URL Vercel.

---

## Cập nhật về sau (chỉ một lệnh)

```bash
git push          # Render + Vercel tự build lại; migration chạy tự động
```

---

## Bảng xử lý sự cố nhanh

| Lệnh báo lỗi / hiện tượng | Cách xử lý |
|---|---|
| `/health/full` → `database: unavailable` | kiểm tra `DATABASE_URL` giữ đúng `postgresql+psycopg://…?sslmode=require` |
| `/health/full` → `redis: unavailable` | kiểm tra `REDIS_URL` bắt đầu bằng `rediss://` (hai chữ s) |
| Log Render: *"JWT_SECRET is the development default"* | đặt lại `JWT_SECRET` ≥ 32 ký tự trong Render, deploy lại |
| Web gọi API lỗi | `vercel env add ATHENA_API_URL production` lại cho đúng URL Render, rồi `vercel --prod` |
| Login trả 401 | seed chưa chạy → đảm bảo đã điền `ATHENA_SEED_ADMIN_EMAIL/PASSWORD` ở Bước 4, deploy lại |

> Tất cả bước "👉 đăng nhập" là phần bắt buộc dùng tài khoản cá nhân của bạn —
> không thể tự động hóa. Mọi thứ còn lại trong repo đã được chuẩn bị sẵn.
