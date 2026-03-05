# 📖 Hướng Dẫn Setup TeacherBot - Gmail OAuth & Chạy Ứng Dụng

## 🎯 Mục Đích
Hướng dẫn chi tiết để:
- Tạo OAuth 2.0 credentials trên Google Cloud Console
- Cấu hình ứng dụng để kết nối Gmail
- Chạy ứng dụng bằng **1 dòng lệnh duy nhất**

---

## 📋 Bước 1: Tạo OAuth 2.0 Credentials trên Google Cloud Console

### 1.1. Tạo Project Mới

1. Truy cập **Google Cloud Console**: https://console.cloud.google.com
2. Nếu chưa có tài khoản Google, hãy tạo một tài khoản
3. Ở góc trên cùng, click **"Select a Project"** → **"NEW PROJECT"**
4. Nhập tên project: `TeacherBot` (hoặc tên bất kỳ)
5. Click **"CREATE"** rồi chờ project được tạo (1-2 phút)

### 1.2. Bật Gmail API

1. Tìm kiếm **"Gmail API"** trong thanh tìm kiếm ở trên cùng
2. Click vào **Gmail API**
3. Click nút **"ENABLE"**
4. Chờ API được bật (có thể mất vài giây)

### 1.3. Tạo OAuth 2.0 Credentials

1. Ở menu trái, click **"Credentials"**
2. Click nút **"+ CREATE CREDENTIALS"** ở phía trên
3. Chọn **"OAuth client ID"**
4. Nếu hiện bảng "OAuth consent screen", làm theo hướng dẫn:
   - Chọn **"External"** (hoặc **"Internal"** nếu là tài khoản công ty)
   - Click **"CREATE"**
   - Điền:
     - **App name**: `TeacherBot`
     - **User support email**: Email của bạn
     - **Developer contact**: Email của bạn
   - Click **"SAVE AND CONTINUE"** ở cuối trang
   - Bỏ qua các scope (click **SAVE AND CONTINUE**)
   - Bỏ qua test users (click **SAVE AND CONTINUE**)
   - Review và click **"BACK TO DASHBOARD"**

5. Quay lại **Credentials**, click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"** lần nữa
6. Chọn **Application type**: **Web application**
7. Điền **Name**: `TeacherBot Local Dev`
8. Scroll xuống **"Authorized redirect URIs"**
9. Thêm các URI sau (click **"+ ADD URI"**):
   ```
   http://localhost:5000/api/email/oauth2callback
   http://127.0.0.1:5000/api/email/oauth2callback
   http://192.168.0.102:5000/api/email/oauth2callback
   ```
   (Nếu máy bạn có IP khác, hãy thêm IP đó vào)

10. Click **"CREATE"**

### 1.4. Lấy Client ID & Client Secret

1. Sau khi tạo xong, bạn sẽ thấy một popup với **Client ID** và **Client Secret**
2. **Copy cả hai giá trị này** - sẽ cần dùng ở bước tiếp theo ⚠️

---

## 🔧 Bước 2: Cấu Hình Ứng Dụng

### 2.1. Tạo File `.env`

1. Mở Command Prompt / PowerShell
2. Chuyển tới thư mục dự án:
   ```powershell
   cd d:\OJT\testing\testing-local-deploy-version
   ```

3. Tạo file `.env`:
   ```powershell
   echo. > .env
   ```

4. Mở file `.env` với Notepad:
   ```powershell
   notepad .env
   ```

5. Dán nội dung sau và **thay thế** `YOUR_CLIENT_ID` và `YOUR_CLIENT_SECRET` bằng giá trị từ bước 1.4:
   ```
   # Gmail OAuth Credentials (từ Google Cloud Console)
   GMAIL_CLIENT_ID=YOUR_CLIENT_ID
   GMAIL_CLIENT_SECRET=YOUR_CLIENT_SECRET
   
   # AI API Keys
   OPENAI_API_KEY=sk-...
   MISTRAL_API_KEY=...
   CLAUDE_API_KEY=sk-ant-...
   GEMINI_API_KEY=AIza...
   
   # Environment
   SECRET_KEY=dev-secret-key
   ```

6. **Lưu** file (Ctrl+S)

### 2.2. Cấu Hình AI API Keys (Tùy Chọn)

Nếu muốn sử dụng các AI service:

**OpenAI (ChatGPT-4)**:
1. Truy cập: https://platform.openai.com/api-keys
2. Tạo API key mới
3. Copy vào `.env` dòng `OPENAI_API_KEY=sk-...`

**Mistral AI**:
1. Truy cập: https://console.mistral.ai
2. Tạo API key
3. Copy vào `.env`

**Claude (Anthropic)**:
1. Truy cập: https://console.anthropic.com/account/keys
2. Tạo API key
3. Copy vào `.env`

**Gemini (Google)**:
1. Truy cập: https://ai.google.dev
2. Tạo API key
3. Copy vào `.env`

---

