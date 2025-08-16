# 第八章：生产环境部署与运维

## 本章概述

本章将深入探讨 SQLModel 应用在生产环境中的部署、配置、监控和运维最佳实践。我们将涵盖从开发环境到生产环境的完整部署流程，包括数据库配置优化、安全性设置、性能监控、故障排除和自动化运维等关键主题。

### 学习目标

通过本章学习，你将能够：
- 掌握生产环境数据库配置和优化技巧
- 实施全面的安全性措施和访问控制
- 建立完善的监控和告警体系
- 实现自动化部署和运维流程
- 处理常见的生产环境问题和故障
- 制定有效的备份和灾难恢复策略

---

## 1. 生产环境配置

### 1.1 数据库连接配置

```python
# production_config.py
from sqlmodel import SQLModel, create_engine
from sqlalchemy.pool import QueuePool
from sqlalchemy import event
from typing import Optional
import os
import logging
from urllib.parse import quote_plus

class ProductionDatabaseConfig:
    """生产环境数据库配置"""
    
    def __init__(self):
        self.database_url = self._build_database_url()
        self.engine = self._create_engine()
        self._setup_event_listeners()
    
    def _build_database_url(self) -> str:
        """构建数据库连接URL"""
        # 从环境变量获取数据库配置
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'production_db')
        db_user = os.getenv('DB_USER', 'app_user')
        db_password = os.getenv('DB_PASSWORD', '')
        
        # URL编码密码以处理特殊字符
        encoded_password = quote_plus(db_password)
        
        # 构建连接URL
        database_url = (
            f"postgresql://{db_user}:{encoded_password}"
            f"@{db_host}:{db_port}/{db_name}"
        )
        
        # 添加SSL配置
        ssl_mode = os.getenv('DB_SSL_MODE', 'require')
        if ssl_mode:
            database_url += f"?sslmode={ssl_mode}"
        
        return database_url
    
    def _create_engine(self):
        """创建数据库引擎"""
        return create_engine(
            self.database_url,
            # 连接池配置
            poolclass=QueuePool,
            pool_size=int(os.getenv('DB_POOL_SIZE', '20')),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '30')),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
            pool_recycle=int(os.getenv('DB_POOL_RECYCLE', '3600')),
            pool_pre_ping=True,  # 连接健康检查
            
            # 查询配置
            echo=False,  # 生产环境关闭SQL日志
            echo_pool=False,
            
            # 连接参数
            connect_args={
                "connect_timeout": 10,
                "command_timeout": 60,
                "server_settings": {
                    "application_name": os.getenv('APP_NAME', 'SQLModel_App'),
                    "timezone": "UTC"
                }
            }
        )
    
    def _setup_event_listeners(self):
        """设置事件监听器"""
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """连接时设置数据库参数"""
            if 'postgresql' in self.database_url:
                with dbapi_connection.cursor() as cursor:
                    # 设置查询超时
                    cursor.execute("SET statement_timeout = '60s'")
                    # 设置锁等待超时
                    cursor.execute("SET lock_timeout = '30s'")
                    # 设置空闲连接超时
                    cursor.execute("SET idle_in_transaction_session_timeout = '300s'")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """连接检出时的处理"""
            logging.debug(f"连接检出: {id(dbapi_connection)}")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """连接归还时的处理"""
            logging.debug(f"连接归还: {id(dbapi_connection)}")
    
    def get_engine(self):
        """获取数据库引擎"""
        return self.engine
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute("SELECT 1")
                return result.scalar() == 1
        except Exception as e:
            logging.error(f"数据库连接测试失败: {e}")
            return False
    
    def get_connection_info(self) -> dict:
        """获取连接信息"""
        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }

# 环境配置管理
class EnvironmentConfig:
    """环境配置管理"""
    
    def __init__(self, env: str = None):
        self.env = env or os.getenv('ENVIRONMENT', 'development')
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载环境配置"""
        base_config = {
            "DEBUG": False,
            "TESTING": False,
            "LOG_LEVEL": "INFO",
            "DB_POOL_SIZE": 20,
            "DB_MAX_OVERFLOW": 30,
            "CACHE_TTL": 3600,
            "RATE_LIMIT": 1000
        }
        
        env_configs = {
            "development": {
                "DEBUG": True,
                "LOG_LEVEL": "DEBUG",
                "DB_POOL_SIZE": 5,
                "DB_MAX_OVERFLOW": 10
            },
            "testing": {
                "TESTING": True,
                "LOG_LEVEL": "WARNING",
                "DB_POOL_SIZE": 2,
                "DB_MAX_OVERFLOW": 5
            },
            "staging": {
                "LOG_LEVEL": "INFO",
                "DB_POOL_SIZE": 10,
                "DB_MAX_OVERFLOW": 20
            },
            "production": {
                "LOG_LEVEL": "WARNING",
                "DB_POOL_SIZE": 20,
                "DB_MAX_OVERFLOW": 30
            }
        }
        
        config = base_config.copy()
        config.update(env_configs.get(self.env, {}))
        
        # 从环境变量覆盖配置
        for key, default_value in config.items():
            env_value = os.getenv(key)
            if env_value is not None:
                # 类型转换
                if isinstance(default_value, bool):
                    config[key] = env_value.lower() in ('true', '1', 'yes')
                elif isinstance(default_value, int):
                    config[key] = int(env_value)
                else:
                    config[key] = env_value
        
        return config
    
    def get(self, key: str, default=None):
        """获取配置值"""
        return self.config.get(key, default)
    
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.env == 'production'
    
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.env == 'development'

# 使用示例
def setup_production_database():
    """设置生产环境数据库"""
    # 加载环境配置
    env_config = EnvironmentConfig()
    
    # 设置日志级别
    logging.basicConfig(
        level=getattr(logging, env_config.get('LOG_LEVEL')),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建数据库配置
    db_config = ProductionDatabaseConfig()
    
    # 测试连接
    if db_config.test_connection():
        logging.info("数据库连接成功")
        logging.info(f"连接信息: {db_config.get_connection_info()}")
    else:
        logging.error("数据库连接失败")
        raise RuntimeError("无法连接到数据库")
    
    return db_config.get_engine()
```

### 1.2 安全配置

```python
# security_config.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import create_engine, event, text
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import hashlib
import secrets
import logging
import os
import jwt
from cryptography.fernet import Fernet

class SecurityConfig:
    """安全配置管理"""
    
    def __init__(self):
        self.secret_key = self._get_secret_key()
        self.jwt_secret = self._get_jwt_secret()
        self.encryption_key = self._get_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
    
    def _get_secret_key(self) -> str:
        """获取应用密钥"""
        secret_key = os.getenv('SECRET_KEY')
        if not secret_key:
            if os.getenv('ENVIRONMENT') == 'production':
                raise ValueError("生产环境必须设置 SECRET_KEY")
            secret_key = secrets.token_urlsafe(32)
            logging.warning("使用临时生成的密钥，请在生产环境中设置 SECRET_KEY")
        return secret_key
    
    def _get_jwt_secret(self) -> str:
        """获取JWT密钥"""
        jwt_secret = os.getenv('JWT_SECRET')
        if not jwt_secret:
            if os.getenv('ENVIRONMENT') == 'production':
                raise ValueError("生产环境必须设置 JWT_SECRET")
            jwt_secret = secrets.token_urlsafe(32)
        return jwt_secret
    
    def _get_encryption_key(self) -> bytes:
        """获取加密密钥"""
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            if os.getenv('ENVIRONMENT') == 'production':
                raise ValueError("生产环境必须设置 ENCRYPTION_KEY")
            encryption_key = Fernet.generate_key().decode()
        return encryption_key.encode()
    
    def encrypt_data(self, data: str) -> str:
        """加密数据"""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def generate_token(self, user_id: int, expires_in: int = 3600) -> str:
        """生成JWT令牌"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logging.warning("令牌已过期")
            return None
        except jwt.InvalidTokenError:
            logging.warning("无效令牌")
            return None

# 数据库安全模型
class AuditLog(SQLModel, table=True):
    """审计日志模型"""
    __tablename__ = "audit_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, index=True)
    action: str = Field(max_length=100, index=True)
    table_name: str = Field(max_length=100, index=True)
    record_id: Optional[str] = Field(default=None, index=True)
    old_values: Optional[str] = Field(default=None)  # JSON字符串
    new_values: Optional[str] = Field(default=None)  # JSON字符串
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
class SecurityEvent(SQLModel, table=True):
    """安全事件模型"""
    __tablename__ = "security_events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(max_length=50, index=True)  # login_failed, suspicious_activity, etc.
    severity: str = Field(max_length=20, index=True)  # low, medium, high, critical
    user_id: Optional[int] = Field(default=None, index=True)
    ip_address: Optional[str] = Field(default=None, max_length=45, index=True)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    details: Optional[str] = Field(default=None)  # JSON字符串
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    resolved: bool = Field(default=False, index=True)
    resolved_at: Optional[datetime] = Field(default=None)
    resolved_by: Optional[int] = Field(default=None)

class DatabaseSecurity:
    """数据库安全管理"""
    
    def __init__(self, engine, security_config: SecurityConfig):
        self.engine = engine
        self.security_config = security_config
        self._setup_audit_triggers()
    
    def _setup_audit_triggers(self):
        """设置审计触发器"""
        @event.listens_for(self.engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            # 记录查询开始时间
            context._query_start_time = datetime.utcnow()
            
            # 检查敏感操作
            sensitive_operations = ['DROP', 'DELETE', 'UPDATE', 'ALTER', 'TRUNCATE']
            statement_upper = statement.upper().strip()
            
            for operation in sensitive_operations:
                if statement_upper.startswith(operation):
                    logging.warning(f"敏感操作检测: {operation} - {statement[:100]}...")
                    break
        
        @event.listens_for(self.engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            # 计算执行时间
            if hasattr(context, '_query_start_time'):
                execution_time = (datetime.utcnow() - context._query_start_time).total_seconds()
                
                # 记录慢查询
                if execution_time > 5.0:  # 5秒以上的查询
                    logging.warning(f"慢查询检测: {execution_time:.3f}s - {statement[:100]}...")
    
    def log_audit_event(self, session: Session, user_id: Optional[int], 
                       action: str, table_name: str, record_id: Optional[str] = None,
                       old_values: Optional[dict] = None, new_values: Optional[dict] = None,
                       ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """记录审计事件"""
        import json
        
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        session.add(audit_log)
        session.commit()
    
    def log_security_event(self, session: Session, event_type: str, severity: str,
                          user_id: Optional[int] = None, ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None, details: Optional[dict] = None):
        """记录安全事件"""
        import json
        
        security_event = SecurityEvent(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=json.dumps(details) if details else None
        )
        
        session.add(security_event)
        session.commit()
        
        # 高严重性事件立即告警
        if severity in ['high', 'critical']:
            self._send_security_alert(security_event)
    
    def _send_security_alert(self, event: SecurityEvent):
        """发送安全告警"""
        # 这里可以集成邮件、短信、Slack等告警系统
        logging.critical(f"安全告警: {event.event_type} - 严重性: {event.severity}")
    
    def check_suspicious_activity(self, session: Session, user_id: int, 
                                 ip_address: str, time_window: int = 300) -> bool:
        """检查可疑活动"""
        # 检查短时间内的多次失败登录
        cutoff_time = datetime.utcnow() - timedelta(seconds=time_window)
        
        failed_attempts = session.exec(
            select(SecurityEvent)
            .where(SecurityEvent.event_type == 'login_failed')
            .where(SecurityEvent.user_id == user_id)
            .where(SecurityEvent.ip_address == ip_address)
            .where(SecurityEvent.timestamp > cutoff_time)
        ).all()
        
        if len(failed_attempts) >= 5:  # 5次失败登录
            self.log_security_event(
                session, 'suspicious_login_attempts', 'high',
                user_id=user_id, ip_address=ip_address,
                details={'failed_attempts': len(failed_attempts)}
            )
            return True
        
        return False
    
    def get_security_summary(self, session: Session, days: int = 7) -> Dict[str, Any]:
        """获取安全摘要"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # 统计安全事件
        events = session.exec(
            select(SecurityEvent)
            .where(SecurityEvent.timestamp > cutoff_time)
        ).all()
        
        event_summary = {}
        severity_summary = {}
        
        for event in events:
            event_summary[event.event_type] = event_summary.get(event.event_type, 0) + 1
            severity_summary[event.severity] = severity_summary.get(event.severity, 0) + 1
        
        return {
            "时间范围": f"最近 {days} 天",
            "总事件数": len(events),
            "事件类型统计": event_summary,
            "严重性统计": severity_summary,
            "未解决事件": len([e for e in events if not e.resolved])
        }

# 访问控制
class AccessControl:
    """访问控制管理"""
    
    def __init__(self, security_config: SecurityConfig):
        self.security_config = security_config
        self.rate_limits = {}  # IP -> (count, reset_time)
    
    def check_rate_limit(self, ip_address: str, limit: int = 100, 
                        window: int = 3600) -> bool:
        """检查速率限制"""
        now = datetime.utcnow()
        
        if ip_address in self.rate_limits:
            count, reset_time = self.rate_limits[ip_address]
            
            if now > reset_time:
                # 重置计数器
                self.rate_limits[ip_address] = (1, now + timedelta(seconds=window))
                return True
            elif count >= limit:
                return False
            else:
                self.rate_limits[ip_address] = (count + 1, reset_time)
                return True
        else:
            self.rate_limits[ip_address] = (1, now + timedelta(seconds=window))
            return True
    
    def validate_input(self, data: str, max_length: int = 1000) -> bool:
        """验证输入数据"""
        # 长度检查
        if len(data) > max_length:
            return False
        
        # SQL注入检查
        sql_patterns = [
            'union', 'select', 'insert', 'update', 'delete', 'drop',
            'exec', 'execute', 'sp_', 'xp_', '--', '/*', '*/', ';'
        ]
        
        data_lower = data.lower()
        for pattern in sql_patterns:
            if pattern in data_lower:
                logging.warning(f"可疑输入检测: {pattern} in {data[:50]}...")
                return False
        
        return True
    
    def sanitize_input(self, data: str) -> str:
        """清理输入数据"""
        # 移除危险字符
        dangerous_chars = ['<', '>', '"', "'", '&', ';']
        for char in dangerous_chars:
            data = data.replace(char, '')
        
        return data.strip()

# 使用示例
def setup_security():
    """设置安全配置"""
    # 创建安全配置
    security_config = SecurityConfig()
    
    # 创建数据库引擎
    engine = create_engine("postgresql://user:pass@localhost/db")
    
    # 设置数据库安全
    db_security = DatabaseSecurity(engine, security_config)
    
    # 设置访问控制
    access_control = AccessControl(security_config)
    
    return security_config, db_security, access_control
```

