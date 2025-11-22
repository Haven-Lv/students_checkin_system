from pydantic_settings import BaseSettings, SettingsConfigDict
import os 

class Settings(BaseSettings):
    # 数据库配置
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = 'localhost'
    DB_NAME: str = 'student_system_db'
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # 邮件配置
    SMTP_SERVER: str = 'smtp.qq.com'
    SMTP_PORT: int = 465
    SMTP_USER: str
    SMTP_PASSWORD: str
    # --- 2. 修改这里：使用绝对路径定位 .env 文件 ---
    model_config = SettingsConfigDict(
        # os.path.dirname(__file__) 是 app/ 目录
        # 再套一层 os.path.dirname 就是项目根目录
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()