## ⚡ Bước 3: Chạy Ứng Dụng (1 Dòng Lệnh)

### 3.1. Chạy Setup & Start Server

Mở **PowerShell** trong thư mục `testing-local-deploy-version`, rồi chạy:

```powershell
# Windows PowerShell
powershell -Command "python -m pip install -q -r requirements.txt 2>$null; python setup_env.py 2>$null; echo 'Server starting...'; python -m flask --app app run --debug"
```

Hoặc nếu muốn copy lệnh đơn giản hơn (1 dòng):
```powershell
python -m pip install -q -r requirements.txt; python -m flask --app app run --debug
```

### 3.2. Đợi Server Khởi Động

Bạn sẽ thấy:
```
 * Running on http://localhost:5000
```

Khi thấy dòng này, server đã sẵn sàng! ✅

---

## 🧪 Bước 4: Kiểm Tra Kết Nối Gmail

### 4.1. Mở Ứng Dụng

1. Mở trình duyệt
2. Truy cập: http://localhost:5000
3. Click vào **Tab Email** ở sidebar
4. Click **"Đăng nhập Gmail"**
5. Chọn tài khoản Google của bạn
6. **Cấp quyền** khi được hỏi
7. Bạn sẽ bị chuyển hướng về trang, thấy thông báo **"Gmail đã kết nối thành công!"** ✅

### 4.2. Tải Email

1. Sau khi đăng nhập thành công
2. Click **"Làm mới"** để tải danh sách email
3. Bạn sẽ thấy các email gần đây được phân loại theo chủ đề

---

## 🚀 Bước 5: Tùy Chỉnh & Triển Khai Trên Vercel (Tùy Chọn)

### 5.1. Upload Do Vercel

Nếu muốn lưu trữ public:

1. **Git Push**:
   ```powershell
   git add .
   git commit -m "feat: complete Gmail OAuth setup"
   git push origin main
   ```

2. **Kết nối GitHub với Vercel**:
   - Truy cập: https://vercel.com
   - Click **"New Project"**
   - Import repository từ GitHub
   - Tìm kiếm variable trong **Settings** → **Environment Variables**
   - Thêm tất cả biến từ `.env` file

3. Vercel sẽ tự động deploy mỗi khi bạn push code 🎉

---

## 🐛 Gỡ Lỗi & Hỏi Đáp

### ❓ "Error: Gmail OAuth chưa được cấu hình"
**Giải pháp**:
- Kiểm tra file `.env` có chứa `GMAIL_CLIENT_ID` và `GMAIL_CLIENT_SECRET` không?
- Nếu không, thêm vào lại (xem bước 2.1)
- Restart server: Bấm `Ctrl+C` rồi chạy lệnh ở bước 3.1 lại

### ❓ "not_authenticated" khi tải email
**Giải pháp**:
- Bạn chưa đăng nhập Gmail, hoặc đã hết phiên
- Click **"Đăng nhập Gmail"** lại
- Nếu vẫn lỗi, xóa token file: `data/users/gmail_token_*.pickle`

### ❓ "CORS error" hoặc "Connection refused"
**Giải pháp**:
- Server chưa chạy, hãy chạy lệnh ở bước 3.1
- Hoặc port 5000 bị chiếm, thay đổi port:
  ```powershell
  python -m flask --app app run --debug --port 8000
  ```

### ❓ "AttributeError: session"
**Giải pháp**:
- Có lỗi trong email.py khi import session
- Kiểm tra: `from flask import ..., session` có đúng không?
- Rebuild: `python setup_env.py`

---

## 📝 Tóm Tắt

| Bước | Hành Động | Thời Gian |
|------|----------|---------|
| 1 | Tạo Google Cloud Project + OAuth Credentials | 10-15 phút |
| 2 | Tạo & cấu hình file `.env` | 2-3 phút |
| 3 | Chạy ứng dụng (1 dòng lệnh) | <1 phút |
| 4 | Kiểm tra Gmail connection | <1 phút |
| **TOTAL** | | **~15 phút** |

---

## 🎓 Các Lệnh Hữu Ích

```powershell
# Cài đặt dependencies
pip install -r requirements.txt

# Setup environment (tạo database, init services)
python setup_env.py

# Chạy server (debug mode)
python -m flask --app app run --debug

# Chạy server (production mode)
python -m flask --app app run --host 0.0.0.0 --port 5000

# Kiểm tra health
curl http://localhost:5000/api/health

# Kiểm tra Gmail config
curl http://localhost:5000/api/email/oauth-config-check

# Git commit & push
git add .
git commit -m "feat: message"
git push origin main
```

---

**Chúc bạn thành công! 🎉**

Nếu gặp vấn đề, hãy:
1. Kiểm tra lại các bước 1-2
2. Xem logs trong terminal
3. Kiểm tra file `.env` có các biến cần thiết

**Need help?** Xem logs chi tiết bằng cách mở **DevTools** (F12) → **Console** tab