### 1.3 环境变量管理

```python
# environment_manager.py
from typing import Dict, Any, Optional, List
import os
import json
from pathlib import Path
import logging

class EnvironmentManager:
    """环境变量管理器"""
    
    def __init__(self, env_file: Optional[str] = None):
        self.env_file = env_file or '.env'
        self.required_vars = set()
        self.default_values = {}
        self.validators = {}
        self._load_env_file()
    
    def _load_env_file(self):
        """加载环境变量文件"""
        env_path = Path(self.env_file)
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        if key not in os.environ:
                            os.environ[key] = value
    
    def require(self, var_name: str, default: Any = None, 
               validator: Optional[callable] = None) -> 'EnvironmentManager':
        """标记必需的环境变量"""
        self.required_vars.add(var_name)
        if default is not None:
            self.default_values[var_name] = default
        if validator:
            self.validators[var_name] = validator
        return self
    
    def get(self, var_name: str, default: Any = None, 
           var_type: type = str) -> Any:
        """获取环境变量"""
        value = os.getenv(var_name)
        
        if value is None:
            if var_name in self.default_values:
                value = self.default_values[var_name]
            elif default is not None:
                value = default
            elif var_name in self.required_vars:
                raise ValueError(f"必需的环境变量 {var_name} 未设置")
            else:
                return None
        
        # 类型转换
        if var_type == bool:
            return str(value).lower() in ('true', '1', 'yes', 'on')
        elif var_type == int:
            return int(value)
        elif var_type == float:
            return float(value)
        elif var_type == list:
            return [item.strip() for item in str(value).split(',') if item.strip()]
        elif var_type == dict:
            return json.loads(value)
        else:
            return str(value)
    
    def validate(self) -> List[str]:
        """验证环境变量"""
        errors = []
        
        # 检查必需变量
        for var_name in self.required_vars:
            value = os.getenv(var_name)
            if value is None and var_name not in self.default_values:
                errors.append(f"缺少必需的环境变量: {var_name}")
            
            # 运行验证器
            if var_name in self.validators and value is not None:
                validator = self.validators[var_name]
                try:
                    if not validator(value):
                        errors.append(f"环境变量 {var_name} 验证失败")
                except Exception as e:
                    errors.append(f"环境变量 {var_name} 验证错误: {e}")
        
        return errors
    
    def get_config_dict(self, prefix: str = '') -> Dict[str, Any]:
        """获取配置字典"""
        config = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):] if prefix else key
                config[config_key] = value
        return config
    
    def export_template(self, file_path: str):
        """导出环境变量模板"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# 环境变量配置模板\n\n")
            
            for var_name in sorted(self.required_vars):
                default_value = self.default_values.get(var_name, '')
                f.write(f"# {var_name}\n")
                f.write(f"{var_name}={default_value}\n\n")

# 生产环境配置验证器
def validate_database_url(url: str) -> bool:
    """验证数据库URL"""
    return url.startswith(('postgresql://', 'mysql://', 'sqlite:///'))

def validate_port(port: str) -> bool:
    """验证端口号"""
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except ValueError:
        return False

def validate_log_level(level: str) -> bool:
    """验证日志级别"""
    return level.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

# 配置生产环境
def setup_production_environment():
    """设置生产环境配置"""
    env_manager = EnvironmentManager()
    
    # 配置必需的环境变量
    env_manager.require('DATABASE_URL', validator=validate_database_url)
    env_manager.require('SECRET_KEY')
    env_manager.require('JWT_SECRET')
    env_manager.require('ENCRYPTION_KEY')
    env_manager.require('ENVIRONMENT', default='production')
    env_manager.require('LOG_LEVEL', default='INFO', validator=validate_log_level)
    env_manager.require('PORT', default='8000', validator=validate_port)
    env_manager.require('DB_POOL_SIZE', default='20')
    env_manager.require('DB_MAX_OVERFLOW', default='30')
    env_manager.require('REDIS_URL', default='redis://localhost:6379')
    
    # 验证配置
    errors = env_manager.validate()
    if errors:
        for error in errors:
            logging.error(error)
        raise ValueError(f"环境配置验证失败: {errors}")
    
    # 返回配置
    return {
        'database_url': env_manager.get('DATABASE_URL'),
        'secret_key': env_manager.get('SECRET_KEY'),
        'jwt_secret': env_manager.get('JWT_SECRET'),
        'encryption_key': env_manager.get('ENCRYPTION_KEY'),
        'environment': env_manager.get('ENVIRONMENT'),
        'log_level': env_manager.get('LOG_LEVEL'),
        'port': env_manager.get('PORT', var_type=int),
        'db_pool_size': env_manager.get('DB_POOL_SIZE', var_type=int),
        'db_max_overflow': env_manager.get('DB_MAX_OVERFLOW', var_type=int),
        'redis_url': env_manager.get('REDIS_URL'),
        'debug': env_manager.get('DEBUG', default=False, var_type=bool),
        'allowed_hosts': env_manager.get('ALLOWED_HOSTS', default='*', var_type=list)
    }

# 使用示例
if __name__ == "__main__":
    try:
        config = setup_production_environment()
        print("生产环境配置加载成功:")
        for key, value in config.items():
            if 'secret' in key.lower() or 'key' in key.lower():
                print(f"{key}: {'*' * len(str(value))}")
            else:
                print(f"{key}: {value}")
    except Exception as e:
        logging.error(f"配置加载失败: {e}")
        exit(1)
```

---

## 2. 监控与告警

### 2.1 应用监控

