# 🚀 TeacherBot - Trợ Lý AI Cho Giáo Viên

**Quick Start - Chỉ 1 dòng lệnh!**

## ⚡ Cách Nhanh Nhất (30 giây)

### 1️⃣ Clone/Download Project
```powershell
cd d:\OJT\testing\testing-local-deploy-version
```

### 2️⃣ Chạy Server - 1 Dòng Lệnh
```powershell
.\run_app.ps1
```

Hoặc nếu trên Command Prompt:
```cmd
run_app.bat
```

### 3️⃣ Mở Ứng Dụng
Truy cập: http://localhost:5000

---

## 📖 Hướng Dẫn Chi Tiết

### Setup Gmail OAuth (Lần Đầu Tiên)

**Bước 1: Tạo Google Cloud Project**
1. Vào: https://console.cloud.google.com
2. Tạo project mới: **"TeacherBot"**
3. Bật **Gmail API**
4. Tạo **OAuth 2.0 Credentials** (Web Application)
5. Thêm Redirect URI:
   ```
   http://localhost:5000/api/email/oauth2callback
   ```

**Bước 2: Cấu Hình Environment**
1. Tạo file `.env` trong folder này:
   ```
   GMAIL_CLIENT_ID=YOUR_ID_HERE
   GMAIL_CLIENT_SECRET=YOUR_SECRET_HERE
   ```

**Bước 3: Chạy & Kiểm Tra**
- Mở: http://localhost:5000
- Click tab **"Email"**
- Click **"Đăng nhập Gmail"**
- Chọn tài khoản Google
- Cấp quyền

Xong! ✅

---

## 🛠️ Các Lệnh Hữu Ích

```powershell
# Chỉ cài dependencies
pip install -r requirements.txt

# Chỉ khởi tạo database
python setup_env.py

# Chạy server DEBUG mode
python -m flask --app app run --debug

# Chạy server PRODUCTION mode
python -m flask --app app run --host 0.0.0.0 --port 5000

# Kiểm tra health
curl http://localhost:5000/api/health

# Kiểm tra Gmail config
curl http://localhost:5000/api/email/oauth-config-check

# Kiểm tra session (development only)
curl http://localhost:5000/api/debug/session
```

---

## 🎯 Tính Năng

✅ **Chat AI** - Hỗ trợ 4 AI providers (OpenAI, Mistral, Claude, Gemini)  
✅ **Email Management** - AI phân loại email tự động  
✅ **Schedule Management** - Quản lý lịch hẹn, đánh dấu hoàn thành/chỉnh sửa/xóa  
✅ **Gmail OAuth** - Đăng nhập an toàn với Gmail  
✅ **History Tracking** - Lưu lịch sử mọi hoạt động  
✅ **Markdown Support** - Hỗ trợ định dạng markdown trong chat  
✅ **Multi-language** - Giao diện tiếng Việt  

---

## 🐛 Gỡ Lỗi

### ❓ "Port 5000 already in use"
```powershell
# Chạy trên port khác
python -m flask --app app run --debug --port 8000
```

### ❓ "Gmail chưa được cấu hình"
- Kiểm tra file `.env` có `GMAIL_CLIENT_ID` không?
- Restart server sau khi thêm

### ❓ "not_authenticated" khi tải email
- Click "Đăng nhập Gmail" lại
- Hoặc xóa: `data/users/gmail_token_*.pickle`

### ❓ Module import errors
```powershell
# Cài lại dependencies
pip install -r requirements.txt --force-reinstall

# Hoặc dùng virtual environment
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
.\run_app.ps1
```

---

## 📁 Cấu Trúc Project

```
testing-local-deploy-version/
├── backend/
│   ├── models/       # Database models (User, Schedule, History)
│   ├── routes/       # API endpoints (chat, email, schedule, user)
│   ├── services/     # AI services (OpenAI, Mistral, Claude, Gemini)
│   ├── utils/        # Helpers (user context, etc)
│   ├── app.py        # Flask application
│   └── config.py     # Configuration
├── frontend/
│   ├── index.html    # Main UI
│   ├── css/style.css # Styling
│   └── js/app.js     # Client-side logic
├── data/             # Database files (auto-created)
├── setup_env.py      # Setup script
├── run_app.ps1       # PowerShell startup
├── run_app.bat       # CMD startup
├── requirements.txt  # Dependencies
├── SETUP_GUIDE.md    # Detailed setup guide
└── README.md         # This file
```

---

## 🔑 Environment Variables

```bash
# Gmail OAuth
GMAIL_CLIENT_ID=xxx
GMAIL_CLIENT_SECRET=xxx

# AI APIs (Optional - at least one needed for chat)
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...
CLAUDE_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...

# Flask
SECRET_KEY=dev-secret-key
DEBUG=True
```

---

## 💡 Tips

1. **First time?** Read [SETUP_GUIDE.md](./SETUP_GUIDE.md) for detailed instructions
2. **Need to reset?** Delete `data/` folder and run `python setup_env.py` again
3. **Behind proxy?** Set environment variable: `HTTP_PROXY` and `HTTPS_PROXY`
4. **Production deploy?** See [vercel.json](./vercel.json) for Vercel setup
5. **Check logs?** Look at terminal output when running `run_app.ps1`

---

## 📝 Git Usage

```powershell
# View changes
git status

# Commit changes
git add .
git commit -m "feat: your feature description"

# Push to GitHub
git push origin main

# View history
git log --oneline -10
```

---

## ⚙️ Configuration Details

### Session & Auth
- Session cookies enabled with SameSite=Lax for OAuth redirects
- User context tracked via Gmail email (sanitized for file paths)
- Per-user token storage in `data/users/gmail_token_*.pickle`

### Database
- SQLite for all data (auto-created in `data/` folder)
- Per-user database for schedules & history
- Shared database for user profiles

### AI Models (Automatically upgraded)
- **OpenAI**: GPT-4 mini
- **Mistral**: Mistral medium  
- **Claude**: Claude 3.5 Sonnet
- **Gemini**: Gemini 1.5 Pro

### Token Optimization
- Max context messages: 6
- Max input chars: 2800
- Adaptive response length based on task

---

## 🆘 Need Help?

1. Check terminal output for error messages
2. Open DevTools (F12) → Console for client-side errors
3. Run `/api/debug/session` to check session state
4. Check `/api/status` for configuration status
5. Read logs in console when `DEBUG=True`

---

**Chúc bạn thành công! 🎉**

For detailed setup: See [SETUP_GUIDE.md](./SETUP_GUIDE.md)
