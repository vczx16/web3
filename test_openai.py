import os
import logging
import socket
import requests
from dotenv import load_dotenv
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    """检查环境配置"""
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API key',
    }
    
    missing_vars = []
    for var, name in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(name)
    
    if missing_vars:
        print("Missing required environment variables:")
        for var in missing_vars:
            print(f"- {var}")
        return False
    return True

def check_internet_connection():
    """检查互联网连接"""
    try:
        # 尝试连接到 OpenAI 的 API 域名
        socket.create_connection(("api.openai.com", 443), timeout=5)
        return True
    except OSError:
        return False

def check_api_access():
    """检查 API 访问"""
    try:
        api_key = os.getenv('OPENAI_API_KEY', '').strip()  # 清理 API key
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"API access check failed: {str(e)}")
        return False

def test_api():
    try:
        # 检查网络连接
        print("Checking internet connection...")
        if not check_internet_connection():
            print("Error: No internet connection")
            return
        print("Internet connection OK")
        

         # 检查环境变量
        api_key = os.getenv('OPENAI_API_KEY', '').strip()  # 清理 API key
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment variables")
            return
        print(f"API Key found: {api_key[:6]}...{api_key[-4:]}")
        
         # 检查 API 访问
        print("Checking API access...")
        if not check_api_access():
            print("Warning: Cannot access OpenAI API directly")
            print("API may be blocked or experiencing issues")
        else:
            print("API access OK")
        
        # 检查环境变量
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment variables")
            return
        print(f"API Key found: {api_key[:6]}...{api_key[-4:]}")
        
        # 初始化生成器
        from ai_card_generator.services.ai_service import AICardGenerator
        generator = AICardGenerator()
        
        if generator.validate_api_key():
            print("API key format is valid")
        
       # 测试连接
        print("Testing OpenAI API connection...")
        if generator.test_openai_connection():
            print("API connection successful!")
        else:
            print("API connection failed!")
            print("\nTroubleshooting tips:")
            print("1. Verify your API key is active and has sufficient credits")
            print("2. Check if OpenAI services are operational: https://status.openai.com")
            print("3. Try increasing the timeout in the client configuration")
            print("4. Check your network connection and firewall settings")
            
    except Exception as e:
        print(f"Unexpected Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api()