```python
# application_monitoring.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import create_engine, event, text
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import time
import psutil
import threading
import logging
import json
from collections import defaultdict, deque
from dataclasses import dataclass

@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = None

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_points: int = 1000):
        self.metrics = defaultdict(lambda: deque(maxlen=max_points))
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self._lock = threading.Lock()
    
    def counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """计数器指标"""
        with self._lock:
            key = self._make_key(name, tags)
            self.counters[key] += value
            self.metrics[key].append(MetricPoint(datetime.utcnow(), self.counters[key], tags))
    
    def gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """仪表盘指标"""
        with self._lock:
            key = self._make_key(name, tags)
            self.gauges[key] = value
            self.metrics[key].append(MetricPoint(datetime.utcnow(), value, tags))
    
    def histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """直方图指标"""
        with self._lock:
            key = self._make_key(name, tags)
            self.histograms[key].append(value)
            self.metrics[key].append(MetricPoint(datetime.utcnow(), value, tags))
    
    def timer(self, name: str, tags: Dict[str, str] = None):
        """计时器装饰器"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    self.histogram(f"{name}.success", time.time() - start_time, tags)
                    return result
                except Exception as e:
                    self.histogram(f"{name}.error", time.time() - start_time, tags)
                    self.counter(f"{name}.error_count", 1, tags)
                    raise
            return wrapper
        return decorator
    
    def _make_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """生成指标键"""
        if tags:
            tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name}[{tag_str}]"
        return name
    
    def get_metrics(self, name_pattern: str = None, 
                   since: datetime = None) -> Dict[str, List[MetricPoint]]:
        """获取指标数据"""
        with self._lock:
            result = {}
            for key, points in self.metrics.items():
                if name_pattern and name_pattern not in key:
                    continue
                
                filtered_points = points
                if since:
                    filtered_points = [p for p in points if p.timestamp >= since]
                
                result[key] = list(filtered_points)
            
            return result
    
    def get_summary(self, name: str, tags: Dict[str, str] = None, 
                   window_minutes: int = 60) -> Dict[str, Any]:
        """获取指标摘要"""
        key = self._make_key(name, tags)
        since = datetime.utcnow() - timedelta(minutes=window_minutes)
        
        points = [p for p in self.metrics[key] if p.timestamp >= since]
        if not points:
            return {"message": "没有数据"}
        
        values = [p.value for p in points]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1] if values else None,
            "window_minutes": window_minutes
        }

class ApplicationMonitor:
    """应用监控器"""
    
    def __init__(self, engine, metrics_collector: MetricsCollector):
        self.engine = engine
        self.metrics = metrics_collector
        self.start_time = datetime.utcnow()
        self._setup_database_monitoring()
        self._setup_system_monitoring()
    
    def _setup_database_monitoring(self):
        """设置数据库监控"""
        @event.listens_for(self.engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
            self.metrics.counter("database.queries.total")
        
        @event.listens_for(self.engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if hasattr(context, '_query_start_time'):
                execution_time = time.time() - context._query_start_time
                self.metrics.histogram("database.query.duration", execution_time)
                
                # 慢查询监控
                if execution_time > 1.0:
                    self.metrics.counter("database.queries.slow")
                    logging.warning(f"慢查询: {execution_time:.3f}s - {statement[:100]}...")
        
        @event.listens_for(self.engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            self.metrics.counter("database.connections.checkout")
        
        @event.listens_for(self.engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            self.metrics.counter("database.connections.checkin")
    
    def _setup_system_monitoring(self):
        """设置系统监控"""
        def collect_system_metrics():
            while True:
                try:
                    # CPU使用率
                    cpu_percent = psutil.cpu_percent(interval=1)
                    self.metrics.gauge("system.cpu.usage", cpu_percent)
                    
                    # 内存使用
                    memory = psutil.virtual_memory()
                    self.metrics.gauge("system.memory.usage", memory.percent)
                    self.metrics.gauge("system.memory.available", memory.available)
                    
                    # 磁盘使用
                    disk = psutil.disk_usage('/')
                    self.metrics.gauge("system.disk.usage", disk.percent)
                    self.metrics.gauge("system.disk.free", disk.free)
                    
                    # 网络IO
                    net_io = psutil.net_io_counters()
                    self.metrics.gauge("system.network.bytes_sent", net_io.bytes_sent)
                    self.metrics.gauge("system.network.bytes_recv", net_io.bytes_recv)
                    
                    # 数据库连接池状态
                    if hasattr(self.engine, 'pool'):
                        pool = self.engine.pool
                        self.metrics.gauge("database.pool.size", pool.size())
                        self.metrics.gauge("database.pool.checked_in", pool.checkedin())
                        self.metrics.gauge("database.pool.checked_out", pool.checkedout())
                        self.metrics.gauge("database.pool.overflow", pool.overflow())
                    
                except Exception as e:
                    logging.error(f"系统指标收集错误: {e}")
                
                time.sleep(60)  # 每分钟收集一次
        
        # 启动后台线程
        thread = threading.Thread(target=collect_system_metrics, daemon=True)
        thread.start()
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        try:
            # 测试数据库连接
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "healthy"
        except Exception as e:
            db_status = f"unhealthy: {e}"
        
        # 获取系统指标
        cpu_usage = self.metrics.get_summary("system.cpu.usage", window_minutes=5)
        memory_usage = self.metrics.get_summary("system.memory.usage", window_minutes=5)
        
        # 计算运行时间
        uptime = datetime.utcnow() - self.start_time
        
        return {
            "status": "healthy" if db_status == "healthy" else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "database": db_status,
            "cpu_usage": cpu_usage.get("latest", 0),
            "memory_usage": memory_usage.get("latest", 0),
            "version": "1.0.0",  # 应用版本
            "environment": os.getenv("ENVIRONMENT", "unknown")
        }
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能报告"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # 数据库性能
        query_duration = self.metrics.get_summary("database.query.duration", window_minutes=hours*60)
        total_queries = self.metrics.get_summary("database.queries.total", window_minutes=hours*60)
        slow_queries = self.metrics.get_summary("database.queries.slow", window_minutes=hours*60)
        
        # 系统性能
        cpu_usage = self.metrics.get_summary("system.cpu.usage", window_minutes=hours*60)
        memory_usage = self.metrics.get_summary("system.memory.usage", window_minutes=hours*60)
        
        return {
            "时间范围": f"最近 {hours} 小时",
            "数据库性能": {
                "查询总数": total_queries.get("latest", 0),
                "慢查询数": slow_queries.get("latest", 0),
                "平均查询时间": f"{query_duration.get('avg', 0):.3f}s",
                "最大查询时间": f"{query_duration.get('max', 0):.3f}s"
            },
            "系统性能": {
                "平均CPU使用率": f"{cpu_usage.get('avg', 0):.1f}%",
                "最大CPU使用率": f"{cpu_usage.get('max', 0):.1f}%",
                "平均内存使用率": f"{memory_usage.get('avg', 0):.1f}%",
                "最大内存使用率": f"{memory_usage.get('max', 0):.1f}%"
            }
        }

# 告警系统
class AlertManager:
    """告警管理器"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.alert_rules = []
        self.alert_handlers = []
        self.alert_history = deque(maxlen=1000)
        self._setup_default_rules()
    
    def add_rule(self, name: str, metric_name: str, condition: str, 
                threshold: float, severity: str = "warning"):
        """添加告警规则"""
        rule = {
            "name": name,
            "metric_name": metric_name,
            "condition": condition,  # ">", "<", ">=", "<=", "=="
            "threshold": threshold,
            "severity": severity,
            "last_triggered": None
        }
        self.alert_rules.append(rule)
    
    def add_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    def _setup_default_rules(self):
        """设置默认告警规则"""
        self.add_rule("高CPU使用率", "system.cpu.usage", ">", 80, "warning")
        self.add_rule("极高CPU使用率", "system.cpu.usage", ">", 95, "critical")
        self.add_rule("高内存使用率", "system.memory.usage", ">", 85, "warning")
        self.add_rule("极高内存使用率", "system.memory.usage", ">", 95, "critical")
        self.add_rule("慢查询过多", "database.queries.slow", ">", 10, "warning")
        self.add_rule("磁盘空间不足", "system.disk.usage", ">", 90, "critical")
    
    def check_alerts(self):
        """检查告警条件"""
        for rule in self.alert_rules:
            try:
                summary = self.metrics.get_summary(rule["metric_name"], window_minutes=5)
                if summary.get("latest") is None:
                    continue
                
                current_value = summary["latest"]
                threshold = rule["threshold"]
                condition = rule["condition"]
                
                triggered = False
                if condition == ">" and current_value > threshold:
                    triggered = True
                elif condition == "<" and current_value < threshold:
                    triggered = True
                elif condition == ">=" and current_value >= threshold:
                    triggered = True
                elif condition == "<=" and current_value <= threshold:
                    triggered = True
                elif condition == "==" and current_value == threshold:
                    triggered = True
                
                if triggered:
                    # 避免重复告警（5分钟内）
                    now = datetime.utcnow()
                    if (rule["last_triggered"] is None or 
                        (now - rule["last_triggered"]).total_seconds() > 300):
                        
                        alert = {
                            "name": rule["name"],
                            "metric_name": rule["metric_name"],
                            "current_value": current_value,
                            "threshold": threshold,
                            "condition": condition,
                            "severity": rule["severity"],
                            "timestamp": now,
                            "message": f"{rule['name']}: {rule['metric_name']} {condition} {threshold} (当前值: {current_value})"
                        }
                        
                        self._trigger_alert(alert)
                        rule["last_triggered"] = now
            
            except Exception as e:
                logging.error(f"告警检查错误: {e}")
    
    def _trigger_alert(self, alert: Dict[str, Any]):
        """触发告警"""
        self.alert_history.append(alert)
        
        # 记录日志
        log_level = logging.CRITICAL if alert["severity"] == "critical" else logging.WARNING
        logging.log(log_level, alert["message"])
        
        # 调用告警处理器
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logging.error(f"告警处理器错误: {e}")
    
    def get_active_alerts(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return [alert for alert in self.alert_history if alert["timestamp"] > cutoff_time]
    
    def start_monitoring(self, interval: int = 60):
        """启动监控"""
        def monitor_loop():
            while True:
                try:
                    self.check_alerts()
                except Exception as e:
                    logging.error(f"监控循环错误: {e}")
                time.sleep(interval)
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        logging.info(f"告警监控已启动，检查间隔: {interval}秒")

# 告警处理器示例
def email_alert_handler(alert: Dict[str, Any]):
    """邮件告警处理器"""
    # 这里可以集成邮件发送功能
    print(f"📧 邮件告警: {alert['message']}")

def slack_alert_handler(alert: Dict[str, Any]):
    """Slack告警处理器"""
    # 这里可以集成Slack API
    print(f"💬 Slack告警: {alert['message']}")

def webhook_alert_handler(alert: Dict[str, Any]):
    """Webhook告警处理器"""
    # 这里可以发送HTTP请求到告警系统
    print(f"🔗 Webhook告警: {alert['message']}")

# 使用示例
def setup_monitoring():
    """设置监控系统"""
    # 创建指标收集器
    metrics = MetricsCollector()
    
    # 创建数据库引擎
    engine = create_engine("postgresql://user:pass@localhost/db")
    
    # 创建应用监控器
    app_monitor = ApplicationMonitor(engine, metrics)
    
    # 创建告警管理器
    alert_manager = AlertManager(metrics)
    
    # 添加告警处理器
    alert_manager.add_handler(email_alert_handler)
    alert_manager.add_handler(slack_alert_handler)
    
    # 启动告警监控
    alert_manager.start_monitoring()
    
    return app_monitor, alert_manager, metrics
```

