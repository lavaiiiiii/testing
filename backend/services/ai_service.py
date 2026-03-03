import os
import sys
import requests
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

# Demo responses khi hết quota
DEMO_RESPONSES = {
    "tóm tắt": "Đây là tóm tắt email:\n- Điểm chính 1: Nội dung quan trọng\n- Điểm chính 2: Thông tin cần chú ý\n- Hành động: Cần phản hồi trong 24h",
    "lịch": "Tôi đề xuất lên lịch hẹn vào ngày mai lúc 14:00 để thảo luận chi tiết.",
    "default": "Xin chào! Tôi là TeacherBot - trợ lý AI cho giáo viên. Tôi có thể giúp bạn với:\n- Soạn tài liệu giáo dục\n- Phân tích email\n- Lên lịch hẹn\n- Và nhiều hơn nữa!\n\n(Hiện đang ở mode Demo - hết quota OpenAI)"
}

class AIService:
    def __init__(self):
        self.timeout = Config.AI_REQUEST_TIMEOUT
        self.max_context_messages = Config.AI_MAX_CONTEXT_MESSAGES
        self.max_input_chars = Config.AI_MAX_INPUT_CHARS
        self.max_system_prompt_chars = Config.AI_MAX_SYSTEM_PROMPT_CHARS
        self.default_max_tokens = Config.AI_DEFAULT_MAX_TOKENS
        self.task_max_tokens = {
            'chat': Config.AI_DEFAULT_MAX_TOKENS,
            'summary': Config.AI_SUMMARY_MAX_TOKENS,
            'reply': Config.AI_REPLY_MAX_TOKENS,
            'analyze': Config.AI_ANALYZE_MAX_TOKENS
        }
        self.provider_order = [
            p.strip().lower() for p in Config.AI_PROVIDER_ORDER.split(',') if p.strip()
        ]
        self.primary_provider = Config.AI_PRIMARY_PROVIDER
        self.task_provider_overrides = {
            'chat': self._parse_provider_list(Config.AI_TASK_PROVIDERS_CHAT),
            'summary': self._parse_provider_list(Config.AI_TASK_PROVIDERS_SUMMARY),
            'reply': self._parse_provider_list(Config.AI_TASK_PROVIDERS_REPLY),
            'analyze': self._parse_provider_list(Config.AI_TASK_PROVIDERS_ANALYZE)
        }
        self.last_provider_used = None
        self.provider_usage = {
            'openai': 0,
            'mistral': 0,
            'claude': 0,
            'gemini': 0,
            'demo': 0
        }

        self.configured_providers = self._detect_configured_providers()

        if not self.configured_providers:
            print("⚠️  Không có AI provider khả dụng - sử dụng Demo Mode")
    
    def generate_response(self, messages, max_tokens=None, task='chat'):
        """Generate AI response using multi-provider fallback chain"""
        if max_tokens is None:
            max_tokens = self.task_max_tokens.get(task, self.default_max_tokens)

        normalized_messages = self._normalize_messages(messages)
        optimized_messages = self._optimize_messages_for_tokens(normalized_messages)

        if not self.configured_providers:
            self.last_provider_used = 'demo'
            self.provider_usage['demo'] += 1
            return self._get_demo_response(optimized_messages)

        providers = self._build_provider_chain(task=task)
        last_error = None

        for provider in providers:
            try:
                response = self._call_provider(provider, optimized_messages, max_tokens)
                if response and response.strip():
                    self.last_provider_used = provider
                    if provider in self.provider_usage:
                        self.provider_usage[provider] += 1
                    return response
            except Exception as e:
                last_error = f"{provider}: {str(e)}"
                print(f"⚠️  {provider} lỗi, chuyển provider tiếp theo: {str(e)}")

        print(f"⚠️  Tất cả AI providers đều lỗi. Last error: {last_error}")
        self.last_provider_used = 'demo'
        self.provider_usage['demo'] += 1
        return self._get_demo_response(optimized_messages)

    def _parse_provider_list(self, value):
        if not value:
            return []
        return [p.strip().lower() for p in value.split(',') if p.strip()]

    def _detect_configured_providers(self):
        configured = []

        if Config.OPENAI_API_KEY:
            configured.append('openai')
        if Config.MISTRAL_API_KEY:
            configured.append('mistral')
        if Config.CLAUDE_API_KEY:
            configured.append('claude')
        if Config.GEMINI_API_KEY:
            configured.append('gemini')

        return configured

    def _build_provider_chain(self, task='chat'):
        ordered = []
        task_overrides = self.task_provider_overrides.get(task, [])

        for provider in task_overrides:
            if provider in self.configured_providers and provider not in ordered:
                ordered.append(provider)

        if not ordered and self.primary_provider in self.configured_providers:
            ordered.append(self.primary_provider)

        for provider in self.provider_order:
            if provider in self.configured_providers and provider not in ordered:
                ordered.append(provider)

        for provider in self.configured_providers:
            if provider not in ordered:
                ordered.append(provider)

        return ordered

    def _normalize_messages(self, messages):
        normalized = []
        for msg in messages or []:
            role = msg.get('role', 'user')
            if role not in ['system', 'user', 'assistant']:
                role = 'user'

            content = msg.get('content', '')
            if content is None:
                content = ''

            normalized.append({
                'role': role,
                'content': str(content)
            })

        return normalized

    def _truncate_text(self, text, max_chars):
        if not text:
            return ''
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n...[truncated]"

    def _optimize_messages_for_tokens(self, messages):
        if not messages:
            return []

        system_messages = [m for m in messages if m.get('role') == 'system']
        non_system = [m for m in messages if m.get('role') != 'system']

        optimized = []

        if system_messages:
            system_content = "\n".join([m.get('content', '') for m in system_messages])
            optimized.append({
                'role': 'system',
                'content': self._truncate_text(system_content, self.max_system_prompt_chars)
            })

        recent_non_system = non_system[-self.max_context_messages:] if self.max_context_messages > 0 else non_system
        per_message_limit = max(200, self.max_input_chars // max(1, len(recent_non_system)))

        for msg in recent_non_system:
            optimized.append({
                'role': msg.get('role', 'user'),
                'content': self._truncate_text(msg.get('content', ''), per_message_limit)
            })

        return optimized

    def _call_provider(self, provider, messages, max_tokens):
        if provider == 'openai':
            return self._call_openai(messages, max_tokens)
        if provider == 'mistral':
            return self._call_mistral(messages, max_tokens)
        if provider == 'claude':
            return self._call_claude(messages, max_tokens)
        if provider == 'gemini':
            return self._call_gemini(messages, max_tokens)

        raise ValueError(f"Unsupported provider: {provider}")

    def _call_openai(self, messages, max_tokens):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI chưa được cấu hình")

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": Config.OPENAI_MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.5
            },
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        return data['choices'][0]['message']['content']

    def _call_mistral(self, messages, max_tokens):
        if not Config.MISTRAL_API_KEY:
            raise ValueError("Mistral chưa được cấu hình")

        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {Config.MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": Config.MISTRAL_MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.4
            },
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        return data['choices'][0]['message']['content']

    def _call_claude(self, messages, max_tokens):
        if not Config.CLAUDE_API_KEY:
            raise ValueError("Claude chưa được cấu hình")

        system_prompt, provider_messages = self._split_system_message(messages)

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": Config.CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": Config.CLAUDE_MODEL,
                "system": system_prompt,
                "messages": provider_messages,
                "max_tokens": max_tokens,
                "temperature": 0.5
            },
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        content_parts = data.get('content', [])
        texts = [part.get('text', '') for part in content_parts if part.get('type') == 'text']
        return "\n".join([t for t in texts if t])

    def _call_gemini(self, messages, max_tokens):
        if not Config.GEMINI_API_KEY:
            raise ValueError("Gemini chưa được cấu hình")

        system_prompt, provider_messages = self._split_system_message(messages)

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{Config.GEMINI_MODEL}:generateContent?key={Config.GEMINI_API_KEY}"
        )

        payload = {
            "contents": self._convert_to_gemini_messages(provider_messages),
            "generationConfig": {
                "temperature": 0.5,
                "maxOutputTokens": max_tokens
            }
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        response = requests.post(
            endpoint,
            headers={"content-type": "application/json"},
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()
        candidates = data.get('candidates', [])
        if not candidates:
            raise ValueError("Gemini không trả về candidates")

        parts = candidates[0].get('content', {}).get('parts', [])
        texts = [part.get('text', '') for part in parts if part.get('text')]
        return "\n".join(texts)

    def _split_system_message(self, messages):
        system_parts = []
        converted = []

        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'system':
                system_parts.append(content)
            elif role in ['user', 'assistant']:
                converted.append({
                    "role": role,
                    "content": content
                })

        return "\n\n".join(system_parts), converted

    def _convert_to_gemini_messages(self, messages):
        converted = []
        for msg in messages:
            role = 'model' if msg.get('role') == 'assistant' else 'user'
            converted.append({
                "role": role,
                "parts": [{"text": msg.get('content', '')}]
            })
        return converted

    def get_provider_status(self):
        """Return provider configuration for UI/debug"""
        chain = self._build_provider_chain() if self.configured_providers else []
        missing_providers = [
            provider for provider in ['openai', 'mistral', 'claude', 'gemini']
            if provider not in self.configured_providers
        ]
        return {
            "primary_provider": self.primary_provider,
            "provider_order": self.provider_order,
            "configured_providers": self.configured_providers,
            "missing_providers": missing_providers,
            "active_chain": chain,
            "task_provider_overrides": self.task_provider_overrides,
            "task_chains": {
                "chat": self._build_provider_chain('chat') if self.configured_providers else [],
                "summary": self._build_provider_chain('summary') if self.configured_providers else [],
                "reply": self._build_provider_chain('reply') if self.configured_providers else [],
                "analyze": self._build_provider_chain('analyze') if self.configured_providers else []
            },
            "last_provider_used": self.last_provider_used,
            "provider_usage": self.provider_usage,
            "demo_mode": len(self.configured_providers) == 0,
            "expected_env": {
                "openai": ["OPENAI_API_KEY", "OPENAI_KEY"],
                "mistral": ["MISTRAL_API_KEY", "MISTRAL_KEY"],
                "claude": ["CLAUDE_API_KEY", "ANTHROPIC_API_KEY"],
                "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"]
            }
        }
    
    def _get_demo_response(self, messages):
        """Trả về demo response"""
        user_msg = messages[-1]["content"].lower() if messages else ""
        
        if "tóm tắt" in user_msg or "summary" in user_msg:
            return DEMO_RESPONSES["tóm tắt"]
        elif "lịch" in user_msg or "schedule" in user_msg:
            return DEMO_RESPONSES["lịch"]
        else:
            return DEMO_RESPONSES["default"]
    
    def summarize_email(self, email_content):
        """Summarize email content"""
        messages = [
            {
                "role": "system",
                "content": "Bạn là trợ lý giáo viên. Tóm tắt ngắn gọn email thành ý chính và 1-2 hành động."
            },
            {
                "role": "user",
                "content": f"Tóm tắt email sau:\n\n{self._truncate_text(email_content, self.max_input_chars)}"
            }
        ]
        return self.generate_response(messages, task='summary')
    
    def generate_reply(self, context, user_choice):
        """Generate automatic reply based on user choice"""
        messages = [
            {
                "role": "system",
                "content": "Bạn là trợ lý giáo viên. Viết email trả lời ngắn gọn, lịch sự, rõ ràng."
            },
            {
                "role": "user",
                "content": (
                    f"Bối cảnh: {self._truncate_text(context, self.max_input_chars)}\n\n"
                    f"Lựa chọn: {user_choice}\n\n"
                    "Viết email trả lời phù hợp."
                )
            }
        ]
        return self.generate_response(messages, task='reply')
    
    def analyze_text(self, text):
        """Analyze text for sentiment and intent"""
        messages = [
            {
                "role": "system",
                "content": "Phân tích ngắn: cảm xúc, ý định chính, hành động đề xuất."
            },
            {
                "role": "user",
                "content": f"Phân tích:\n\n{self._truncate_text(text, self.max_input_chars)}"
            }
        ]
        return self.generate_response(messages, task='analyze')

    def summarize_email_report(self, emails):
        """Summarize multiple emails in a single AI call for reporting."""
        if not emails:
            return []

        compact_items = []
        for idx, email in enumerate(emails, start=1):
            compact_text = self._truncate_text(
                f"Subject: {email.get('subject', '')}\n"
                f"Snippet: {email.get('snippet', '')}\n"
                f"Body: {email.get('body', '')}",
                420
            )
            compact_items.append(
                f"[{idx}] Sender: {email.get('sender', 'Unknown')}\n{compact_text}"
            )

        prompt = (
            "Tóm tắt từng email sau thành 1 câu ngắn. "
            "Trả về JSON array, mỗi phần tử gồm: index (số), summary (chuỗi)."
            " Không thêm giải thích ngoài JSON.\n\n"
            + "\n\n".join(compact_items)
        )

        max_tokens = min(700, max(220, len(emails) * 70))
        messages = [
            {
                "role": "system",
                "content": "Bạn là trợ lý giáo viên. Tóm tắt cực ngắn, rõ ý, đúng nội dung email."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            raw = self.generate_response(messages, max_tokens=max_tokens, task='summary')
            cleaned = raw.strip()
            if '```json' in cleaned:
                cleaned = cleaned.split('```json', 1)[1].split('```', 1)[0].strip()
            elif '```' in cleaned:
                cleaned = cleaned.split('```', 1)[1].split('```', 1)[0].strip()

            parsed = json.loads(cleaned)
            if not isinstance(parsed, list):
                raise ValueError("Invalid JSON structure")

            index_to_summary = {}
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                idx = item.get('index')
                summary = str(item.get('summary', '')).strip()
                if isinstance(idx, int) and summary:
                    index_to_summary[idx] = summary

            rows = []
            for idx, email in enumerate(emails, start=1):
                fallback_summary = self._truncate_text(email.get('snippet', '') or email.get('body', ''), 180)
                rows.append({
                    'sender': email.get('sender', 'Unknown'),
                    'summary': index_to_summary.get(idx, fallback_summary),
                    'subject': email.get('subject', ''),
                    'date': email.get('date', '')
                })
            return rows
        except Exception:
            rows = []
            for email in emails:
                fallback_summary = self._truncate_text(email.get('snippet', '') or email.get('body', ''), 180)
                rows.append({
                    'sender': email.get('sender', 'Unknown'),
                    'summary': fallback_summary,
                    'subject': email.get('subject', ''),
                    'date': email.get('date', '')
                })
            return rows
