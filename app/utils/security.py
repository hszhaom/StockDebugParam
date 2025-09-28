"""
安全相关工具模块
提供配置验证、敏感信息检查等功能
"""
import os
import re
import secrets
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SecurityValidator:
    """安全验证器"""
    
    # 敏感信息模式
    SENSITIVE_PATTERNS = [
        r'client_secret["\s]*[:=]["\s]*[^"\s]+',
        r'api_key["\s]*[:=]["\s]*[^"\s]+',
        r'password["\s]*[:=]["\s]*[^"\s]+',
        r'secret["\s]*[:=]["\s]*[^"\s]+',
        r'token["\s]*[:=]["\s]*[^"\s]+',
        r'GOCSPX-[a-zA-Z0-9_-]+',
        r'ya29\.[a-zA-Z0-9_-]+',
        r'[0-9]+-[a-zA-Z0-9]+\.apps\.googleusercontent\.com',
    ]
    
    @classmethod
    def check_secret_key(cls) -> bool:
        """检查SECRET_KEY是否安全"""
        secret_key = os.environ.get('SECRET_KEY')
        
        if not secret_key:
            logger.warning("SECRET_KEY 未设置，使用随机生成的密钥")
            return False
        
        if secret_key in ['dev-secret-key', 'dev-secret-key-change-in-production']:
            logger.error("SECRET_KEY 使用了不安全的默认值")
            return False
        
        if len(secret_key) < 32:
            logger.error("SECRET_KEY 长度不足32字符")
            return False
        
        return True
    
    @classmethod
    def scan_sensitive_files(cls, directory: str = ".") -> List[Dict[str, Any]]:
        """扫描目录中的敏感信息"""
        issues = []
        directory_path = Path(directory)
        
        # 排除的目录和文件
        exclude_patterns = [
            "**/__pycache__/**",
            "**/.git/**",
            "**/node_modules/**",
            "**/*.pyc",
            "**/*.log",
            "**/env.example",
            "**/token.json.example",
            "**/*example*",
            "**/*template*",
        ]
        
        for file_path in directory_path.rglob("*"):
            if file_path.is_file():
                # 检查是否应该排除
                skip_file = False
                for pattern in exclude_patterns:
                    if file_path.match(pattern):
                        skip_file = True
                        break
                
                if skip_file:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    for pattern in cls.SENSITIVE_PATTERNS:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            issues.append({
                                "file": str(file_path),
                                "pattern": pattern,
                                "match": match.group(),
                                "line_number": content[:match.start()].count('\n') + 1
                            })
                            
                except Exception as e:
                    logger.debug(f"无法读取文件 {file_path}: {str(e)}")
        
        return issues
    
    @classmethod
    def validate_token_files(cls) -> List[Dict[str, Any]]:
        """验证token文件的安全性"""
        issues = []
        token_files = [
            "data/token.json",
            "data/token2.json",
        ]
        
        for token_file in token_files:
            if Path(token_file).exists():
                issues.append({
                    "type": "sensitive_file",
                    "file": token_file,
                    "message": "包含敏感的API认证信息"
                })
        
        return issues
    
    @classmethod
    def generate_secure_key(cls, length: int = 32) -> str:
        """生成安全的密钥"""
        return secrets.token_hex(length)
    
    @classmethod
    def validate_environment(cls) -> Dict[str, Any]:
        """验证环境配置的安全性"""
        results = {
            "secret_key_ok": cls.check_secret_key(),
            "sensitive_files": cls.scan_sensitive_files(),
            "token_files": cls.validate_token_files(),
            "recommendations": []
        }
        
        # 生成建议
        if not results["secret_key_ok"]:
            results["recommendations"].append(
                "设置安全的SECRET_KEY环境变量 (至少32字符)"
            )
        
        if results["sensitive_files"]:
            results["recommendations"].append(
                "检查并移除代码中的敏感信息"
            )
        
        if results["token_files"]:
            results["recommendations"].append(
                "将敏感的token文件添加到.gitignore并考虑使用环境变量"
            )
        
        return results


def run_security_check() -> None:
    """运行安全检查"""
    print("🔒 运行安全检查...")
    
    validator = SecurityValidator()
    results = validator.validate_environment()
    
    print(f"SECRET_KEY 安全: {'✅' if results['secret_key_ok'] else '❌'}")
    print(f"发现敏感文件: {len(results['sensitive_files'])} 个")
    print(f"发现token文件: {len(results['token_files'])} 个")
    
    if results["sensitive_files"]:
        print("\n⚠️  发现敏感信息:")
        for issue in results["sensitive_files"][:5]:  # 只显示前5个
            print(f"  {issue['file']}:{issue['line_number']} - {issue['pattern']}")
        
        if len(results["sensitive_files"]) > 5:
            print(f"  ... 还有 {len(results['sensitive_files']) - 5} 个问题")
    
    if results["token_files"]:
        print("\n⚠️  发现敏感文件:")
        for issue in results["token_files"]:
            print(f"  {issue['file']} - {issue['message']}")
    
    if results["recommendations"]:
        print("\n💡 建议:")
        for rec in results["recommendations"]:
            print(f"  • {rec}")
    
    if not any([results["sensitive_files"], results["token_files"]]) and results["secret_key_ok"]:
        print("\n✅ 未发现明显的安全问题")


if __name__ == "__main__":
    run_security_check()
