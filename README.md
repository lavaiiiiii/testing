# TeacherBot - Trợ lý AI cho Giáo viên

Một ứng dụng chatbox AI đơn giản giúp giáo viên quản lý email, lên lịch hẹn, và lưu lịch sử hoạt động.

## Tính Năng

✨ **Chat với AI** - Trò chuyện với trợ lý AI hỗ trợ tiếng Việt
📧 **Quản lý Email Gmail** - Đọc, tóm tắt, và trả lời email tự động
📅 **Lên Lịch Hẹn** - Tạo và quản lý lịch hẹn với sinh viên/giáo viên khác
📜 **Lịch Sử Hoạt Động** - Lưu trữ toàn bộ lịch sử chat, email, và lịch hẹn

## Yêu Cầu Hệ Thống

- Python 3.8+
- pip (Python package manager)
- Một tài khoản OpenAI có API key
- Một tài khoản Google để sử dụng Gmail API

## Cài Đặt

## Chạy local nhanh (khuyến nghị)

Trên Windows PowerShell, từ thư mục project:

```powershell
./run_local.ps1
```

Script sẽ:
- kiểm tra `.env`
- kiểm tra `data/gmail_credentials.json`
- tự chọn Python từ virtualenv nếu có
- cài dependencies còn thiếu
- chạy server tại `http://localhost:5000`

### 1. Clone hoặc Extract Project

```bash
cd teacher-ai-assistant
```

### 2. Tạo Virtual Environment (Tuỳ chọn nhưng khuyến khích)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Cài Đặt Dependencies

```bash
cd backend
pip install -r ../requirements.txt
```

### 4. Thiết Lập API Keys

#### a. OpenAI API Key

