# 🔄 AI Provider Round-Robin System

## 🎯 Mục Đích

Tự động luân phiên giữa các AI providers để:
- ✅ Tránh hết quota/token trên một provider
- ✅ Phân tải request đều giữa các providers
- ✅ Tự động chuyển sang provider khác khi gặp lỗi
- ✅ Chỉ chuyển Demo Mode khi TẤT CẢ providers hết quota

---

## 🔄 Cách Hoạt Động

### 1. Round-Robin Rotation

Mỗi lần chat, hệ thống sẽ **luân phiên** chọn AI provider khác nhau:

```
Request 1: OpenAI
Request 2: Mistral
Request 3: Claude
Request 4: OpenAI (quay lại)
Request 5: Mistral
...
```

### 2. Quota Error Detection

Khi provider trả về lỗi quota/rate limit, hệ thống tự động:

1. **Phát hiện lỗi quota** (HTTP 429, 402, 403, 401 hoặc error message chứa "quota", "rate_limit", "insufficient_quota")
2. **Đánh dấu provider đó là "unhealthy"**
3. **Set cooldown time**:
   - Lỗi quota: **30 phút**
   - Lỗi thường: **5 phút**
4. **Bỏ qua provider đó** trong rotation
5. **Chuyển sang provider tiếp theo**

### 3. Auto-Recovery

Sau khi hết cooldown, provider tự động:
- ✅ Được đánh dấu lại là "healthy"
- ✅ Quay trở lại rotation
- ✅ Log: "✅ OPENAI cooldown ended - back to healthy"

### 4. Demo Mode Fallback

Chỉ khi **TẤT CẢ** providers không khả dụng:
- 🎭 Chuyển sang Demo Mode
- 📝 Trả về demo responses
- 💡 Hiển thị thông báo rõ ràng

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│            User Request (Chat Message)          │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│      generate_response() - Main Entry Point     │
│                                                 │
│  1. Normalize & optimize messages               │
│  2. Build provider chain (round-robin)          │
│  3. Try each provider sequentially              │
└─────────────────┬───────────────────────────────┘
                  │
      ┌───────────┴──────────┐
      ▼                      ▼
┌──────────────┐      ┌──────────────┐
│_build_       │      │_get_next_    │
│provider_     │      │round_robin_  │
│chain()       │      │provider()    │
│              │      │              │
│• Get healthy │      │• Rotate index│
│  providers   │      │• Pick next   │
│• Apply       │      │  healthy     │
│  round-robin │      │  provider    │
└──────┬───────┘      └──────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│          For each provider in chain:            │
│                                                 │
│  1. Check _is_provider_healthy()                │
│     ├─ In cooldown? → Skip                      │
│     └─ Healthy? → Try                           │
│                                                 │
│  2. Call _call_provider()                       │
│     ├─ Success? → Return response ✅            │
│     └─ Error? ↓                                 │
│                                                 │
│  3. Check _is_quota_error()                     │
│     ├─ Quota error? → 30min cooldown 🚫        │
│     └─ Other error? → 5min cooldown ⚠️         │
│                                                 │
│  4. Mark _mark_provider_failed()                │
│                                                 │
│  5. Continue to next provider                   │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
          All failed? → Demo Mode 🎭
