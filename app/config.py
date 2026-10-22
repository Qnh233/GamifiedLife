"""
Gamified Life-Agent Engine Configuration
"""
import os
from datetime import timedelta
from urllib.parse import quote_plus
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 兼容性处理：如果 .env 中使用的是 LITELLM_ 前缀，自动映射到 OPENAI_ 前缀以支持 LiteLLM 的 OpenAI 兼容模式
if os.environ.get('LITELLM_API_KEY') and not os.environ.get('OPENAI_API_KEY'):
    os.environ['OPENAI_API_KEY'] = os.environ.get('LITELLM_API_KEY')

if os.environ.get('LITELLM_BASE_URL') and not os.environ.get('OPENAI_API_BASE'):
    os.environ['OPENAI_API_BASE'] = os.environ.get('LITELLM_BASE_URL')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Application
    APP_NAME = "Gamified Life-Agent Engine"
    DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'
    
    # MySQL Database
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'password')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'gamified_life')
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"

    @property
    def sync_database_url(self) -> str:
        return self.SQLALCHEMY_DATABASE_URI

    @property
    def database_url(self) -> str:
        return self.SQLALCHEMY_DATABASE_URI.replace("mysql+pymysql", "mysql+aiomysql")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG
    
    # Redis
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    REDIS_USERNAME = os.environ.get('REDIS_USERNAME', '').strip()
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '').strip()
    REDIS_URL_OVERRIDE = os.environ.get('REDIS_URL', '').strip()
    # Checkpoint Redis 连接超时（秒）：避免 Redis 抖动时工作流无限阻塞。
    REDIS_SOCKET_CONNECT_TIMEOUT_SEC = float(
        os.environ.get('REDIS_SOCKET_CONNECT_TIMEOUT_SEC', 3.0)
    )
    # Checkpoint Redis 命令读写超时（秒）：超时后触发失败并由上层 fallback。
    REDIS_SOCKET_TIMEOUT_SEC = float(os.environ.get('REDIS_SOCKET_TIMEOUT_SEC', 3.0))
    
    @property
    def REDIS_URL(self) -> str:
        # 支持通过 REDIS_URL 一次性覆盖（含 TLS、密码、集群代理等场景）。
        if self.REDIS_URL_OVERRIDE:
            return self.REDIS_URL_OVERRIDE
        # 兼容无密码/仅密码/用户名+密码三种常见连接方式。
        if self.REDIS_USERNAME and self.REDIS_PASSWORD:
            auth = f"{quote_plus(self.REDIS_USERNAME)}:{quote_plus(self.REDIS_PASSWORD)}@"
        elif self.REDIS_PASSWORD:
            auth = f":{quote_plus(self.REDIS_PASSWORD)}@"
        else:
            auth = ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # LLM Configuration (LiteLLM)
    DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'gpt-4')
    FALLBACK_MODELS = os.environ.get('FALLBACK_MODELS', 'gpt-3.5-turbo,claude-3-opus').split(',')
    LLM_MAX_RETRIES = int(os.environ.get('LLM_MAX_RETRIES', 3))
    LLM_RETRY_BASE_DELAY_SEC = float(os.environ.get('LLM_RETRY_BASE_DELAY_SEC', 1.0))
    LLM_RETRY_MAX_DELAY_SEC = float(os.environ.get('LLM_RETRY_MAX_DELAY_SEC', 8.0))
    LITELLM_API_KEY = os.environ.get('LITELLM_API_KEY')
    LITELLM_BASE_URL = os.environ.get('LITELLM_BASE_URL')
    
    # MCP Configuration
    MCP_SERVER_HOST = os.environ.get('MCP_SERVER_HOST', 'localhost')
    MCP_SERVER_PORT = int(os.environ.get('MCP_SERVER_PORT', 8001))
    MCP_CIRCUIT_FAIL_THRESHOLD = int(os.environ.get('MCP_CIRCUIT_FAIL_THRESHOLD', 3))
    MCP_CIRCUIT_RESET_TIMEOUT_SEC = int(os.environ.get('MCP_CIRCUIT_RESET_TIMEOUT_SEC', 30))
    # 外部 MCP 服务 JSON，供 MultiServerMCPClient 统一接入多个远端服务
    # 例如：{"remote_docs":{"transport":"streamable_http","url":"http://localhost:9000/mcp"}}
    MCP_EXTERNAL_SERVERS_JSON = os.environ.get('MCP_EXTERNAL_SERVERS_JSON', '')

    # Database and workflow resilience
    DB_MAX_RETRIES = int(os.environ.get('DB_MAX_RETRIES', 3))
    DB_RETRY_BASE_DELAY_SEC = float(os.environ.get('DB_RETRY_BASE_DELAY_SEC', 1.0))
    AGENT_WORKFLOW_TIMEOUT_SEC = int(os.environ.get('AGENT_WORKFLOW_TIMEOUT_SEC', 60))
    
    # Flask Configuration
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    # 开发模式热重载：保存代码会重启进程，进行中的长请求（如 LLM）会被打断，前端常表现为 ERROR。
    # Windows 上 watchdog 重载还易出现 serve_forever / WinError 10038；本地联调长请求建议 false。
    _default_flask_use_reloader = "false" if os.name == "nt" else "true"
    FLASK_USE_RELOADER = (
        os.environ.get("FLASK_USE_RELOADER", _default_flask_use_reloader).lower() == "true"
    )

    # Session Configuration
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get('SESSION_LIFETIME_HOURS', 24)))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'

    # 反向代理信任配置（Nginx/Ingress 场景）
    PROXY_FIX_X_FOR = int(os.environ.get('PROXY_FIX_X_FOR', 1))
    PROXY_FIX_X_PROTO = int(os.environ.get('PROXY_FIX_X_PROTO', 1))
    PROXY_FIX_X_HOST = int(os.environ.get('PROXY_FIX_X_HOST', 1))
    PROXY_FIX_X_PORT = int(os.environ.get('PROXY_FIX_X_PORT', 1))
    PROXY_FIX_X_PREFIX = int(os.environ.get('PROXY_FIX_X_PREFIX', 0))

    # Game Mechanics
    BASE_XP_PER_TASK = int(os.environ.get('BASE_XP_PER_TASK', 100))
    DIFFICULTY_MULTIPLIER = {
        "easy": 1.0,
        "medium": 1.5,
        "hard": 2.0,
        "epic": 3.0
    }
    DROP_RATE_BASE = float(os.environ.get('DROP_RATE_BASE', 0.1))


config = Config()
