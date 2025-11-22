from pydantic_settings import BaseSettings
from pydantic import ConfigDict  # 导入 V2 配置类

class Settings(BaseSettings):
    # 数据库配置
    DB_USER: str = 'student_system_user'
    DB_PASSWORD: str = '201303103670@Dxsg'  # 替换为您的密码
    DB_HOST: str = 'localhost'
    DB_NAME: str = 'student_system_db'
    
    # JWT (用于管理员登录)
    JWT_SECRET_KEY: str = '4b7e2f9d3a8b1c5d6e7f9a2b3c4d5e6f'  # 替换为一个随机长字符串
    JWT_ALGORITHM: str = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 天

    # --- 新增：邮件 SMTP 配置 ---
    # 以 QQ 邮箱为例
    SMTP_SERVER: str = 'smtp.qq.com'
    SMTP_PORT: int = 465 # SSL 端口
    SMTP_USER: str = '2412748011@qq.com'      # 发送方邮箱
    SMTP_PASSWORD: str = 'vkxcjnuxlacxdjha'   # 注意：是授权码，不是密码！
    
    model_config = ConfigDict(case_sensitive=True)
settings = Settings()