### 2.2 日志管理

```python
# logging_config.py
import logging
import logging.handlers
from typing import Dict, Any, Optional
import json
import os
from datetime import datetime
from pathlib import Path
import gzip
import shutil

class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        # 基础日志信息
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # 添加自定义字段
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'ip_address'):
            log_entry["ip_address"] = record.ip_address
        if hasattr(record, 'extra_data'):
            log_entry["extra_data"] = record.extra_data
        
        return json.dumps(log_entry, ensure_ascii=False)

class DatabaseLogHandler(logging.Handler):
    """数据库日志处理器"""
    
    def __init__(self, engine, table_name: str = "application_logs"):
        super().__init__()
        self.engine = engine
        self.table_name = table_name
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """确保日志表存在"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            level VARCHAR(20) NOT NULL,
            logger VARCHAR(100) NOT NULL,
            message TEXT NOT NULL,
            module VARCHAR(100),
            function VARCHAR(100),
            line_number INTEGER,
            user_id INTEGER,
            request_id VARCHAR(100),
            ip_address INET,
            exception TEXT,
            extra_data JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_timestamp ON {self.table_name}(timestamp);
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_level ON {self.table_name}(level);
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_user_id ON {self.table_name}(user_id);
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_request_id ON {self.table_name}(request_id);
        """
        
        try:
            with self.engine.connect() as conn:
                conn.execute(create_table_sql)
                conn.commit()
        except Exception as e:
            print(f"创建日志表失败: {e}")
    
    def emit(self, record: logging.LogRecord):
        """发送日志记录到数据库"""
        try:
            # 准备数据
            data = {
                "timestamp": datetime.utcfromtimestamp(record.created),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line_number": record.lineno,
                "user_id": getattr(record, 'user_id', None),
                "request_id": getattr(record, 'request_id', None),
                "ip_address": getattr(record, 'ip_address', None),
                "exception": self.formatException(record.exc_info) if record.exc_info else None,
                "extra_data": getattr(record, 'extra_data', None)
            }
            
            # 插入数据库
            insert_sql = f"""
            INSERT INTO {self.table_name} 
            (timestamp, level, logger, message, module, function, line_number, 
             user_id, request_id, ip_address, exception, extra_data)
            VALUES (%(timestamp)s, %(level)s, %(logger)s, %(message)s, %(module)s, 
                   %(function)s, %(line_number)s, %(user_id)s, %(request_id)s, 
                   %(ip_address)s, %(exception)s, %(extra_data)s)
            """
            
            with self.engine.connect() as conn:
                conn.execute(insert_sql, data)
                conn.commit()
        
        except Exception as e:
            # 避免日志循环
            self.handleError(record)

class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """压缩轮转文件处理器"""
    
    def doRollover(self):
        """执行日志轮转并压缩旧文件"""
        if self.stream:
            self.stream.close()
            self.stream = None
        
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename("%s.%d.gz" % (self.baseFilename, i))
                dfn = self.rotation_filename("%s.%d.gz" % (self.baseFilename, i + 1))
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            
            # 压缩当前文件
            dfn = self.rotation_filename(self.baseFilename + ".1.gz")
            if os.path.exists(dfn):
                os.remove(dfn)
            
            with open(self.baseFilename, 'rb') as f_in:
                with gzip.open(dfn, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            os.remove(self.baseFilename)
        
        if not self.delay:
            self.stream = self._open()

class LoggingConfig:
    """日志配置管理"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.loggers = {}
    
    def setup_logging(self):
        """设置日志配置"""
        # 创建日志目录
        log_dir = Path(self.config.get('log_dir', 'logs'))
        log_dir.mkdir(exist_ok=True)
        
        # 根日志器配置
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        
        # 清除现有处理器
        root_logger.handlers.clear()
        
        # 控制台处理器
        if self.config.get('console', {}).get('enabled', True):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, self.config.get('console', {}).get('level', 'INFO')))
            
            if self.config.get('console', {}).get('structured', False):
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
            
            root_logger.addHandler(console_handler)
        
        # 文件处理器
        if self.config.get('file', {}).get('enabled', True):
            file_config = self.config.get('file', {})
            log_file = log_dir / file_config.get('filename', 'application.log')
            
            if file_config.get('rotate', True):
                file_handler = CompressedRotatingFileHandler(
                    log_file,
                    maxBytes=file_config.get('max_bytes', 10*1024*1024),  # 10MB
                    backupCount=file_config.get('backup_count', 5)
                )
            else:
                file_handler = logging.FileHandler(log_file)
            
            file_handler.setLevel(getattr(logging, file_config.get('level', 'INFO')))
            
            if file_config.get('structured', True):
                file_handler.setFormatter(StructuredFormatter())
            else:
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
            
            root_logger.addHandler(file_handler)
        
        # 数据库处理器
        if self.config.get('database', {}).get('enabled', False):
            from sqlalchemy import create_engine
            engine = create_engine(self.config['database']['url'])
            
            db_handler = DatabaseLogHandler(engine, self.config['database'].get('table', 'application_logs'))
            db_handler.setLevel(getattr(logging, self.config.get('database', {}).get('level', 'WARNING')))
            
            root_logger.addHandler(db_handler)
        
        # 错误文件处理器
        if self.config.get('error_file', {}).get('enabled', True):
            error_config = self.config.get('error_file', {})
            error_file = log_dir / error_config.get('filename', 'error.log')
            
            error_handler = CompressedRotatingFileHandler(
                error_file,
                maxBytes=error_config.get('max_bytes', 5*1024*1024),  # 5MB
                backupCount=error_config.get('backup_count', 10)
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(StructuredFormatter())
            
            root_logger.addHandler(error_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取指定名称的日志器"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        return self.loggers[name]
    
    def add_context(self, **kwargs) -> 'LogContext':
        """添加日志上下文"""
        return LogContext(**kwargs)

class LogContext:
    """日志上下文管理器"""
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)

# 日志分析工具
class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, engine):
        self.engine = engine
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误摘要"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = """
        SELECT 
            level,
            COUNT(*) as count,
            COUNT(DISTINCT user_id) as affected_users,
            array_agg(DISTINCT logger) as loggers
        FROM application_logs 
        WHERE timestamp > %s AND level IN ('ERROR', 'CRITICAL')
        GROUP BY level
        ORDER BY count DESC
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(query, (cutoff_time,))
            errors = result.fetchall()
        
        return {
            "时间范围": f"最近 {hours} 小时",
            "错误统计": [dict(row) for row in errors]
        }
    
    def get_top_errors(self, limit: int = 10, hours: int = 24) -> List[Dict[str, Any]]:
        """获取最频繁的错误"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = """
        SELECT 
            message,
            COUNT(*) as count,
            MAX(timestamp) as last_occurrence,
            array_agg(DISTINCT user_id) FILTER (WHERE user_id IS NOT NULL) as affected_users
        FROM application_logs 
        WHERE timestamp > %s AND level IN ('ERROR', 'CRITICAL')
        GROUP BY message
        ORDER BY count DESC
        LIMIT %s
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(query, (cutoff_time, limit))
            errors = result.fetchall()
        
        return [dict(row) for row in errors]
    
    def get_user_activity(self, user_id: int, hours: int = 24) -> List[Dict[str, Any]]:
        """获取用户活动日志"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = """
        SELECT timestamp, level, logger, message, ip_address
        FROM application_logs 
        WHERE user_id = %s AND timestamp > %s
        ORDER BY timestamp DESC
        LIMIT 100
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(query, (user_id, cutoff_time))
            logs = result.fetchall()
        
        return [dict(row) for row in logs]
    
    def cleanup_old_logs(self, days: int = 30) -> int:
        """清理旧日志"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        query = "DELETE FROM application_logs WHERE timestamp < %s"
        
        with self.engine.connect() as conn:
            result = conn.execute(query, (cutoff_time,))
            conn.commit()
            return result.rowcount

# 生产环境日志配置
def get_production_logging_config() -> Dict[str, Any]:
    """获取生产环境日志配置"""
    return {
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "log_dir": os.getenv("LOG_DIR", "/var/log/app"),
        "console": {
            "enabled": os.getenv("LOG_CONSOLE_ENABLED", "true").lower() == "true",
            "level": os.getenv("LOG_CONSOLE_LEVEL", "INFO"),
            "structured": os.getenv("LOG_CONSOLE_STRUCTURED", "false").lower() == "true"
        },
        "file": {
            "enabled": os.getenv("LOG_FILE_ENABLED", "true").lower() == "true",
            "filename": os.getenv("LOG_FILE_NAME", "application.log"),
            "level": os.getenv("LOG_FILE_LEVEL", "INFO"),
            "structured": os.getenv("LOG_FILE_STRUCTURED", "true").lower() == "true",
            "rotate": os.getenv("LOG_FILE_ROTATE", "true").lower() == "true",
            "max_bytes": int(os.getenv("LOG_FILE_MAX_BYTES", "10485760")),  # 10MB
            "backup_count": int(os.getenv("LOG_FILE_BACKUP_COUNT", "5"))
        },
        "error_file": {
            "enabled": os.getenv("LOG_ERROR_FILE_ENABLED", "true").lower() == "true",
            "filename": os.getenv("LOG_ERROR_FILE_NAME", "error.log"),
            "max_bytes": int(os.getenv("LOG_ERROR_FILE_MAX_BYTES", "5242880")),  # 5MB
            "backup_count": int(os.getenv("LOG_ERROR_FILE_BACKUP_COUNT", "10"))
        },
        "database": {
            "enabled": os.getenv("LOG_DB_ENABLED", "false").lower() == "true",
            "url": os.getenv("LOG_DB_URL", ""),
            "table": os.getenv("LOG_DB_TABLE", "application_logs"),
            "level": os.getenv("LOG_DB_LEVEL", "WARNING")
        }
    }

# 使用示例
def setup_production_logging():
    """设置生产环境日志"""
    config = get_production_logging_config()
    logging_config = LoggingConfig(config)
    logging_config.setup_logging()
    
    # 获取应用日志器
    app_logger = logging_config.get_logger("app")
    db_logger = logging_config.get_logger("database")
    security_logger = logging_config.get_logger("security")
    
    return app_logger, db_logger, security_logger

# 日志使用示例
def example_logging_usage():
    """日志使用示例"""
    app_logger, db_logger, security_logger = setup_production_logging()
    
    # 基础日志
    app_logger.info("应用启动")
    
    # 带上下文的日志
    with LogContext(user_id=123, request_id="req-456", ip_address="192.168.1.1"):
        app_logger.info("用户登录成功")
        db_logger.debug("执行查询: SELECT * FROM users")
        security_logger.warning("检测到可疑活动")
    
    # 错误日志
    try:
        raise ValueError("示例错误")
    except Exception as e:
        app_logger.error("处理请求时发生错误", exc_info=True, extra={
             'extra_data': {'error_code': 'E001', 'user_action': 'login'}
         })
```