1. Truy cập [OpenAI Platform](https://platform.openai.com)
2. Đăng nhập hoặc tạo tài khoản
3. Vào [API Keys](https://platform.openai.com/account/api-keys)
4. Tạo một API key mới
5. Copy API key

#### b. Gmail API

1. Truy cập [Google Cloud Console](https://console.cloud.google.com)
2. Tạo một project mới
3. Bật Gmail API:
   - Vào **APIs & Services** > **Library**
   - Tìm "Gmail API"
   - Click "Enable"
4. Tạo OAuth credentials:
   - Vào **APIs & Services** > **Credentials**
   - Click **Create Credentials** > **OAuth client ID**
   - Chọn **Desktop application**
   - Download JSON file
5. Rename file thành `gmail_credentials.json`
6. Copy vào thư mục `data/`

### 5. Cấu Hình Environment

1. Copy file `.env.example` thành `.env`:
   ```bash
   cp .env.example .env
   ```

2. Mở `.env` và điền thông tin:
   ```
   OPENAI_API_KEY=your-api-key-here
   MISTRAL_API_KEY=your-mistral-api-key
   CLAUDE_API_KEY=your-claude-api-key
   GEMINI_API_KEY=your-gemini-api-key

   AI_PRIMARY_PROVIDER=openai
   AI_PROVIDER_ORDER=openai,mistral,claude,gemini
   AI_DEFAULT_MAX_TOKENS=220
   AI_SUMMARY_MAX_TOKENS=180
   AI_REPLY_MAX_TOKENS=220
   AI_ANALYZE_MAX_TOKENS=180
   AI_TASK_PROVIDERS_SUMMARY=gemini,claude,mistral,openai
   AI_TASK_PROVIDERS_REPLY=claude,openai,mistral,gemini
   AI_TASK_PROVIDERS_ANALYZE=openai,gemini,claude,mistral
   GMAIL_CLIENT_ID=your-client-id
   GMAIL_CLIENT_SECRET=your-client-secret
   ```

### Cấu hình trên Vercel (quan trọng)

Vercel **không tự đọc file `.env` trong repo**. Bạn phải vào **Project Settings → Environment Variables** để set biến môi trường.

Tối thiểu cần:
- Ít nhất 1 AI key để chat không rơi vào demo mode: `OPENAI_API_KEY` (hoặc Mistral/Claude/Gemini)
- Gmail OAuth: `GMAIL_CLIENT_ID` + `GMAIL_CLIENT_SECRET`
   - Hoặc dùng `GMAIL_CREDENTIALS_JSON` (toàn bộ JSON OAuth client)
- `SECRET_KEY`

Redirect URI trong Google Cloud Console:
- `https://<your-vercel-domain>/api/email/oauth2callback`

### 6. Chạy Ứng Dụng

```bash
python app.py
```

Ứng dụng sẽ chạy tại `http://localhost:5000`

## Sử Dụng

### Chat với AI

1. Truy cập trang Chat
2. Nhập câu hỏi hoặc yêu cầu
3. Nhấn "Gửi" hoặc Shift+Enter

### Quản Lý Email

1. Vào tab Email
2. Xem danh sách email chưa đọc
3. Click vào email để xem chi tiết
4. Có thể:
   - **Tóm tắt**: AI sẽ tóm tắt nội dung email
   - **Trả lời tự động**: Chọn hành động (Đồng ý/Từ chối/Yêu cầu info) → AI sẽ soạn email trả lời
5. Tab "Soạn thảo" để gửi email thủ công

### Lên Lịch Hẹn

1. Vào tab Lịch hẹn
2. Tab "Sắp tới" để xem lịch hẹn
3. Tab "Tạo lịch hẹn mới" để:
   - Nhập tiêu đề
   - Nhập mô tả (tuỳ chọn)
   - Chọn ngày giờ
   - Nhập email người tham dự (tuỳ chọn, cách nhau bằng dấu phẩy)
   - Nhấn "Tạo lịch hẹn"

### Lịch Sử Hoạt Động

1. Vào tab Lịch sử
2. Xem toàn bộ hoạt động (chat, email, lịch hẹn)
3. Click "Xóa lịch sử" để xóa toàn bộ

## Cấu Trúc Project

```
teacher-ai-assistant/
├── backend/
│   ├── app.py              # Main Flask app
│   ├── config.py           # Configuration
│   ├── services/           # Business logic
│   │   ├── ai_service.py
│   │   ├── gmail_service.py
│   │   └── schedule_service.py
│   ├── models/             # Database models
│   │   ├── schedule.py
│   │   └── history.py
│   └── routes/             # API endpoints
│       ├── chat.py
│       ├── email.py
│       └── schedule.py
├── frontend/
│   ├── index.html          # Main UI
### 5. Thiết Lập OAuth Web Credentials

1. Tải file JSON credentials loại **Web application** (OAuth client ID) từ Google Cloud
2. Đặt tên file đó là `gmail_credentials.json` và đặt vào thư mục `data/` (hoặc chỉnh `Config` nếu khác)
3. Trong console Google, cấu hình **Redirect URI**: `http://localhost:5000/api/email/oauth2callback`
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── data/                   # Database & credentials
│   ├── assistant.db
│   ├── gmail_credentials.json
│   └── gmail_token.pickle
├── requirements.txt        # Python dependencies
├── .env                    # Configuration file
└── README.md
```

## Troubleshooting

### Lỗi Gmail Authentication

- Đảm bảo `gmail_credentials.json` nằm trong thư mục `backend/data/`
- Xóa file `gmail_token.pickle` nếu có lỗi xác thực, ứng dụng sẽ yêu cầu xác thực lại

### Lỗi OpenAI API

- Kiểm tra API key có hợp lệ không
- Kiểm tra quota và billing của OpenAI
- Đảm bảo kết nối internet ổn định

### Port 5000 đang được sử dụng

Chỉnh sửa file `.env`:
```
API_PORT=8000
```

Rồi truy cập `http://localhost:8000`

## Development

### Thêm tính năng mới

1. Tạo service mới trong `backend/services/`
2. Tạo route mới trong `backend/routes/`
3. Cập nhật `backend/app.py` để register blueprint
4. Cập nhật frontend trong `frontend/js/app.js`

### Database

- Sử dụng SQLite, database file: `data/assistant.db`
- Models được định nghĩa trong `backend/models/`
- Tự động khởi tạo tables khi ứng dụng chạy

### Multi-user data isolation

- Mỗi tài khoản Gmail đăng nhập sẽ có database riêng: `data/users/<gmail_email_sanitized>.db`
- Gmail token cũng tách theo tài khoản: `data/users/gmail_token_<gmail_email_sanitized>.pickle`
- Đăng nhập hỗ trợ chọn/đổi tài khoản (`select_account`) và hiển thị email đang kết nối trên UI

## API Endpoints

### Chat
- `POST /api/chat/message` - Gửi tin nhắn
   - Có thể truyền thêm `task` (`chat|summary|reply|analyze`) để route model
- `GET /api/chat/history` - Lấy lịch sử chat
- `POST /api/chat/summarize-email` - Tóm tắt email
- `POST /api/chat/generate-reply` - Tạo email trả lời
- `GET /api/chat/providers` - Xem provider AI đang cấu hình & fallback chain

### Email
- `GET /api/email/get-unread` - Lấy email chưa đọc
   - Hỗ trợ `filter`: `all|education|work|meeting|promotion|finance|personal|other`
- `POST /api/email/send-reply` - Gửi email
- `POST /api/email/summarize-by-date` - Tóm tắt email theo ngày (bảng người gửi + nội dung tóm tắt)
   - Endpoint này lấy toàn bộ email theo ngày (không áp bộ lọc category)

### Schedule
- `POST /api/schedule/create` - Tạo lịch hẹn
- `GET /api/schedule/list` - Lấy danh sách lịch hẹn
- `GET /api/schedule/upcoming` - Lấy lịch hẹn sắp tới
- `PATCH /api/schedule/<id>/update-status` - Cập nhật trạng thái

## License

MIT License - Tự do sử dụng cho mục đích cá nhân

## Hỗ Trợ

Nếu gặp vấn đề, vui lòng kiểm tra:
1. Tất cả dependencies đã cài đặt
2. API keys đã thiết lập đúng
3. Database có thể ghi được
4. Kết nối internet bình thường