```

---

## 📊 Provider Health Tracking

### Data Structure

```python
provider_health = {
    'openai': {
        'failed_at': datetime(2026, 3, 5, 14, 30),
        'error': 'Rate limit exceeded',
        'is_quota_error': True,
        'cooldown_minutes': 30
    },
    'mistral': {
        'failed_at': datetime(2026, 3, 5, 14, 25),
        'error': 'Connection timeout',
        'is_quota_error': False,
        'cooldown_minutes': 5
    }
}
```

### Health States

| State | Icon | Description | Action |
|-------|------|-------------|--------|
| **Healthy** | ✅ | Provider OK | Use in rotation |
| **Cooldown (Quota)** | 🚫 | Hết quota/rate limit | Skip for 30min |
| **Cooldown (Error)** | ⚠️ | Lỗi tạm thời | Skip for 5min |
| **Demo Mode** | 🎭 | Tất cả failed | Use demo responses |

---

## 🎨 UI Indicators

### Chat Provider Status Bar

**Khi healthy:**
```
🔄 AI Rotation: ✅ OPENAI [5] | ✅ MISTRAL [3] | ✅ CLAUDE [2] | Luân phiên tự động
```

**Khi có provider trong cooldown:**
```
🔄 AI Rotation: ✅ OPENAI [8] | ⏸️ MISTRAL (25min) [3] | ✅ CLAUDE [5] | Luân phiên tự động
```

**Khi tất cả trong cooldown:**
```
🎭 Demo Mode - Tất cả AI providers đang cooldown: OPENAI: 25min, MISTRAL: 18min, CLAUDE: 10min
```

### Message Badges

Mỗi message từ AI có badge hiển thị provider:

- 🤖 OPENAI (màu xanh)
- 🤖 MISTRAL (màu xanh)
- 🤖 CLAUDE (màu xanh)
- 🎭 Demo (màu cam)

---

## 🔍 Error Detection

### Quota Error Keywords

```python
QUOTA_ERROR_KEYWORDS = [
    'quota', 'rate_limit', 'insufficient_quota', 
    'quota_exceeded', 'rate limit', 'too many requests',
    'billing', 'overloaded', 'capacity', 'throttled',
    'exceeded your current quota'
]
```

### HTTP Status Codes

```python
QUOTA_STATUS_CODES = [
    429,  # Too Many Requests
    402,  # Payment Required
    403,  # Forbidden (quota)
    401   # Unauthorized (expired quota)
]
```

---

## 🧪 Testing Round-Robin

### Test 1: Normal Rotation

```powershell
# Send 5 messages
curl -X POST http://localhost:5000/api/chat/message `
  -H "Content-Type: application/json" `
  -d '{"message":"Hello 1"}'
  
curl -X POST http://localhost:5000/api/chat/message `
  -H "Content-Type: application/json" `
  -d '{"message":"Hello 2"}'
  
curl -X POST http://localhost:5000/api/chat/message `
  -H "Content-Type: application/json" `
  -d '{"message":"Hello 3"}'
```

**Expected logs:**
```
🔄 Round-robin selected: OPENAI
✅ OPENAI responded successfully

🔄 Round-robin selected: MISTRAL
✅ MISTRAL responded successfully

🔄 Round-robin selected: CLAUDE
✅ CLAUDE responded successfully

🔄 Round-robin selected: OPENAI
✅ OPENAI responded successfully
```

### Test 2: Quota Error Handling

Simulate quota error (shut down one provider):

```powershell
# Remove Mistral key temporarily
$env:MISTRAL_API_KEY=""

# Send requests
curl -X POST http://localhost:5000/api/chat/message ...
```

**Expected logs:**
```
🔄 Round-robin selected: MISTRAL
🚫 MISTRAL HẾT QUOTA - chuyển sang provider khác
🔴 MISTRAL QUOTA: ... (cooldown: 30min)

🔄 Trying next: OPENAI
✅ OPENAI responded successfully
```

### Test 3: All Providers Down

```powershell
# Remove all API keys
$env:OPENAI_API_KEY=""
$env:MISTRAL_API_KEY=""
$env:CLAUDE_API_KEY=""

# Send request
curl -X POST http://localhost:5000/api/chat/message ...
```

**Expected response:**
```json
{
  "success": true,
  "response": "Xin chào! Tôi là TeacherBot... (Demo Mode)",
  "provider": "demo",
  "demo_mode": true
}
```

---

## 📊 Monitoring & Debugging

### Check Provider Status

```powershell
# See current provider health
curl http://localhost:5000/api/chat/providers
```

**Response:**
```json
{
  "success": true,
  "providers": {
    "configured_providers": ["openai", "mistral", "claude"],
    "active_chain": ["mistral", "claude", "openai"],
    "provider_health": {
      "openai": {
        "healthy": true,
        "usage_count": 15
      },
      "mistral": {
        "healthy": false,
        "usage_count": 8,
        "cooldown_remaining_minutes": 25.3,
        "error": "Rate limit exceeded",
        "is_quota_error": true
      },
      "claude": {
        "healthy": true,
        "usage_count": 12
      }
    },
    "rotation_index": 23,
    "last_provider_used": "openai",
    "demo_mode": false
  }
}
```

### View Logs in Terminal

Khi chạy server với `--debug`, bạn sẽ thấy:

```
🔄 Round-robin selected: OPENAI
✅ OPENAI responded successfully

🔄 Round-robin selected: MISTRAL  
🚫 MISTRAL HẾT QUOTA - chuyển sang provider khác
🔴 MISTRAL QUOTA: Rate limit exceeded for requests (cooldown: 30min)

⏭️  Bỏ qua MISTRAL (đang cooldown ~25min)

🔄 Round-robin selected: CLAUDE
✅ CLAUDE responded successfully
```

---

## ⚙️ Configuration

### Default Settings

