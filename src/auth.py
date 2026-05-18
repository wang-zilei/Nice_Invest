"""
auth.py — 邮箱验证码登录 + 会话管理 + 用户存储
使用 Resend API 发送验证码邮件，内存存储（面试项目，不做持久化）。
"""
import random
import time
import hashlib
import secrets

# Resend API 配置（从 config.py 读取）
try:
    from config import RESEND_API_KEY
except ImportError:
    RESEND_API_KEY = ""

RESEND_API_URL = "https://api.resend.com/emails"
SENDER_EMAIL = "Nice Invest <noreply@niceinvest.dev>"
CODE_EXPIRE_SECONDS = 300       # 验证码 5 分钟过期
SESSION_EXPIRE_SECONDS = 86400  # 会话 24 小时过期


def generate_code() -> str:
    """生成 6 位数字验证码"""
    return str(random.randint(100000, 999999))


def _generate_token() -> str:
    """生成随机 session token"""
    return secrets.token_hex(32)


def _hash_token(token: str) -> str:
    """对 token 做单向哈希用于存储"""
    return hashlib.sha256(token.encode()).hexdigest()


# ============================================================
# 邮件模板 — Nice Invest 品牌风格
# ============================================================
EMAIL_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f5f3ef;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f3ef;padding:40px 0;">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="background-color:#fffcf2;border-radius:12px;overflow:hidden;border:1px solid #e0dbd0;">

  <!-- Header -->
  <tr>
    <td style="background-color:#252422;padding:32px 36px;text-align:center;">
      <span style="font-family:Georgia,serif;font-size:22px;font-weight:700;font-style:italic;color:#fffcf2;letter-spacing:1px;">Nice Invest</span>
    </td>
  </tr>

  <!-- Body -->
  <tr>
    <td style="padding:36px 36px 24px 36px;">
      <p style="margin:0 0 12px 0;font-size:15px;color:#403d39;line-height:1.6;">
        您好，
      </p>
      <p style="margin:0 0 24px 0;font-size:15px;color:#403d39;line-height:1.6;">
        欢迎使用 Nice Invest 金融分析平台。您的邮箱验证码如下：
      </p>

      <!-- Code box -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
        <tr>
          <td align="center" style="padding:24px 20px;background-color:#faf7f0;border:1px solid #e0dbd0;border-radius:8px;">
            <span style="font-family:'Courier New',monospace;font-size:32px;font-weight:700;letter-spacing:10px;color:#252422;">{code}</span>
          </td>
        </tr>
      </table>

      <p style="margin:0 0 8px 0;font-size:13px;color:#8c8780;line-height:1.5;">
        验证码有效期为 <b>5 分钟</b>，请尽快使用。
      </p>
      <p style="margin:0 0 8px 0;font-size:13px;color:#8c8780;line-height:1.5;">
        如果不是您本人的操作，请忽略此邮件。
      </p>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="padding:20px 36px 28px 36px;border-top:1px solid #e0dbd0;">
      <p style="margin:0;font-size:11px;color:#b0a99e;text-align:center;line-height:1.6;">
        Nice Invest &mdash; 基于 LangGraph 的金融分析 Multi-Agent 系统
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def build_email_html(code: str) -> str:
    """生成包含验证码的 HTML 邮件内容"""
    return EMAIL_TEMPLATE.format(code=code)


async def send_verification_email(email: str, code: str) -> bool:
    """
    通过 Resend API 发送验证码邮件。
    返回 True 表示发送成功，False 表示 Resend 未配置或发送失败。
    """
    if not RESEND_API_KEY or RESEND_API_KEY.startswith("re_placeholder"):
        return False  # 未配置 Resend，降级为终端输出

    import aiohttp

    payload = {
        "from": SENDER_EMAIL,
        "to": [email],
        "subject": f"Nice Invest 邮箱验证码：{code}",
        "html": build_email_html(code),
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                RESEND_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (200, 201):
                    return True
                # 失败时返回 False，由调用方降级
                return False
    except Exception:
        return False


# ============================================================
# 内存存储
# ============================================================
class CodeStore:
    """验证码内存存储（5 分钟过期）"""
    def __init__(self):
        self._store: dict[str, tuple[str, float]] = {}  # email → (code, created_at)

    def set(self, email: str, code: str):
        self._store[email] = (code, time.time())
        # 清理过期
        self._cleanup()

    def verify(self, email: str, code: str) -> bool:
        self._cleanup()
        entry = self._store.get(email)
        if not entry:
            return False
        stored_code, _ = entry
        if stored_code != code:
            return False
        del self._store[email]  # 验证通过后删除
        return True

    def _cleanup(self):
        now = time.time()
        expired = [e for e, (_, t) in self._store.items() if now - t > CODE_EXPIRE_SECONDS]
        for e in expired:
            del self._store[e]


class SessionStore:
    """会话内存存储（24 小时过期）"""
    def __init__(self):
        self._store: dict[str, tuple[str, float]] = {}  # hashed_token → (email, created_at)

    def create(self, email: str) -> str:
        token = _generate_token()
        hashed = _hash_token(token)
        self._store[hashed] = (email, time.time())
        self._cleanup()
        return token

    def validate(self, token: str) -> str | None:
        """校验 session token，返回 email 或 None"""
        self._cleanup()
        hashed = _hash_token(token)
        entry = self._store.get(hashed)
        if not entry:
            return None
        return entry[0]

    def _cleanup(self):
        now = time.time()
        expired = [h for h, (_, t) in self._store.items() if now - t > SESSION_EXPIRE_SECONDS]
        for h in expired:
            del self._store[h]


class UserStore:
    """用户信息内存存储"""
    def __init__(self):
        self._store: dict[str, dict] = {}  # email → {created_at, last_login, ...}

    def get_or_create(self, email: str) -> dict:
        if email not in self._store:
            self._store[email] = {
                "email": email,
                "created_at": time.time(),
                "last_login": time.time(),
            }
        else:
            self._store[email]["last_login"] = time.time()
        return self._store[email]

    @property
    def total_users(self) -> int:
        return len(self._store)


# ============================================================
# 全局单例
# ============================================================
code_store = CodeStore()
session_store = SessionStore()
user_store = UserStore()