## 4. 备份与恢复

### 4.1 数据库备份策略

```python
import subprocess
import boto3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import tarfile
import gzip
import shutil

class DatabaseBackupManager:
    """数据库备份管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backup_dir = Path(config.get('backup_dir', '/var/backups/db'))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # S3 配置（可选）
        if config.get('s3_enabled', False):
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=config['s3_access_key'],
                aws_secret_access_key=config['s3_secret_key'],
                region_name=config.get('s3_region', 'us-east-1')
            )
            self.s3_bucket = config['s3_bucket']
        else:
            self.s3_client = None
    
    def create_backup(self, backup_type: str = 'full') -> Dict[str, Any]:
        """创建数据库备份"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{self.config['database_name']}_{backup_type}_{timestamp}"
        backup_file = self.backup_dir / f"{backup_name}.sql"
        compressed_file = self.backup_dir / f"{backup_name}.sql.gz"
        
        try:
            # 执行 pg_dump
            cmd = [
                'pg_dump',
                '-h', self.config['host'],
                '-p', str(self.config['port']),
                '-U', self.config['username'],
                '-d', self.config['database_name'],
                '--no-password',
                '--verbose',
                '--clean',
                '--if-exists',
                '--create',
                '-f', str(backup_file)
            ]
            
            # 设置环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = self.config['password']
            
            # 执行备份
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode != 0:
                raise Exception(f"备份失败: {result.stderr}")
            
            # 压缩备份文件
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 删除未压缩文件
            backup_file.unlink()
            
            # 获取文件信息
            file_size = compressed_file.stat().st_size
            
            backup_info = {
                'name': backup_name,
                'file_path': str(compressed_file),
                'size_bytes': file_size,
                'size_mb': round(file_size / 1024 / 1024, 2),
                'timestamp': timestamp,
                'type': backup_type,
                'status': 'completed'
            }
            
            # 上传到 S3（如果配置了）
            if self.s3_client:
                s3_key = f"database-backups/{backup_name}.sql.gz"
                self.s3_client.upload_file(
                    str(compressed_file),
                    self.s3_bucket,
                    s3_key
                )
                backup_info['s3_key'] = s3_key
                backup_info['s3_bucket'] = self.s3_bucket
            
            return backup_info
            
        except Exception as e:
            return {
                'name': backup_name,
                'status': 'failed',
                'error': str(e),
                'timestamp': timestamp
            }
    
    def restore_backup(self, backup_file: str, target_db: Optional[str] = None) -> Dict[str, Any]:
        """恢复数据库备份"""
        if target_db is None:
            target_db = self.config['database_name']
        
        backup_path = Path(backup_file)
        if not backup_path.exists():
            # 尝试从 S3 下载
            if self.s3_client and backup_file.startswith('s3://'):
                s3_key = backup_file.replace(f's3://{self.s3_bucket}/', '')
                local_file = self.backup_dir / Path(s3_key).name
                self.s3_client.download_file(self.s3_bucket, s3_key, str(local_file))
                backup_path = local_file
            else:
                raise FileNotFoundError(f"备份文件不存在: {backup_file}")
        
        try:
            # 解压文件（如果需要）
            if backup_path.suffix == '.gz':
                decompressed_file = backup_path.with_suffix('')
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(decompressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                sql_file = decompressed_file
            else:
                sql_file = backup_path
            
            # 执行恢复
            cmd = [
                'psql',
                '-h', self.config['host'],
                '-p', str(self.config['port']),
                '-U', self.config['username'],
                '-d', target_db,
                '-f', str(sql_file)
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.config['password']
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode != 0:
                raise Exception(f"恢复失败: {result.stderr}")
            
            # 清理临时文件
            if backup_path.suffix == '.gz' and sql_file.exists():
                sql_file.unlink()
            
            return {
                'status': 'success',
                'target_database': target_db,
                'backup_file': str(backup_path),
                'restored_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'target_database': target_db,
                'backup_file': str(backup_path)
            }
    
    def list_backups(self, include_s3: bool = True) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        
        # 本地备份
        for backup_file in self.backup_dir.glob('*.sql.gz'):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.stem.replace('.sql', ''),
                'file_path': str(backup_file),
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / 1024 / 1024, 2),
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'location': 'local'
            })
        
        # S3 备份
        if include_s3 and self.s3_client:
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix='database-backups/'
                )
                
                for obj in response.get('Contents', []):
                    backups.append({
                        'name': Path(obj['Key']).stem.replace('.sql', ''),
                        's3_key': obj['Key'],
                        'size_bytes': obj['Size'],
                        'size_mb': round(obj['Size'] / 1024 / 1024, 2),
                        'created_at': obj['LastModified'].isoformat(),
                        'location': 's3'
                    })
            except Exception as e:
                print(f"获取 S3 备份列表失败: {e}")
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    
    def cleanup_old_backups(self, keep_days: int = 30, keep_count: int = 10) -> Dict[str, Any]:
        """清理旧备份"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        deleted_local = 0
        deleted_s3 = 0
        
        # 清理本地备份
        local_backups = []
        for backup_file in self.backup_dir.glob('*.sql.gz'):
            stat = backup_file.stat()
            created_at = datetime.fromtimestamp(stat.st_ctime)
            local_backups.append((backup_file, created_at))
        
        # 按时间排序，保留最新的
        local_backups.sort(key=lambda x: x[1], reverse=True)
        
        for i, (backup_file, created_at) in enumerate(local_backups):
            if i >= keep_count or created_at < cutoff_date:
                backup_file.unlink()
                deleted_local += 1
        
        # 清理 S3 备份
        if self.s3_client:
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix='database-backups/'
                )
                
                s3_backups = []
                for obj in response.get('Contents', []):
                    s3_backups.append((obj['Key'], obj['LastModified']))
                
                s3_backups.sort(key=lambda x: x[1], reverse=True)
                
                for i, (key, last_modified) in enumerate(s3_backups):
                    if i >= keep_count or last_modified.replace(tzinfo=None) < cutoff_date:
                        self.s3_client.delete_object(Bucket=self.s3_bucket, Key=key)
                        deleted_s3 += 1
                        
            except Exception as e:
                print(f"清理 S3 备份失败: {e}")
        
        return {
            'deleted_local': deleted_local,
            'deleted_s3': deleted_s3,
            'cutoff_date': cutoff_date.isoformat(),
            'keep_count': keep_count
        }

class BackupScheduler:
    """备份调度器"""
    
    def __init__(self, backup_manager: DatabaseBackupManager):
        self.backup_manager = backup_manager
        self.schedules = []
    
    def add_schedule(self, schedule_type: str, frequency: str, backup_type: str = 'full'):
        """添加备份计划"""
        self.schedules.append({
            'type': schedule_type,
            'frequency': frequency,
            'backup_type': backup_type,
            'last_run': None
        })
    
    def should_run_backup(self, schedule: Dict[str, Any]) -> bool:
        """检查是否应该运行备份"""
        if schedule['last_run'] is None:
            return True
        
        last_run = datetime.fromisoformat(schedule['last_run'])
        now = datetime.now()
        
        if schedule['frequency'] == 'daily':
            return (now - last_run).days >= 1
        elif schedule['frequency'] == 'weekly':
            return (now - last_run).days >= 7
        elif schedule['frequency'] == 'monthly':
            return (now - last_run).days >= 30
        
        return False
    
    def run_scheduled_backups(self) -> List[Dict[str, Any]]:
        """运行计划的备份"""
        results = []
        
        for schedule in self.schedules:
            if self.should_run_backup(schedule):
                result = self.backup_manager.create_backup(schedule['backup_type'])
                result['schedule_type'] = schedule['type']
                result['frequency'] = schedule['frequency']
                
                if result['status'] == 'completed':
                    schedule['last_run'] = datetime.now().isoformat()
                
                results.append(result)
        
        return results

# 备份配置示例
def get_backup_config() -> Dict[str, Any]:
    """获取备份配置"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'username': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database_name': os.getenv('DB_NAME', 'myapp'),
        'backup_dir': os.getenv('BACKUP_DIR', '/var/backups/db'),
        's3_enabled': os.getenv('S3_BACKUP_ENABLED', 'false').lower() == 'true',
        's3_access_key': os.getenv('S3_ACCESS_KEY', ''),
        's3_secret_key': os.getenv('S3_SECRET_KEY', ''),
        's3_bucket': os.getenv('S3_BACKUP_BUCKET', ''),
        's3_region': os.getenv('S3_REGION', 'us-east-1')
    }

# 使用示例
def setup_backup_system():
    """设置备份系统"""
    config = get_backup_config()
    backup_manager = DatabaseBackupManager(config)
    scheduler = BackupScheduler(backup_manager)
    
    # 添加备份计划
    scheduler.add_schedule('daily', 'daily', 'full')
    scheduler.add_schedule('weekly', 'weekly', 'full')
    
    return backup_manager, scheduler
```

### 4.2 应用状态备份

