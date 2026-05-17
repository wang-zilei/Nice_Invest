# 配置模板 — 复制为 config.py 后填入真实 Key
# config.py 已在 .gitignore 中，不会被提交

TUSHARE_TOKEN = "your_tushare_token_here"
OPENAI_API_KEY = "sk-..."
OPENAI_BASE_URL = "https://api.openai.com/v1"
DEEPSEEK_API_KEY = "sk-..."
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
QWEN_API_KEY = "sk-..."
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 默认模型（可选值: gpt-4o / deepseek-chat / qwen-plus）
DEFAULT_MODEL = "gpt-4o"

# ============================================================
# 邮箱验证码（Resend API）+ 体验 Key
# ============================================================
# Resend API Key（注册 https://resend.com 免费 100 封/天）
RESEND_API_KEY = "re_placeholder_..."

# 用户共享体验 Key（提供给没有自己 API Key 的用户体验用）
DEMO_API_KEY = "sk-..."
DEMO_BASE_URL = "https://api.deepseek.com"
DEMO_MODEL = "deepseek-chat"
DEMO_MAX_USES_PER_USER = 2
