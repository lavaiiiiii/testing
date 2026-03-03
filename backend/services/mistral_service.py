import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

class MistralService:
    """Service for Mistral AI API integration - Email classification"""
    
    def __init__(self):
        self.api_key = Config.MISTRAL_API_KEY
        self.model = Config.MISTRAL_MODEL
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        self.max_body_preview_chars = 280
        self.allowed_categories = [
            'education', 'work', 'meeting', 'promotion', 'finance', 'personal', 'other'
        ]
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def classify_email(self, subject, snippet, body_preview):
        """
        Classify email to check if it's related to education
        
        Args:
            subject: Email subject
            snippet: Email snippet
            body_preview: First 500 chars of email body
            
        Returns dict with category and compatibility fields.
        """
        try:
            prompt = f"""Classify if this email is education-related.
Return strict JSON with keys:
- category: one of {self.allowed_categories}
- confidence: number 0..1
- keywords: array of short keywords
- reason: short explanation

Subject: {subject}
Snippet: {snippet}
Body: {body_preview[:self.max_body_preview_chars]}"""

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.0,
                "max_tokens": 120
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse JSON response
                import json
                # Try to extract JSON from response
                try:
                    # Remove markdown code blocks if present
                    if '```json' in content:
                        content = content.split('```json')[1].split('```')[0].strip()
                    elif '```' in content:
                        content = content.split('```')[1].split('```')[0].strip()
                    
                    classification = json.loads(content)
                    return self._normalize_classification(classification)
                except json.JSONDecodeError:
                    return self._fallback_classification(subject, snippet, body_preview)
            else:
                # API error, use fallback
                return self._fallback_classification(subject, snippet, body_preview)
                
        except Exception as e:
            print(f"Mistral classification error: {str(e)}")
            return self._fallback_classification(subject, snippet, body_preview)
    
    def _fallback_classification(self, subject, snippet, body_preview):
        """Fallback keyword-based multi-category classification when API fails"""
        keyword_map = {
            'education': [
                'education', 'teaching', 'teacher', 'learning', 'student', 'class',
                'course', 'lesson', 'school', 'academic', 'training', 'assignment',
                'giảng dạy', 'giáo viên', 'học sinh', 'học', 'lớp', 'khóa học', 'bài giảng'
            ],
            'work': [
                'project', 'deadline', 'client', 'report', 'task', 'office', 'work',
                'công việc', 'dự án', 'báo cáo', 'nhiệm vụ'
            ],
            'meeting': [
                'meeting', 'calendar', 'zoom', 'teams', 'appointment', 'agenda',
                'họp', 'lịch họp', 'cuộc họp', 'thảo luận'
            ],
            'promotion': [
                'sale', 'discount', 'promotion', 'offer', 'deal', 'coupon', 'newsletter',
                'khuyến mãi', 'giảm giá', 'ưu đãi'
            ],
            'finance': [
                'invoice', 'payment', 'bank', 'receipt', 'tax', 'billing', 'transaction',
                'hóa đơn', 'thanh toán', 'ngân hàng', 'thuế'
            ],
            'personal': [
                'family', 'friend', 'birthday', 'party', 'trip', 'vacation',
                'gia đình', 'bạn bè', 'sinh nhật', 'du lịch'
            ]
        }

        text = f"{subject} {snippet} {body_preview}".lower()

        best_category = 'other'
        best_keywords = []
        best_score = 0

        for category, keywords in keyword_map.items():
            found = [kw for kw in keywords if kw in text]
            if len(found) > best_score:
                best_score = len(found)
                best_category = category
                best_keywords = found[:5]

        confidence = min(best_score * 0.15, 0.85) if best_score > 0 else 0.45

        return {
            'category': best_category,
            'is_education': best_category == 'education',
            'confidence': confidence,
            'keywords': best_keywords,
            'reason': 'Fallback keyword-based classification'
        }

    def _normalize_classification(self, classification):
        category = str(classification.get('category', 'other')).lower().strip()
        if category not in self.allowed_categories:
            category = 'other'

        keywords = classification.get('keywords', [])
        if not isinstance(keywords, list):
            keywords = []

        confidence = classification.get('confidence', 0.7)
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.7

        return {
            'category': category,
            'is_education': category == 'education',
            'confidence': max(0.0, min(1.0, confidence)),
            'keywords': [str(k) for k in keywords][:5],
            'reason': str(classification.get('reason', ''))[:200]
        }
    
    def batch_classify_emails(self, emails, filter_type='education'):
        """
        Classify multiple emails and filter education-related ones
        
        Args:
            emails: List of email dicts with 'subject', 'snippet', 'body'
            
        Returns:
            List of emails matching selected filter_type with classification info
        """
        classified_emails = []
        filter_type = (filter_type or 'education').lower().strip()
        
        for email in emails:
            classification = self.classify_email(
                email.get('subject', ''),
                email.get('snippet', ''),
                email.get('body', '')[:self.max_body_preview_chars]
            )

            match = False
            if filter_type == 'all':
                match = True
            elif filter_type == 'education':
                match = classification.get('is_education', False)
            else:
                match = classification.get('category') == filter_type

            if match:
                email_copy = dict(email)
                email_copy['classification'] = classification
                classified_emails.append(email_copy)
        
        return classified_emails