```python
class ApplicationStateBackup:
    """应用状态备份"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backup_dir = Path(config.get('state_backup_dir', '/var/backups/app'))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def backup_configuration(self) -> Dict[str, Any]:
        """备份配置文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"config_backup_{timestamp}"
        backup_file = self.backup_dir / f"{backup_name}.tar.gz"
        
        try:
            with tarfile.open(backup_file, 'w:gz') as tar:
                # 备份配置目录
                config_dirs = self.config.get('config_dirs', ['/etc/myapp', '/opt/myapp/config'])
                for config_dir in config_dirs:
                    if Path(config_dir).exists():
                        tar.add(config_dir, arcname=Path(config_dir).name)
                
                # 备份环境变量文件
                env_files = self.config.get('env_files', ['.env', '.env.production'])
                for env_file in env_files:
                    if Path(env_file).exists():
                        tar.add(env_file)
            
            return {
                'status': 'success',
                'backup_file': str(backup_file),
                'size_bytes': backup_file.stat().st_size,
                'timestamp': timestamp
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': timestamp
            }
    
    def backup_logs(self, days: int = 7) -> Dict[str, Any]:
        """备份日志文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"logs_backup_{timestamp}"
        backup_file = self.backup_dir / f"{backup_name}.tar.gz"
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with tarfile.open(backup_file, 'w:gz') as tar:
                log_dirs = self.config.get('log_dirs', ['/var/log/myapp', 'logs'])
                
                for log_dir in log_dirs:
                    log_path = Path(log_dir)
                    if log_path.exists():
                        for log_file in log_path.rglob('*.log*'):
                            if log_file.is_file():
                                stat = log_file.stat()
                                modified_time = datetime.fromtimestamp(stat.st_mtime)
                                
                                if modified_time >= cutoff_date:
                                    tar.add(log_file, arcname=f"logs/{log_file.name}")
            
            return {
                'status': 'success',
                'backup_file': str(backup_file),
                'size_bytes': backup_file.stat().st_size,
                'days_included': days,
                'timestamp': timestamp
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': timestamp
            }
    
    def create_full_backup(self) -> Dict[str, Any]:
        """创建完整应用备份"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"full_app_backup_{timestamp}"
        backup_file = self.backup_dir / f"{backup_name}.tar.gz"
        
        try:
            with tarfile.open(backup_file, 'w:gz') as tar:
                # 应用代码
                app_dirs = self.config.get('app_dirs', ['/opt/myapp'])
                for app_dir in app_dirs:
                    if Path(app_dir).exists():
                        tar.add(app_dir, arcname=f"app/{Path(app_dir).name}")
                
                # 配置文件
                config_dirs = self.config.get('config_dirs', [])
                for config_dir in config_dirs:
                    if Path(config_dir).exists():
                        tar.add(config_dir, arcname=f"config/{Path(config_dir).name}")
                
                # 数据目录
                data_dirs = self.config.get('data_dirs', [])
                for data_dir in data_dirs:
                    if Path(data_dir).exists():
                        tar.add(data_dir, arcname=f"data/{Path(data_dir).name}")
            
            return {
                'status': 'success',
                'backup_file': str(backup_file),
                'size_bytes': backup_file.stat().st_size,
                'size_mb': round(backup_file.stat().st_size / 1024 / 1024, 2),
                'timestamp': timestamp
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': timestamp
             }
```

## 5. 容器化部署

### 5.1 Docker 配置

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 设置权限
RUN chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/myapp
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - app-network

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    networks:
      - app-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

### 5.2 Kubernetes 部署

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: myapp
---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: myapp
data:
  LOG_LEVEL: "INFO"
  REDIS_URL: "redis://redis-service:6379"
  DATABASE_HOST: "postgres-service"
  DATABASE_PORT: "5432"
  DATABASE_NAME: "myapp"
---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: myapp
type: Opaque
data:
  DATABASE_PASSWORD: cGFzc3dvcmQ=  # base64 encoded 'password'
  SECRET_KEY: c2VjcmV0a2V5  # base64 encoded 'secretkey'
---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
  namespace: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          value: "postgresql://postgres:$(DATABASE_PASSWORD)@$(DATABASE_HOST):$(DATABASE_PORT)/$(DATABASE_NAME)"
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: app-service
  namespace: myapp
spec:
  selector:
    app: myapp
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: myapp
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - myapp.example.com
    secretName: app-tls
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app-service
            port:
              number: 80
```

### 5.3 容器化最佳实践

```python
class ContainerHealthCheck:
    """容器健康检查"""
    
    def __init__(self, engine):
        self.engine = engine
        self.start_time = datetime.now()
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查端点"""
        checks = {
            'database': await self._check_database(),
            'redis': await self._check_redis(),
            'disk_space': self._check_disk_space(),
            'memory': self._check_memory()
        }
        
        all_healthy = all(check['status'] == 'healthy' for check in checks.values())
        
        return {
            'status': 'healthy' if all_healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
            'checks': checks
        }
    
    async def _check_database(self) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return {'status': 'healthy', 'message': 'Database connection OK'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': f'Database error: {str(e)}'}
    
    async def _check_redis(self) -> Dict[str, Any]:
        """检查 Redis 连接"""
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
            await redis_client.ping()
            await redis_client.close()
            return {'status': 'healthy', 'message': 'Redis connection OK'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': f'Redis error: {str(e)}'}
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """检查磁盘空间"""
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            free_percent = (free / total) * 100
            
            if free_percent < 10:
                status = 'unhealthy'
                message = f'Low disk space: {free_percent:.1f}% free'
            elif free_percent < 20:
                status = 'warning'
                message = f'Disk space warning: {free_percent:.1f}% free'
            else:
                status = 'healthy'
                message = f'Disk space OK: {free_percent:.1f}% free'
            
            return {
                'status': status,
                'message': message,
                'free_percent': round(free_percent, 1),
                'free_gb': round(free / (1024**3), 2)
            }
        except Exception as e:
            return {'status': 'unhealthy', 'message': f'Disk check error: {str(e)}'}
    
    def _check_memory(self) -> Dict[str, Any]:
        """检查内存使用"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            if memory.percent > 90:
                status = 'unhealthy'
                message = f'High memory usage: {memory.percent:.1f}%'
            elif memory.percent > 80:
                status = 'warning'
                message = f'Memory usage warning: {memory.percent:.1f}%'
            else:
                status = 'healthy'
                message = f'Memory usage OK: {memory.percent:.1f}%'
            
            return {
                'status': status,
                'message': message,
                'used_percent': round(memory.percent, 1),
                'available_gb': round(memory.available / (1024**3), 2)
            }
        except Exception as e:
            return {'status': 'unhealthy', 'message': f'Memory check error: {str(e)}'}

class GracefulShutdown:
    """优雅关闭处理"""
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.tasks = set()
        self.cleanup_functions = []
    
    def add_cleanup_function(self, func):
        """添加清理函数"""
        self.cleanup_functions.append(func)
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"收到信号 {signum}，开始优雅关闭...")
        self.shutdown_event.set()
    
    async def wait_for_shutdown(self):
        """等待关闭信号"""
        await self.shutdown_event.wait()
        
        print("开始清理资源...")
        
        # 停止接受新任务
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # 等待现有任务完成
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # 执行清理函数
        for cleanup_func in self.cleanup_functions:
            try:
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func()
                else:
                    cleanup_func()
            except Exception as e:
                print(f"清理函数执行失败: {e}")
        
        print("优雅关闭完成")

# FastAPI 应用集成
from fastapi import FastAPI
import signal

def create_production_app() -> FastAPI:
    """创建生产环境应用"""
    app = FastAPI(
        title="MyApp",
        description="生产环境应用",
        version="1.0.0",
        docs_url=None if os.getenv('ENVIRONMENT') == 'production' else '/docs',
        redoc_url=None if os.getenv('ENVIRONMENT') == 'production' else '/redoc'
    )
    
    # 健康检查
    health_checker = ContainerHealthCheck(engine)
    
    @app.get('/health')
    async def health():
        return await health_checker.health_check()
    
    @app.get('/ready')
    async def ready():
        # 简单的就绪检查
        return {'status': 'ready', 'timestamp': datetime.now().isoformat()}
    
    # 优雅关闭
    shutdown_handler = GracefulShutdown()
    
    @app.on_event('startup')
    async def startup():
        # 注册信号处理器
        signal.signal(signal.SIGTERM, shutdown_handler.signal_handler)
        signal.signal(signal.SIGINT, shutdown_handler.signal_handler)
        
        # 添加清理函数
        shutdown_handler.add_cleanup_function(lambda: engine.dispose())
    
    @app.on_event('shutdown')
    async def shutdown():
        await shutdown_handler.wait_for_shutdown()
    
    return app
