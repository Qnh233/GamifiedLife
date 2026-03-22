"""
Gamified Life-Agent Engine Configuration
"""
import os
from typing import Optional
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
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # LLM Configuration (LiteLLM)
    DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'gpt-4')
    FALLBACK_MODELS = os.environ.get('FALLBACK_MODELS', 'gpt-3.5-turbo,claude-3-opus').split(',')
    LITELLM_API_KEY = os.environ.get('LITELLM_API_KEY')
    LITELLM_BASE_URL = os.environ.get('LITELLM_BASE_URL')
    
    # MCP Configuration
    MCP_SERVER_HOST = os.environ.get('MCP_SERVER_HOST', 'localhost')
    MCP_SERVER_PORT = int(os.environ.get('MCP_SERVER_PORT', 8001))
    
    # Flask Configuration
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
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