```python
# In AIService.__init__()
provider_cooldown_minutes = 5           # Lỗi thường
quota_error_cooldown_minutes = 30      # Hết quota/rate limit
```

### Override Settings (Optional)

Thêm vào `.env`:

```bash
# Đổi thời gian cooldown (phút)
AI_PROVIDER_COOLDOWN_MINUTES=10
AI_QUOTA_ERROR_COOLDOWN_MINUTES=60
```

### Provider Order

Mặc định trong `config.py`:

```python
AI_PROVIDER_ORDER='openai,mistral,claude,gemini'
```

Có thể override:

```bash
# .env
AI_PROVIDER_ORDER=claude,openai,mistral,gemini
```

---

## 🎓 Benefits

### Before (No Rotation)

```
Request 1 → OpenAI (success)
Request 2 → OpenAI (success)
Request 3 → OpenAI (success)
...
Request 50 → OpenAI (QUOTA ERROR ❌)
Request 51 → Mistral (success)
Request 52 → Mistral (success)
...
Request 100 → Mistral (QUOTA ERROR ❌)
Request 101 → Claude (success)
...
ALL OUT → Demo Mode 🎭
```

**Problem**: Nhanh hết quota trên một provider!

### After (Round-Robin)

```
Request 1 → OpenAI (success)
Request 2 → Mistral (success)
Request 3 → Claude (success)
Request 4 → OpenAI (success)
Request 5 → Mistral (success)
Request 6 → Claude (success)
...
Request 150 → Still rotating! ✅
Request 151 → Still rotating! ✅
```

**Benefit**: Quota phân tán đều, không bị hết một lúc!

---

## 💡 Smart Features

### 1. Intelligent Cooldown

- **Quota errors**: 30 phút cooldown (khả năng phục hồi cao)
- **Network/other errors**: 5 phút cooldown (có thể là tạm thời)

### 2. Auto-Recovery

Provider tự động quay lại rotation sau cooldown:

```
14:00 - Mistral fails (quota error)
14:05 - Still in cooldown (25min left)
14:15 - Still in cooldown (15min left)
14:30 - Cooldown ended! ✅ Back to rotation
```

### 3. Real-time Status

Frontend hiển thị status bar with:
- ✅ Healthy providers (màu xanh)
- ⏸️ Providers in cooldown (với thời gian còn lại)
- 🎭 Demo mode warning (màu cam)

### 4. Usage Tracking

Mỗi provider có counter:
```
OPENAI [25] | MISTRAL [18] | CLAUDE [22]
```
→ Dễ monitor load balancing

---

## 🐛 Debugging

### Check Provider Health

```javascript
// Browser Console (F12)
fetch('/api/chat/providers', {credentials: 'include'})
  .then(r => r.json())
  .then(d => console.table(d.providers.provider_health))
```

### Reset Provider Health

```python
# Python console or add API endpoint
from backend.services.ai_service import AIService
service = AIService()
service.provider_health = {}  # Clear all cooldowns
```

### Force Demo Mode Test

```python
# Temporarily disable all providers
export OPENAI_API_KEY=""
export MISTRAL_API_KEY=""
export CLAUDE_API_KEY=""
export GEMINI_API_KEY=""
```

Then send chat message → should see Demo Mode

---

## 📈 Performance Comparison

| Scenario | Before (No Rotation) | After (Round-Robin) |
|----------|---------------------|---------------------|
| **Request distribution** | 100% on primary | 25-35% each provider ✅ |
| **Time to quota limit** | ~50-100 requests | ~200-400 requests ✅ |
| **Recovery time** | Must wait for cooldown | Auto-switch to other ✅ |
| **User experience** | Interruption when quota hits | Seamless ✅ |
| **Cost efficiency** | Burn through one API fast | Balanced usage ✅ |

---

## 🔐 Security & Best Practices

### 1. Error Message Sanitization

```python
# Don't expose API keys in error messages
error_msg = str(error_message)[:200]  # Truncate
```

### 2. Quota Error Privacy

```python
# Log quota errors but don't store sensitive data
logger.warning(f"Provider {provider} quota exceeded")
# Don't log: API key, full error payloads
```

### 3. Rate Limit Compliance

```python
# Respect provider rate limits with cooldowns
# Don't retry immediately on 429 errors
```

---

## 🚀 Usage Statistics

View usage stats:

```javascript
// Browser Console
fetch('/api/chat/providers', {credentials: 'include'})
  .then(r => r.json())
  .then(d => {
    console.log('Usage:', d.providers.provider_usage);
    console.log('Rotation index:', d.providers.rotation_index);
    console.log('Last used:', d.providers.last_provider_used);
  })
```