```

## 6. 负载均衡与高可用

### 6.1 Nginx 负载均衡配置

```nginx
# nginx.conf
upstream app_servers {
    least_conn;
    server app1:8000 max_fails=3 fail_timeout=30s;
    server app2:8000 max_fails=3 fail_timeout=30s;
    server app3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name myapp.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name myapp.example.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # 限流
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # 健康检查
    location /health {
        access_log off;
        proxy_pass http://app_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API 路由
    location /api/ {
        proxy_pass http://app_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # 缓冲设置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # 静态文件
    location /static/ {
        alias /var/www/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 默认路由
    location / {
        proxy_pass http://app_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6.2 数据库高可用

```python
class DatabaseClusterManager:
    """数据库集群管理"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.primary_engine = None
        self.replica_engines = []
        self.current_replica_index = 0
        self.setup_connections()
    
    def setup_connections(self):
        """设置数据库连接"""
        # 主库连接
        primary_url = self.config['primary_url']
        self.primary_engine = create_async_engine(
            primary_url,
            pool_size=self.config.get('pool_size', 20),
            max_overflow=self.config.get('max_overflow', 30),
            pool_timeout=self.config.get('pool_timeout', 30),
            pool_recycle=self.config.get('pool_recycle', 3600)
        )
        
        # 从库连接
        for replica_url in self.config.get('replica_urls', []):
            replica_engine = create_async_engine(
                replica_url,
                pool_size=self.config.get('replica_pool_size', 10),
                max_overflow=self.config.get('replica_max_overflow', 20)
            )
            self.replica_engines.append(replica_engine)
    
    def get_write_engine(self):
        """获取写入引擎（主库）"""
        return self.primary_engine
    
    def get_read_engine(self):
        """获取读取引擎（从库轮询）"""
        if not self.replica_engines:
            return self.primary_engine
        
        engine = self.replica_engines[self.current_replica_index]
        self.current_replica_index = (self.current_replica_index + 1) % len(self.replica_engines)
        return engine
    
    async def health_check(self) -> Dict[str, Any]:
        """集群健康检查"""
        results = {
            'primary': await self._check_engine_health(self.primary_engine, 'primary'),
            'replicas': []
        }
        
        for i, engine in enumerate(self.replica_engines):
            replica_health = await self._check_engine_health(engine, f'replica_{i}')
            results['replicas'].append(replica_health)
        
        return results
    
    async def _check_engine_health(self, engine, name: str) -> Dict[str, Any]:
        """检查单个引擎健康状态"""
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()
            
            return {
                'name': name,
                'status': 'healthy',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'name': name,
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

class ReadWriteSession:
    """读写分离会话"""
    
    def __init__(self, cluster_manager: DatabaseClusterManager):
        self.cluster_manager = cluster_manager
        self._write_session = None
        self._read_session = None
    
    async def get_write_session(self):
        """获取写入会话"""
        if self._write_session is None:
            engine = self.cluster_manager.get_write_engine()
            self._write_session = async_sessionmaker(engine, expire_on_commit=False)
        return self._write_session()
    
    async def get_read_session(self):
        """获取读取会话"""
        if self._read_session is None:
            engine = self.cluster_manager.get_read_engine()
            self._read_session = async_sessionmaker(engine, expire_on_commit=False)
        return self._read_session()
    
    async def close(self):
        """关闭会话"""
        if self._write_session:
            await self._write_session.close()
        if self._read_session:
            await self._read_session.close()

# 使用示例
class UserService:
    """用户服务（读写分离示例）"""
    
    def __init__(self, cluster_manager: DatabaseClusterManager):
        self.cluster_manager = cluster_manager
    
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """创建用户（写操作）"""
        session_manager = ReadWriteSession(self.cluster_manager)
        async with await session_manager.get_write_session() as session:
            user = User(**user_data)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """获取用户（读操作）"""
        session_manager = ReadWriteSession(self.cluster_manager)
        async with await session_manager.get_read_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """列出用户（读操作）"""
        session_manager = ReadWriteSession(self.cluster_manager)
        async with await session_manager.get_read_session() as session:
            result = await session.execute(
                select(User).limit(limit).offset(offset)
            )
            return result.scalars().all()
```

### 6.3 故障转移与自动恢复

```python
class FailoverManager:
    """故障转移管理器"""
    
    def __init__(self, cluster_manager: DatabaseClusterManager):
        self.cluster_manager = cluster_manager
        self.circuit_breaker = CircuitBreaker()
        self.health_check_interval = 30  # 秒
        self.failover_threshold = 3  # 连续失败次数
        self.recovery_check_interval = 60  # 秒
        self.failed_engines = set()
        self.monitoring_task = None
    
    async def start_monitoring(self):
        """开始监控"""
        self.monitoring_task = asyncio.create_task(self._monitor_health())
    
    async def stop_monitoring(self):
        """停止监控"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_health(self):
        """监控健康状态"""
        while True:
            try:
                await self._check_all_engines()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查失败: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _check_all_engines(self):
        """检查所有引擎"""
        # 检查主库
        primary_healthy = await self._check_engine_health(
            self.cluster_manager.primary_engine, 'primary'
        )
        
        if not primary_healthy:
            await self._handle_primary_failure()
        
        # 检查从库
        for i, engine in enumerate(self.cluster_manager.replica_engines):
            replica_healthy = await self._check_engine_health(engine, f'replica_{i}')
            if not replica_healthy:
                await self._handle_replica_failure(engine, i)
    
    async def _check_engine_health(self, engine, name: str) -> bool:
        """检查引擎健康状态"""
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning(f"引擎 {name} 健康检查失败: {e}")
            return False
    
    async def _handle_primary_failure(self):
        """处理主库故障"""
        logger.error("主库故障，尝试故障转移")
        
        # 选择最健康的从库作为新主库
        best_replica = await self._select_best_replica()
        if best_replica:
            await self._promote_replica_to_primary(best_replica)
        else:
            logger.critical("没有可用的从库进行故障转移")
            # 发送紧急告警
            await self._send_critical_alert("数据库完全不可用")
    
    async def _handle_replica_failure(self, engine, index: int):
        """处理从库故障"""
        logger.warning(f"从库 {index} 故障，从负载均衡中移除")
        self.failed_engines.add(engine)
        
        # 从集群中临时移除故障从库
        if engine in self.cluster_manager.replica_engines:
            self.cluster_manager.replica_engines.remove(engine)
    
    async def _select_best_replica(self):
        """选择最佳从库"""
        best_replica = None
        best_lag = float('inf')
        
        for engine in self.cluster_manager.replica_engines:
            try:
                lag = await self._get_replication_lag(engine)
                if lag < best_lag:
                    best_lag = lag
                    best_replica = engine
            except Exception as e:
                logger.warning(f"无法获取从库延迟: {e}")
        
        return best_replica
    
    async def _get_replication_lag(self, engine) -> float:
        """获取复制延迟"""
        async with engine.begin() as conn:
            result = await conn.execute(text(
                "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))"
            ))
            lag = result.scalar()
            return lag if lag is not None else 0.0
    
    async def _promote_replica_to_primary(self, replica_engine):
        """提升从库为主库"""
        try:
            # 这里需要根据具体的数据库集群方案实现
            # 例如：PostgreSQL 的 pg_promote()
            async with replica_engine.begin() as conn:
                await conn.execute(text("SELECT pg_promote()"))
            
            # 更新集群配置
            old_primary = self.cluster_manager.primary_engine
            self.cluster_manager.primary_engine = replica_engine
            self.cluster_manager.replica_engines.remove(replica_engine)
            
            logger.info("故障转移完成，新主库已启用")
            
            # 发送故障转移通知
            await self._send_failover_notification()
            
        except Exception as e:
            logger.error(f"故障转移失败: {e}")
            await self._send_critical_alert(f"故障转移失败: {e}")
    
    async def _send_failover_notification(self):
        """发送故障转移通知"""
        # 实现告警通知逻辑
        pass
    
    async def _send_critical_alert(self, message: str):
        """发送紧急告警"""
        # 实现紧急告警逻辑
        pass

class CircuitBreaker:
    """熔断器"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        """通过熔断器调用函数"""
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
            else:
                raise Exception("熔断器开启，拒绝请求")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
```

## 7. 自动扩缩容

### 7.1 水平扩缩容

```python
class AutoScaler:
    """自动扩缩容管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_replicas = config.get('min_replicas', 2)
        self.max_replicas = config.get('max_replicas', 10)
        self.target_cpu_utilization = config.get('target_cpu_utilization', 70)
        self.target_memory_utilization = config.get('target_memory_utilization', 80)
        self.scale_up_threshold = config.get('scale_up_threshold', 80)
        self.scale_down_threshold = config.get('scale_down_threshold', 30)
        self.cooldown_period = config.get('cooldown_period', 300)  # 5分钟
        self.last_scale_time = 0
        self.metrics_collector = MetricsCollector()
    
    async def start_autoscaling(self):
        """开始自动扩缩容"""
        while True:
            try:
                await self._check_and_scale()
                await asyncio.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"自动扩缩容检查失败: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_scale(self):
        """检查并执行扩缩容"""
        if not self._can_scale():
            return
        
        current_metrics = await self._get_current_metrics()
        current_replicas = await self._get_current_replicas()
        
        # 计算目标副本数
        target_replicas = self._calculate_target_replicas(
            current_metrics, current_replicas
        )
        
        if target_replicas != current_replicas:
            await self._scale_to(target_replicas)
            self.last_scale_time = time.time()
    
    def _can_scale(self) -> bool:
        """检查是否可以扩缩容（冷却期检查）"""
        return time.time() - self.last_scale_time >= self.cooldown_period
    
    async def _get_current_metrics(self) -> Dict[str, float]:
        """获取当前指标"""
        return {
            'cpu_utilization': await self.metrics_collector.get_avg_cpu_utilization(),
            'memory_utilization': await self.metrics_collector.get_avg_memory_utilization(),
            'request_rate': await self.metrics_collector.get_request_rate(),
            'response_time': await self.metrics_collector.get_avg_response_time()
        }
    
    async def _get_current_replicas(self) -> int:
        """获取当前副本数"""
        # 这里需要根据部署平台实现
        # Kubernetes 示例
        try:
            import kubernetes
            v1 = kubernetes.client.AppsV1Api()
            deployment = v1.read_namespaced_deployment(
                name=self.config['deployment_name'],
                namespace=self.config['namespace']
            )
            return deployment.spec.replicas
        except Exception as e:
            logger.error(f"获取当前副本数失败: {e}")
            return self.min_replicas
    
    def _calculate_target_replicas(self, metrics: Dict[str, float], current_replicas: int) -> int:
        """计算目标副本数"""
        cpu_ratio = metrics['cpu_utilization'] / self.target_cpu_utilization
        memory_ratio = metrics['memory_utilization'] / self.target_memory_utilization
        
        # 使用最高的资源利用率来计算
        max_ratio = max(cpu_ratio, memory_ratio)
        
        target_replicas = int(current_replicas * max_ratio)
        
        # 应用最小和最大限制
        target_replicas = max(self.min_replicas, min(self.max_replicas, target_replicas))
        
        # 避免频繁的小幅调整
        if abs(target_replicas - current_replicas) == 1:
            if metrics['cpu_utilization'] < self.scale_down_threshold and \
               metrics['memory_utilization'] < self.scale_down_threshold:
                target_replicas = current_replicas - 1
            elif metrics['cpu_utilization'] > self.scale_up_threshold or \
                 metrics['memory_utilization'] > self.scale_up_threshold:
                target_replicas = current_replicas + 1
            else:
                target_replicas = current_replicas
        
        return target_replicas
    
    async def _scale_to(self, target_replicas: int):
        """扩缩容到目标副本数"""
        try:
            import kubernetes
            v1 = kubernetes.client.AppsV1Api()
            
            # 更新 Deployment
            body = {'spec': {'replicas': target_replicas}}
            v1.patch_namespaced_deployment(
                name=self.config['deployment_name'],
                namespace=self.config['namespace'],
                body=body
            )
            
            logger.info(f"扩缩容完成: 目标副本数 {target_replicas}")
            
            # 记录扩缩容事件
            await self._record_scaling_event(target_replicas)
            
        except Exception as e:
            logger.error(f"扩缩容失败: {e}")
    
    async def _record_scaling_event(self, target_replicas: int):
        """记录扩缩容事件"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'scaling',
            'target_replicas': target_replicas,
            'metrics': await self._get_current_metrics()
        }
        
        # 保存到数据库或发送到监控系统
        logger.info(f"扩缩容事件: {event}")

class ResourceOptimizer:
    """资源优化器"""
    
    def __init__(self):
        self.optimization_history = []
    
    async def optimize_resources(self) -> Dict[str, Any]:
        """优化资源配置"""
        recommendations = {
            'cpu': await self._optimize_cpu(),
            'memory': await self._optimize_memory(),
            'storage': await self._optimize_storage(),
            'network': await self._optimize_network()
        }
        
        return recommendations
    
    async def _optimize_cpu(self) -> Dict[str, Any]:
        """CPU 优化建议"""
        # 分析 CPU 使用模式
        cpu_metrics = await self._get_cpu_metrics()
        
        recommendations = []
        
        if cpu_metrics['avg_utilization'] < 30:
            recommendations.append({
                'type': 'reduce_cpu',
                'current': cpu_metrics['allocated'],
                'recommended': cpu_metrics['allocated'] * 0.8,
                'reason': 'CPU 利用率过低'
            })
        elif cpu_metrics['avg_utilization'] > 80:
            recommendations.append({
                'type': 'increase_cpu',
                'current': cpu_metrics['allocated'],
                'recommended': cpu_metrics['allocated'] * 1.2,
                'reason': 'CPU 利用率过高'
            })
        
        return {
            'current_metrics': cpu_metrics,
            'recommendations': recommendations
        }
    
    async def _optimize_memory(self) -> Dict[str, Any]:
        """内存优化建议"""
        memory_metrics = await self._get_memory_metrics()
        
        recommendations = []
        
        if memory_metrics['avg_utilization'] < 40:
            recommendations.append({
                'type': 'reduce_memory',
                'current': memory_metrics['allocated'],
                'recommended': memory_metrics['allocated'] * 0.8,
                'reason': '内存利用率过低'
            })
        elif memory_metrics['avg_utilization'] > 85:
            recommendations.append({
                'type': 'increase_memory',
                'current': memory_metrics['allocated'],
                'recommended': memory_metrics['allocated'] * 1.3,
                'reason': '内存利用率过高'
            })
        
        return {
            'current_metrics': memory_metrics,
            'recommendations': recommendations
        }
    
    async def _get_cpu_metrics(self) -> Dict[str, float]:
        """获取 CPU 指标"""
        # 实现 CPU 指标收集
        return {
            'avg_utilization': 45.0,
            'peak_utilization': 78.0,
            'allocated': 2.0  # CPU 核心数
        }
    
    async def _get_memory_metrics(self) -> Dict[str, float]:
        """获取内存指标"""
        # 实现内存指标收集
        return {
            'avg_utilization': 65.0,
            'peak_utilization': 89.0,
            'allocated': 4096  # MB
        }
    
    async def _optimize_storage(self) -> Dict[str, Any]:
        """存储优化建议"""
        return {'recommendations': []}
    
    async def _optimize_network(self) -> Dict[str, Any]:
        """网络优化建议"""
        return {'recommendations': []}
```

## 8. 最佳实践

### 8.1 部署最佳实践

```python
class DeploymentBestPractices:
    """部署最佳实践"""
    
    @staticmethod
    def get_deployment_checklist() -> List[Dict[str, Any]]:
        """获取部署检查清单"""
        return [
            {
                'category': '安全配置',
                'items': [
                    '所有敏感信息使用环境变量或密钥管理',
                    '启用 HTTPS 和 TLS 加密',
                    '配置防火墙和网络安全组',
                    '定期更新依赖包和基础镜像',
                    '实施最小权限原则'
                ]
            },
            {
                'category': '性能优化',
                'items': [
                    '配置适当的连接池大小',
                    '启用数据库查询缓存',
                    '实施 CDN 和静态资源缓存',
                    '优化数据库索引',
                    '配置负载均衡'
                ]
            },
            {
                'category': '监控告警',
                'items': [
                    '配置应用性能监控',
                    '设置关键指标告警',
                    '实施日志聚合和分析',
                    '配置健康检查端点',
                    '监控资源使用情况'
                ]
            },
            {
                'category': '可靠性',
                'items': [
                    '实施多副本部署',
                    '配置自动故障转移',
                    '定期备份数据',
                    '实施优雅关闭',
                    '配置熔断器和重试机制'
                ]
            }
        ]
    
    @staticmethod
    def validate_production_config(config: Dict[str, Any]) -> List[str]:
        """验证生产环境配置"""
        issues = []
        
        # 检查必需的环境变量
        required_vars = [
            'DATABASE_URL', 'SECRET_KEY', 'LOG_LEVEL'
        ]
        
        for var in required_vars:
            if not config.get(var):
                issues.append(f"缺少必需的环境变量: {var}")
        
        # 检查安全配置
        if config.get('DEBUG', False):
            issues.append("生产环境不应启用 DEBUG 模式")
        
        if not config.get('SECRET_KEY') or len(config.get('SECRET_KEY', '')) < 32:
            issues.append("SECRET_KEY 长度应至少为 32 个字符")
        
        # 检查数据库配置
        db_url = config.get('DATABASE_URL', '')
        if 'localhost' in db_url or '127.0.0.1' in db_url:
            issues.append("生产环境不应使用本地数据库")
        
        return issues
    
    @staticmethod
    def generate_deployment_script(config: Dict[str, Any]) -> str:
        """生成部署脚本"""
        script = f"""
#!/bin/bash
set -e

# 生产环境部署脚本
echo "开始部署到生产环境..."

# 1. 拉取最新代码
git pull origin main

# 2. 构建 Docker 镜像
docker build -t {config.get('app_name', 'myapp')}:latest .

# 3. 运行数据库迁移
docker run --rm \
  --env-file .env.production \
  {config.get('app_name', 'myapp')}:latest \
  alembic upgrade head

# 4. 滚动更新应用
docker-compose -f docker-compose.prod.yml up -d --no-deps app

# 5. 健康检查
echo "等待应用启动..."
sleep 30

if curl -f http://localhost:8000/health; then
    echo "部署成功！"
else
    echo "部署失败，回滚..."
    docker-compose -f docker-compose.prod.yml rollback
    exit 1
fi

echo "部署完成"
"""
        return script

class ProductionMonitoring:
    """生产环境监控"""
    
    def __init__(self):
        self.alerts = []
        self.metrics_history = []
    
    async def setup_monitoring(self):
        """设置监控"""
        # 设置关键指标监控
        await self._setup_application_monitoring()
        await self._setup_infrastructure_monitoring()
        await self._setup_business_monitoring()
    
    async def _setup_application_monitoring(self):
        """设置应用监控"""
        monitors = [
            {
                'name': 'response_time',
                'threshold': 1000,  # ms
                'description': 'API 响应时间监控'
            },
            {
                'name': 'error_rate',
                'threshold': 5,  # %
                'description': '错误率监控'
            },
            {
                'name': 'throughput',
                'threshold': 100,  # req/s
                'description': '吞吐量监控'
            }
        ]
        
        for monitor in monitors:
            await self._create_monitor(monitor)
    
    async def _setup_infrastructure_monitoring(self):
        """设置基础设施监控"""
        monitors = [
            {
                'name': 'cpu_utilization',
                'threshold': 80,  # %
                'description': 'CPU 使用率监控'
            },
            {
                'name': 'memory_utilization',
                'threshold': 85,  # %
                'description': '内存使用率监控'
            },
            {
                'name': 'disk_usage',
                'threshold': 90,  # %
                'description': '磁盘使用率监控'
            },
            {
                'name': 'database_connections',
                'threshold': 80,  # % of pool
                'description': '数据库连接数监控'
            }
        ]
        
        for monitor in monitors:
            await self._create_monitor(monitor)
    
    async def _setup_business_monitoring(self):
        """设置业务监控"""
        monitors = [
            {
                'name': 'user_registrations',
                'threshold': 10,  # per hour
                'description': '用户注册数监控'
            },
            {
                'name': 'transaction_volume',
                'threshold': 1000,  # per hour
                'description': '交易量监控'
            }
        ]
        
        for monitor in monitors:
            await self._create_monitor(monitor)
    
    async def _create_monitor(self, monitor_config: Dict[str, Any]):
        """创建监控器"""
        # 实现监控器创建逻辑
        logger.info(f"创建监控器: {monitor_config['name']}")
```

## 9. 本章总结

### 9.1 核心概念回顾

本章详细介绍了 SQLModel 应用在生产环境中的部署、配置、监控和运维最佳实践：

1. **生产环境配置**
   - 数据库连接池配置和优化
   - 安全配置和访问控制
   - 环境变量管理

2. **监控与告警**
   - 应用性能监控
   - 系统资源监控
   - 告警管理和通知

3. **日志管理**
   - 结构化日志记录
   - 日志轮转和压缩
   - 日志分析和查询

4. **备份与恢复**
   - 数据库备份策略
   - 应用状态备份
   - 灾难恢复计划

5. **容器化部署**
   - Docker 配置和优化
   - Kubernetes 部署
   - 健康检查和优雅关闭

6. **负载均衡与高可用**
   - Nginx 负载均衡配置
   - 数据库读写分离
   - 故障转移和自动恢复

7. **自动扩缩容**
   - 水平扩缩容策略
   - 资源优化建议
   - 性能调优

### 9.2 最佳实践总结

1. **安全第一**
   - 使用环境变量管理敏感信息
   - 实施最小权限原则
   - 定期更新依赖和安全补丁

2. **监控驱动**
   - 建立全面的监控体系
   - 设置合理的告警阈值
   - 定期审查和优化监控策略

3. **自动化运维**
   - 自动化部署流程
   - 自动化备份和恢复
   - 自动化扩缩容和故障处理

4. **性能优化**
   - 合理配置连接池
   - 实施缓存策略
   - 优化数据库查询

### 9.3 常见陷阱与避免方法

1. **配置管理陷阱**
   - ❌ 硬编码敏感信息
   - ✅ 使用环境变量和密钥管理

2. **监控盲区**
   - ❌ 只监控基础指标
   - ✅ 建立业务指标监控

3. **单点故障**
   - ❌ 单实例部署
   - ✅ 多副本和故障转移

4. **资源浪费**
   - ❌ 固定资源配置
   - ✅ 动态扩缩容和资源优化

### 9.4 实践检查清单

- [ ] 配置生产环境数据库连接
- [ ] 实施安全配置和访问控制
- [ ] 设置环境变量管理
- [ ] 配置应用监控和告警
- [ ] 实施日志管理策略
- [ ] 建立备份和恢复机制
- [ ] 容器化应用部署
- [ ] 配置负载均衡和高可用
- [ ] 实施自动扩缩容
- [ ] 建立运维最佳实践

### 9.5 下一步学习

1. **深入学习容器编排**
   - Kubernetes 高级特性
   - 服务网格（Service Mesh）
   - GitOps 部署策略

2. **云原生技术**
   - 微服务架构
   - 无服务器计算
   - 云原生数据库

3. **DevOps 实践**
   - CI/CD 流水线
   - 基础设施即代码
   - 混沌工程

### 9.6 扩展练习

1. **部署练习**
   - 在云平台部署完整的 SQLModel 应用
   - 配置多环境部署流程
   - 实施蓝绿部署策略

2. **监控练习**
   - 集成 Prometheus 和 Grafana
   - 配置自定义业务指标
   - 建立告警响应流程

3. **高可用练习**
   - 配置数据库主从复制
   - 实施应用故障转移
   - 进行灾难恢复演练

通过本章的学习，你已经掌握了 SQLModel 应用在生产环境中的完整部署和运维知识。这些实践将帮助你构建稳定、可靠、高性能的生产系统。