Example output:
```json
{
  "provider_usage": {
    "openai": 25,
    "mistral": 18,
    "claude": 22,
    "gemini": 0,
    "demo": 3
  },
  "rotation_index": 68,
  "last_provider_used": "claude"
}
```

---

## 🎯 Configuration Examples

### Example 1: Prefer OpenAI, fallback to others

```bash
# .env
AI_PRIMARY_PROVIDER=openai
AI_PROVIDER_ORDER=openai,mistral,claude,gemini
```

Result: Round-robin starts with OpenAI, then rotates through all

### Example 2: Task-specific providers

```bash
# .env
AI_TASK_PROVIDERS_CHAT=openai,mistral
AI_TASK_PROVIDERS_SUMMARY=claude
AI_TASK_PROVIDERS_REPLY=mistral
```

Result:
- Chat → OpenAI/Mistral only
- Summary → Claude preferred
- Reply → Mistral preferred

### Example 3: Single provider with fallback

```bash
# .env
AI_PROVIDER_ORDER=claude,openai
```

Result: Try Claude first, fallback to OpenAI if fails

---

## 📝 Example Scenarios

### Scenario 1: Normal Operation

```
User: "Xin chào"
System: 🔄 Round-robin → OPENAI
Response: ✅ OPENAI responded
UI: 🤖 OPENAI badge

User: "Hôm nay thế nào?"
System: 🔄 Round-robin → MISTRAL
Response: ✅ MISTRAL responded
UI: 🤖 MISTRAL badge

User: "Tóm tắt email"
System: 🔄 Round-robin → CLAUDE
Response: ✅ CLAUDE responded
UI: 🤖 CLAUDE badge
```

### Scenario 2: Quota Hit

```
User: "Hello"
System: 🔄 Round-robin → OPENAI
Response: 🚫 OPENAI QUOTA ERROR
System: 🔴 OPENAI cooldown: 30min
System: ⏭️ Trying next: MISTRAL
Response: ✅ MISTRAL responded
UI: 🤖 MISTRAL badge

User: "Next message"
System: 🔄 Round-robin → MISTRAL (skip OPENAI - cooldown)
Response: ✅ MISTRAL responded
UI: 🤖 MISTRAL badge
```

### Scenario 3: All Providers Down

```
User: "Hello"
System: 🔄 Round-robin → OPENAI
Response: 🚫 QUOTA ERROR
System: ⏭️ Trying MISTRAL
Response: 🚫 QUOTA ERROR
System: ⏭️ Trying CLAUDE
Response: 🚫 QUOTA ERROR
System: ❌ All providers failed → Demo Mode
UI: 🎭 Demo badge
Response: "Xin chào! Tôi là TeacherBot... (Demo Mode)"
```

---

## 🔧 Advanced Configuration

### Custom Cooldown Times

Edit `backend/services/ai_service.py`:

```python
self.provider_cooldown_minutes = 10          # Change from 5 to 10
self.quota_error_cooldown_minutes = 60       # Change from 30 to 60
```

### Add New Provider

1. Add API key to `.env`:
   ```bash
   NEW_PROVIDER_API_KEY=xxx
   ```

2. Add to `config.py`:
   ```python
   NEW_PROVIDER_API_KEY = os.getenv('NEW_PROVIDER_API_KEY')
   ```

3. Add to `ai_service.py`:
   ```python
   def _call_new_provider(self, messages, max_tokens):
       # Implementation
   ```

4. Update provider detection:
   ```python
   if Config.NEW_PROVIDER_API_KEY:
       configured.append('new_provider')
   ```

---

## 📞 Troubleshooting

### Problem: Provider stuck in cooldown

**Solution:**
```python
# Clear health status
from backend.services.ai_service import AIService
service = AIService()
service.provider_health = {}
```

### Problem: Round-robin not rotating

**Solution:**
Check if only one provider is configured
```bash
# .env
# Make sure multiple providers have keys
OPENAI_API_KEY=sk-xxx
MISTRAL_API_KEY=xxx
CLAUDE_API_KEY=sk-ant-xxx
```

### Problem: Always using same provider

**Check:**
1. Other providers might be in cooldown
2. Check task-specific overrides in config
3. View `/api/chat/providers` to see active chain

---

**🎉 Bây giờ hệ thống luân phiên AI providers hoạt động hoàn hảo!**

- 🔄 Request được phân tải đều
- 🚫 Tự động skip provider hết quota
- ⏰ Auto-recovery sau cooldown
- 🎭 Demo mode chỉ khi thực sự cần

**Refresh browser (F5) để test ngay!** 🚀
