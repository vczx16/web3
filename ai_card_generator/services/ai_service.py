import random
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import requests
from io import BytesIO
import os
from datetime import datetime
import logging
import base64
from pathlib import Path
import json
import openai  # 新增导入
from openai import OpenAI  # 新增导入
from dotenv import load_dotenv
load_dotenv()
import time
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout
import httpx
from openai import OpenAI
import backoff  # 需要安装：pip install backoff
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import socket
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import os
import base64
from io import BytesIO
import textwrap    
logger = logging.getLogger(__name__)

class AICardGenerator:
    def __init__(self):
     
         # 初始化重试配置
        self.max_retries = 3
        self.retry_delay = 2

        # 初始化卡片尺寸（标准 TCG 卡片比例）
        self.card_width = 748    # 2.5 inches at 300 DPI
        self.card_height = 1024  # 3.5 inches at 300 DPI
        
        # 添加资源路径初始化（移到最前面）
        self.resources_dir = Path(__file__).parent / 'resources'
        self.resources_dir.mkdir(exist_ok=True)

        # 初始化字体
        self.title_font_size = 160      # 标题更大
        self.stats_font_size = 140      # 攻击防御更大
        self.rarity_font_size = 120     # 稀有度更大
        self.type_font_size = 110       # 属性更大

        # 初始化提示词模板（移到最前面）
        self.style_prompts = {
            'C': {
                'prompt': "trading card game style, pokemon card layout, creature character, full art, centered composition, clean background, basic effect",
                'weight': 0.60
            },
            'R': {
                'prompt': "trading card game style, pokemon card layout, magical creature, dynamic pose, full art, fantasy background, holographic effect",
                'weight': 0.30
            },
            'SR': {
                'prompt': "trading card game style, pokemon card layout, mythical creature, epic pose, full art, cosmic background, premium effect, glowing aura",
                'weight': 0.08
            },
            'SSR': {
                'prompt': "trading card game style, pokemon card layout, legendary creature, majestic pose, full art, divine background, ultimate effect, celestial aura",
                'weight': 0.02
            }
        }

        # 从 style_prompts 提取权重
        self.rarity_weights = {
            rarity: data['weight'] 
            for rarity, data in self.style_prompts.items()
        }

       # 更新稀有度样式定义
        self.rarity_styles = {
        'C': {
            'color': (128, 128, 128),  # 灰色
            'glow': False,
            'effect': 'basic',
            'frame_alpha': 0.8
        },
        'R': {
            'color': (0, 191, 255),    # 深蓝色
            'glow': True,
            'effect': 'holographic',
            'frame_alpha': 0.85
        },
        'SR': {
            'color': (148, 0, 211),    # 紫色
            'glow': True,
            'effect': 'rainbow',
            'frame_alpha': 0.9
        },
        'UR': {
            'color': (255, 215, 0),    # 金色
            'glow': True,
            'effect': 'prismatic',
            'frame_alpha': 0.95
        }
    }

        # 负面提示词
        self.negative_prompt = (
            "text, watermark, signature, frame, border, low quality, "
            "blurry, distorted, disfigured, bad anatomy, deformed, "
            "mutated, ugly, duplicate, morbid, mutilated, extra limbs"
        )

        self.background_styles = {
        'FIRE': {
            'gradient': [(255, 69, 0), (255, 140, 0)],
            'pattern': 'flames'
        },
        'WATER': {
            'gradient': [(0, 119, 190), (0, 191, 255)],
            'pattern': 'waves'
        },
        # ... 其他属性的背景样式
    }


        # 初始化字体对象
        try:
            font_path = self.resources_dir / 'fonts' / 'your-font.ttf'
            self.title_font = ImageFont.truetype(str(font_path), self.title_font_size)
            self.stats_font = ImageFont.truetype(str(font_path), self.stats_font_size)
            self.type_font = ImageFont.truetype(str(font_path), self.type_font_size)
            self.rarity_font = ImageFont.truetype(str(font_path), self.rarity_font_size)
        except Exception as e:
            logger.warning(f"Failed to load custom font: {e}, using default font")
            self.title_font = ImageFont.load_default()
            self.stats_font = ImageFont.load_default()
            self.type_font = ImageFont.load_default()
            self.rarity_font = ImageFont.load_default()

        # 初始化资源
        self._init_resources()

        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found")

        # 初始化 OpenAI 客户端（只初始化一次）
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found")

        try:
            self.openai_client = OpenAI(
                api_key=self.openai_api_key,
                base_url="https://api.openai.com/v1",
                timeout=60.0,
                max_retries=3
            )
            logger.info("OpenAI client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise




   # 添加 system_prompt 属性
        self.system_prompt = """
        You are a Pokemon card game designer. Create a new Pokemon-like creature card with the following details:
        1. Name of the creature
        2. Type (choose from: FIRE, WATER, GRASS, ELECTRIC, PSYCHIC, FIGHTING, DRAGON, DARK, STEEL, FAIRY)
        3. Attack power (between 50-200, based on the creature's characteristics)
        4. Defense power (between 30-150, based on the creature's characteristics)
        5. A detailed description for image generation (include appearance, pose, environment)
        
        Format the response as JSON with the following structure:
        {
            "name": "creature name",
            "type": "chosen type",
            "attack": number,
            "defense": number,
            "description": "detailed description"
        }
        """

            # Pokemon 类型定义
        self.pokemon_types = {
            'NORMAL': {'color': (168, 168, 120), 'icon': 'normal.png'},
            'FIRE': {'color': (240, 128, 48), 'icon': 'fire.png'},
            'WATER': {'color': (104, 144, 240), 'icon': 'water.png'},
            'GRASS': {'color': (120, 200, 80), 'icon': 'grass.png'},
            'ELECTRIC': {'color': (248, 208, 48), 'icon': 'electric.png'},
            'PSYCHIC': {'color': (248, 88, 136), 'icon': 'psychic.png'},
            'FIGHTING': {'color': (192, 48, 40), 'icon': 'fighting.png'},
            'DRAGON': {'color': (112, 56, 248), 'icon': 'dragon.png'},
            'DARK': {'color': (112, 88, 72), 'icon': 'dark.png'},
            'STEEL': {'color': (184, 184, 208), 'icon': 'steel.png'},
            'FAIRY': {'color': (238, 153, 172), 'icon': 'fairy.png'}
        }

        

      
        
        # 卡片样式定义
        self.card_styles = {
            'C': {
                'frame_pattern': 'basic_frame.png',
                'background_gradient': [(200, 200, 200), (240, 240, 240)],
                'border_style': {
                    'width': 8,
                    'color': (192, 192, 192),
                    'pattern': 'solid'
                }
            },
            'R': {
                'frame_pattern': 'rare_frame.png',
                'background_gradient': [(255, 215, 0), (218, 165, 32)],
                'border_style': {
                    'width': 10,
                    'color': (255, 215, 0),
                    'pattern': 'holo'
                }
            },
            'SR': {
                'frame_pattern': 'super_rare_frame.png',
                'background_gradient': [(148, 0, 211), (75, 0, 130)],
                'border_style': {
                    'width': 12,
                    'color': (148, 0, 211),
                    'pattern': 'rainbow'
                }
            },
            'SSR': {
                'frame_pattern': 'ultra_rare_frame.png',
                'background_gradient': [(255, 0, 0), (139, 0, 0)],
                'border_style': {
                    'width': 15,
                    'color': (255, 0, 0),
                    'pattern': 'galaxy'
                }
            }
        }


        # 资源文件路径处理
        self.resources_dir = Path(__file__).parent.parent / 'resources'
        self.fonts_dir = self.resources_dir / 'fonts'
        self.icons_dir = self.resources_dir / 'icons'
            # 创建必要的目录
        for directory in [self.resources_dir, self.fonts_dir, self.icons_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        # 字体加载处理
        try:
            font_path = self.resources_dir / 'fonts' / 'your-font.ttf'
            self.custom_font = ImageFont.truetype(str(font_path), size=32)
        except Exception as e:
            logger.warning(f"Failed to load custom font: {e}, using default font")
            self.custom_font = ImageFont.load_default()
        
        # 图标加载处理
        try:
            icon_path = self.resources_dir / 'icons' / 'energy_icon.png'
            self.energy_icon = Image.open(icon_path)
        except Exception as e:
            logger.warning(f"Failed to load energy icon: {e}")
            self.energy_icon = None

        # 添加资源路径初始化
        self.resources_dir = Path(__file__).parent / 'resources'
        self.resources_dir.mkdir(exist_ok=True)
        
        # 初始化资源
        self._init_resources()
        self._init_font()

        # 添加重试配置
        self.max_retries = 3
        self.retry_delay = 2  # 秒
        

    @backoff.on_exception(
            backoff.expo,
            (httpx.ConnectError, httpx.TimeoutException),
            max_tries=3
        )


    def test_openai_connection(self):
        """测试 OpenAI API 连接"""
        try:
            logger.info("Testing OpenAI API connection...")
            # 移除 request_timeout 参数
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hi"}
                ],
                max_tokens=5,
                temperature=0
            )
            
            if response and hasattr(response, 'choices'):
                logger.info(f"API Response: {response}")
                logger.info("API connection test successful")
                return True
            return False
        except Exception as e:
            logger.error(f"OpenAI API connection test failed: {str(e)}")
            return False




    def validate_api_key(self):
        """验证 API 密钥格式"""
        # 清理 API key
        self.openai_api_key = self.openai_api_key.strip()  # 移除空白字符和换行符
        
        if not self.openai_api_key or not self.openai_api_key.startswith('sk-'):
            raise ValueError("Invalid OpenAI API key format")
        
        # 更新客户端的 API key
        self.openai_client.api_key = self.openai_api_key
        return True

    def _init_resources(self):
        """初始化资源文件"""
        try:
            # 创建资源目录
            for directory in [self.resources_dir, self.fonts_dir, self.icons_dir]:
                directory.mkdir(parents=True, exist_ok=True)

            # 下载默认字体
            font_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
            font_path = self.fonts_dir / 'custom_font.ttf'
            if not font_path.exists():
                self._download_resource(font_url, font_path)

            # 下载默认图标
            for type_info in self.pokemon_types.values():
                icon_name = type_info['icon']
                icon_path = self.icons_dir / icon_name
                if not icon_path.exists():
                    self._create_default_icon(icon_path)

        except Exception as e:
            logger.error(f"Error initializing resources: {str(e)}")

    def _download_resource(self, url, path):
        """下载资源文件"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            path.write_bytes(response.content)
            logger.info(f"Downloaded resource to: {path}")
        except Exception as e:
            logger.error(f"Failed to download resource: {str(e)}")

    def _create_default_icon(self, path):
        """创建默认图标"""
        try:
            icon = Image.new('RGBA', (30, 30), (255, 255, 255, 0))
            draw = ImageDraw.Draw(icon)
            draw.ellipse([0, 0, 29, 29], fill=(200, 200, 200, 255))
            icon.save(path)
            logger.info(f"Created default icon at: {path}")
        except Exception as e:
         logger.error(f"Failed to create default icon: {str(e)}")

    def _init_font(self):
        """初始化字体"""
        try:
            font_dir = Path(__file__).parent / 'fonts'
            font_dir.mkdir(exist_ok=True)
            
            # 使用更适合 TCG 的字体
            font_path = font_dir / 'Orbitron-Bold.ttf'
            
            if not font_path.exists():
                font_url = ("https://github.com/google/fonts/raw/main/ofl/"
                           "orbitron/static/Orbitron-Bold.ttf")
                response = requests.get(font_url)
                font_path.write_bytes(response.content)
            
            self.title_font = ImageFont.truetype(str(font_path), self.title_font_size)
            self.stats_font = ImageFont.truetype(str(font_path), self.stats_font_size)
            self.rarity_font = ImageFont.truetype(str(font_path), self.rarity_font_size)
            
        except Exception as e:
            logger.warning(f"Failed to load custom font: {e}, using default font")
            self.title_font = ImageFont.load_default()
            self.stats_font = self.title_font
            self.rarity_font = self.title_font
            self.type_font = self.title_font  # 添加这行
    def generate_card_info(self, rarity):
        """生成卡片信息"""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Create a {rarity} rarity Pokemon card"}
            ]

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.8
            )

            # 解析响应
            content = response.choices[0].message.content
            card_info = json.loads(content)
            
            # 添加稀有度信息
            card_info['rarity'] = rarity
            
            return card_info

        except Exception as e:
            logger.error(f"Error generating card info: {str(e)}")
            # 返回默认卡片信息
            return {
                'name': 'Unknown',
                'type': 'NORMAL',
                'attack': 100,
                'defense': 100,
                'description': 'A mysterious Pokemon.',
                'creature_prompt': 'A mysterious creature',
                'frame_prompt': 'Basic frame design',
                'rarity': rarity
            }
    def generate_card(self, prompt=None):
        """生成完整的卡片"""
        try:
            # 生成卡片稀有度
            rarity = self.determine_rarity()
            logger.info(f"Generated card rarity: {rarity}")
            
            # 获取卡片信息
            try:
                card_info = self.generate_card_info(rarity)
                logger.info(f"Generated card info: {card_info}")
            except Exception as e:
                logger.error(f"Error generating card info: {str(e)}")
                card_info = {
                    'name': 'Unknown',
                    'type': 'NORMAL',
                    'attack': 100,
                    'defense': 100,
                    'description': 'A mysterious Pokemon.',
                    'creature_prompt': prompt or 'A mysterious creature',
                    'frame_prompt': 'Basic frame design',
                    'rarity': rarity
                }
            
            # 生成基础图像
            try:
                base_image = self.generate_base_image(
                    prompt or card_info.get('creature_prompt'), 
                    rarity
                )
            except Exception as e:
                logger.error(f"Error generating base image: {str(e)}")
                base_image = self._create_fallback_image(rarity, str(e))
            
            # 添加卡片详细信息
            try:
                final_image = self.add_card_details(base_image, card_info, rarity)
            except Exception as e:
                logger.error(f"Error adding card details: {str(e)}")
                final_image = base_image
            
            return final_image, card_info
            
        except Exception as e:
            logger.error(f"Critical error in generate_card: {str(e)}")
            fallback_image = self._create_fallback_image('C', str(e))
            fallback_info = {
                'name': 'Error Card',
                'type': 'NORMAL',
                'attack': 0,
                'defense': 0,
                'description': f'Error: {str(e)}',
                'rarity': 'C'
            }
            return fallback_image, fallback_info

    def generate_frame_prompt(self, card_type, rarity, style_details):
        """使用 ChatGPT 生成边框提示词"""
        try:
            client = OpenAI(api_key=self.openai_api_key)
            
            system_prompt = """
            You are a Stable Diffusion prompt expert. Create a detailed prompt for generating a Pokemon card frame.
            The prompt should:
            1. Describe the frame's visual style
            2. Include material and texture details
            3. Specify special effects and patterns
            4. Maintain card game aesthetics
            
            Return only the prompt text, no explanations.
            """
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": (
                        f"Create a frame prompt for a {card_type} type Pokemon card with {rarity} rarity. "
                        f"Style details: {json.dumps(style_details)}"
                    )}
                ],
                temperature=0.7
            )
            
            frame_prompt = response.choices[0].message.content.strip()
            return frame_prompt
            
        except Exception as e:
            logger.error(f"Error generating frame prompt: {str(e)}")
            raise

    def _ensure_resources(self):
        """确保必要的资源文件存在"""
        try:
            # 确保字体目录存在
            if not (self.fonts_dir / 'custom_font.ttf').exists():
                logger.warning("Custom font not found, using default font")
                self.custom_font = ImageFont.load_default()
            
            # 确保图标目录存在
            if not (self.icons_dir / 'energy_icon.png').exists():
                logger.warning("Energy icon not found, creating default icon")
                self._create_default_icon()
                
        except Exception as e:
            logger.error(f"Error ensuring resources: {str(e)}")
            
    def _create_default_icon(self):
        """创建默认的能量图标"""
        try:
            icon = Image.new('RGBA', (30, 30), (255, 255, 255, 0))
            draw = ImageDraw.Draw(icon)
            draw.ellipse([0, 0, 29, 29], fill=(255, 200, 0, 255))
            icon.save(self.icons_dir / 'energy_icon.png')
        except Exception as e:
            logger.error(f"Error creating default icon: {str(e)}")

    def generate_base_image(self, prompt, rarity):
        """从 API 生成基础图像"""
        try:
            # 验证 API key
            api_key = os.getenv('STABILITY_API_KEY')
            if not api_key:
                logger.error("Stability API key not found")
                return self._create_fallback_image(rarity, "No API Key Available")

            # 设置会话
            session = self._create_session()
            
            # 准备请求数据
            headers, payload = self._prepare_request_data(prompt, rarity, api_key)
            
            # 尝试每个 API 端点
            for api_base in self._get_api_endpoints():
                try:
                    image = self._try_api_endpoint(api_base, session, headers, payload)
                    if image:
                        return image
                except Exception as e:
                    logger.error(f"Error with endpoint {api_base}: {str(e)}")
                    continue
            
            return self._create_fallback_image(rarity, "All API endpoints failed")
            
        except Exception as e:
            logger.error(f"Critical error in generate_base_image: {str(e)}")
            return self._create_fallback_image(rarity, "System Error")

    def _create_fallback_image(self, rarity, error_message):
        """创建备用图像"""
        try:
            # 尝试加载预设的备用图像
            fallback_path = self.resources_dir / 'fallback' / f'{rarity.lower()}_card.png'
            if fallback_path.exists():
                logger.info(f"Using fallback image from: {fallback_path}")
                return Image.open(fallback_path)

            # 创建基本的占位图像
            logger.info("Creating basic placeholder image")
            img = Image.new('RGBA', (768, 1024), (255, 255, 255, 255))
            draw = ImageDraw.Draw(img)

            # 添加背景色
            background_color = getattr(self, 'card_styles', {}).get(rarity, {}).get(
                'background_gradient', [(200, 200, 200)])[0]
            draw.rectangle([(0, 0), (768, 1024)], fill=background_color)

            # 添加错误信息
            font = getattr(self, 'title_font', None) or ImageFont.load_default()
            text_color = (0, 0, 0)
            
            # 绘制文本
            draw.text(
                (384, 512),
                f"Image Generation Failed\n{error_message}",
                fill=text_color,
                font=font,
                anchor="mm",
                align="center"
            )

            return img

        except Exception as e:
            logger.error(f"Error creating fallback image: {str(e)}")
            # 返回最基本的纯色图像
            return Image.new('RGBA', (768, 1024), (255, 255, 255, 255))



    def generate_card_frame(self, frame_prompt, rarity):
        """生成卡片边框"""
        try:
            api_key = os.getenv('STABILITY_AI_API_KEY')
            if not api_key:
                raise ValueError("Stability AI API key not found")
                
            # 检查 API 余额
            balance_url = "https://api.stability.ai/v1/user/balance"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            balance_response = requests.get(balance_url, headers=headers)
            if balance_response.status_code == 200:
                balance_data = balance_response.json()
                if balance_data.get('credits') < 0.01:
                    raise ValueError("Insufficient Stability AI API balance")

            api_url = "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/text-to-image"
            
            payload = {
                "text_prompts": [
                    {"text": frame_prompt, "weight": 1},
                    {"text": self.negative_prompt, "weight": -1}
                ],
                "cfg_scale": 8,
                "height": 1024,
                "width": 768,
                "samples": 1,
                "steps": 30
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                raise ValueError(f"Frame API Error: {response.text}")
                
            response_data = response.json()
            frame_data = base64.b64decode(response_data['artifacts'][0]['base64'])
            frame_image = Image.open(BytesIO(frame_data)).convert('RGBA')
            
            return frame_image
            
        except Exception as e:
            logger.error(f"Error generating frame: {str(e)}")
            raise

    def combine_card_with_frame(self, base_image, frame_image, rarity):
        """合并卡片图像和边框"""
        try:
            # 确保图像尺寸一致
            base_image = base_image.resize((self.card_width, self.card_height))
            frame_image = frame_image.resize((self.card_width, self.card_height))
            
            # 转换为 RGBA 模式
            if base_image.mode != 'RGBA':
                base_image = base_image.convert('RGBA')
            if frame_image.mode != 'RGBA':
                frame_image = frame_image.convert('RGBA')
            
            # 获取稀有度样式
            style = self.rarity_styles.get(rarity, self.rarity_styles['C'])
            
            # 调整边框透明度
            frame_alpha = int(255 * style.get('frame_alpha', 0.8))
            frame_image.putalpha(frame_alpha)
            
            # 合并图层
            combined = Image.alpha_composite(base_image, frame_image)
            
            # 添加特效
            effect_type = style.get('effect', 'basic')
            if effect_type == 'holographic':
                combined = self.add_holographic_effect(combined)
            elif effect_type == 'rainbow':
                combined = self.add_rainbow_effect(combined)
            elif effect_type == 'prismatic':
                combined = self.add_prismatic_effect(combined)
            
            return combined
            
        except Exception as e:
            logger.error(f"Error combining card with frame: {str(e)}")
            raise

    def add_rainbow_effect(self, image):
        """添加彩虹特效"""
        try:
            # 创建彩虹渐变层
            gradient = Image.new('RGBA', image.size)
            draw = ImageDraw.Draw(gradient)
            
            colors = [
                (255, 0, 0, 30),    # 红
                (255, 127, 0, 30),  # 橙
                (255, 255, 0, 30),  # 黄
                (0, 255, 0, 30),    # 绿
                (0, 0, 255, 30),    # 蓝
                (75, 0, 130, 30),   # 靛
                (148, 0, 211, 30)   # 紫
            ]
            
            height = image.height
            for i, color in enumerate(colors):
                y0 = int(height * i / len(colors))
                y1 = int(height * (i + 1) / len(colors))
                draw.rectangle([(0, y0), (image.width, y1)], fill=color)
            
            return Image.alpha_composite(image, gradient)
            
        except Exception as e:
            logger.error(f"Error adding rainbow effect: {str(e)}")
            return image

    def add_prismatic_effect(self, image):
        """添加棱镜特效"""
        try:
            # 创建高光层
            highlight = Image.new('RGBA', image.size)
            draw = ImageDraw.Draw(highlight)
            
            # 添加对角线高光
            for i in range(0, image.width + image.height, 20):
                draw.line(
                    [(i, 0), (0, i)],
                    fill=(255, 255, 255, 20),
                    width=10
                )
            
            # 添加一些随机的光点
            for _ in range(50):
                x = random.randint(0, image.width)
                y = random.randint(0, image.height)
                r = random.randint(2, 5)
                draw.ellipse(
                    [(x-r, y-r), (x+r, y+r)],
                    fill=(255, 255, 255, 30)
                )
            
            return Image.alpha_composite(image, highlight)
            
        except Exception as e:
            logger.error(f"Error adding prismatic effect: {str(e)}")
            return image

    def add_card_details(self, image, card_info, rarity):
        """添加卡片详细信息"""
        try:
            # 创建可绘制的图像副本
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            draw = ImageDraw.Draw(image)
            
            # 获取卡片类型信息，使用默认值如果类型不存在
            card_type = card_info.get('type', 'NORMAL')
            type_info = self.pokemon_types.get(card_type, self.pokemon_types['NORMAL'])
            
            # 获取样式
            style = self.rarity_styles.get(rarity, self.rarity_styles['C'])
            
            # 使用默认字体如果自定义字体加载失败
            title_font = getattr(self, 'title_font', None) or ImageFont.load_default()
            stats_font = getattr(self, 'stats_font', None) or ImageFont.load_default()
            
            # 添加标题
            name = card_info.get('name', 'Unknown')
            draw.text((384, 100), name, 
                    font=title_font, 
                    fill=style['color'], 
                    anchor="mm")
            
            # 添加类型图标和文本
            type_text = card_type
            draw.text((384, 150), type_text, 
                    font=stats_font, 
                    fill=type_info['color'], 
                    anchor="mm")
            
            # 添加攻击和防御值
            attack = str(card_info.get('attack', 0))
            defense = str(card_info.get('defense', 0))
            draw.text((100, 900), f"ATK: {attack}", 
                    font=stats_font, 
                    fill=style['color'], 
                    anchor="lm")
            draw.text((668, 900), f"DEF: {defense}", 
                    font=stats_font, 
                    fill=style['color'], 
                    anchor="rm")
            
            # 添加描述文本
            description = card_info.get('description', '')
            wrapped_text = textwrap.fill(description, width=40)
            draw.text((384, 800), wrapped_text, 
                    font=stats_font, 
                    fill=style['color'], 
                    anchor="mm", 
                    align="center")
            
            return image
            
        except Exception as e:
            logger.error(f"Error adding card details: {str(e)}")
            # 返回原始图像而不是抛出异常
            return image

    def process_card_image(self, base_image, rarity, card_details=None):
        """处理卡片图像
        Args:
            base_image: 基础图像
            rarity: 稀有度
            card_details: 可选的卡片详细信息
        """
        try:
            # 创建新的 RGBA 图像
            card = Image.new('RGBA', (self.card_width, self.card_height), (0, 0, 0, 0))
            
            # 调整基础图像大小
            base_image = base_image.resize((self.card_width, self.card_height), Image.Resampling.LANCZOS)
            
            # 粘贴基础图像
            card.paste(base_image, (0, 0))
            
            # 生成卡片边框
            frame = self.generate_card_frame(rarity)
            
            # 合并卡片和边框
            card = self.combine_card_with_frame(card, frame, rarity)
            
            # 如果有卡片详情，添加文字和图标
            if card_details:
                draw = ImageDraw.Draw(card)
                
                # 添加名称
                name_y = 50
                draw.text(
                    (self.card_width // 2, name_y),
                    card_details['name'],
                    font=self.title_font,
                    fill=(0, 0, 0),
                    anchor="mm"
                )
                
                # 添加类型
                type_y = 100
                pokemon_type = card_details['type']
                type_color = self.pokemon_types.get(pokemon_type, {'color': (0, 0, 0)})['color']
                draw.text(
                    (self.card_width // 2, type_y),
                    pokemon_type,
                    font=self.type_font,
                    fill=type_color,
                    anchor="mm"
                )
                
                # 添加攻击和防御值
                stats_y = self.card_height - 100
                draw.text(
                    (100, stats_y),
                    f"ATK: {card_details['attack']}",
                    font=self.stats_font,
                    fill=(0, 0, 0)
                )
                draw.text(
                    (self.card_width - 100, stats_y),
                    f"DEF: {card_details['defense']}",
                    font=self.stats_font,
                    fill=(0, 0, 0)
                )
            
            # 添加稀有度标记
            if hasattr(self, 'add_rarity_mark'):
                card = self.add_rarity_mark(card, rarity)
            
            return card
            
        except Exception as e:
            logger.error(f"Error processing card image: {str(e)}")
            raise

    def add_rarity_effects(self, image, rarity):
        """添加稀有度特效"""
        style = self.rarity_styles[rarity]
        
        if style['effect'] == 'basic':
            return image
            
        elif style['effect'] == 'holo':
            # 添加全息效果
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.1)
            
        elif style['effect'] == 'premium':
            # 添加发光效果
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.2)
            image = image.filter(ImageFilter.GaussianBlur(1))
            
        elif style['effect'] == 'ultimate':
            # 添加终极效果
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.3)
            image = image.filter(ImageFilter.GaussianBlur(2))
            
        return image

    def add_pokemon_type(self, image, rarity):
        """添加宝可梦属性标记（改进版）"""
        draw = ImageDraw.Draw(image)
        
        # 随机选择一个属性
        pokemon_type = random.choice(list(self.pokemon_types.keys()))
        type_style = self.pokemon_types[pokemon_type]
        
        # 文本位置（右上角）
        margin = 50
        text = type_style['text']
        bbox = draw.textbbox((0, 0), text, font=self.type_font)
        text_width = bbox[2] - bbox[0]
        
        x = self.card_width - text_width - margin
        y = margin
        
        # 添加装饰性背景
        padding = 25
        background = Image.new('RGBA', (
            text_width + padding*2,
            bbox[3] - bbox[1] + padding*2
        ))
        bg_draw = ImageDraw.Draw(background)
        
        # 绘制渐变背景
        for i in range(background.height):
            alpha = int(220 * (1 - i/background.height))
            color = (*type_style['color'], alpha)
            bg_draw.line([(0, i), (background.width, i)], fill=color)
        
        # 添加边框
        bg_draw.rectangle(
            [(0, 0), (background.width-1, background.height-1)],
            outline=(255, 255, 255),
            width=4
        )
        
        # 将背景粘贴到主图像
        image.paste(background, (
            int(x - padding),
            int(y - padding)
        ), background)
        
        # 添加文本阴影
        shadow_offset = 3
        draw.text(
            (x + shadow_offset, y + shadow_offset),
            text,
            font=self.type_font,
            fill=(0, 0, 0, 180)
        )
        
        # 添加主文本
        draw.text(
            (x, y),
            text,
            font=self.type_font,
            fill=(255, 255, 255)
        )
        
        return image

    def add_card_border(self, image, rarity):
        """添加高级卡片边框"""
        style = self.rarity_styles[rarity]
        draw = ImageDraw.Draw(image)
        
        # 基础边框
        border_width = 8  # 宝可梦卡片风格的边框宽度
    
    # 外边框
        draw.rectangle(
            [(0, 0), (self.card_width-1, self.card_height-1)],
            outline=style['border_color'],
            width=border_width
        )
        
        # 内边框（图片区域）
        image_margin = 35
        draw.rectangle(
            [(image_margin, image_margin), 
            (self.card_width-image_margin, self.card_height-image_margin*3)],  # 留出更多底部空间
            outline=style['border_color'],
            width=border_width//2
        )
        
        # 添加稀有度特效
        if style['effect'] != 'basic':
            # 添加闪光效果
            alpha = 100  # 透明度
            for i in range(3):
                offset = i * 2
                draw.rectangle(
                    [(offset, offset), 
                    (self.card_width-offset-1, self.card_height-offset-1)],
                    outline=(*style['border_color'], alpha),
                    width=1
                )
        
        return image

    def _add_gradient_border(self, draw, style):
        """添加渐变边框"""
        for i in range(12):
            alpha = int(255 * (1 - i/12))
            color = style['border_color'] + (alpha,)
            draw.rectangle(
                [(i, i), (self.card_width-i-1, self.card_height-i-1)],
                outline=color,
                width=1
            )

    def _add_corner_decorations(self, draw, style):
        """添加角落装饰"""
        corner_size = 40
        for x, y in [(0, 0), (0, self.card_height), 
                     (self.card_width, 0), (self.card_width, self.card_height)]:
            self._draw_corner_decoration(draw, x, y, corner_size, style)


    def _draw_attack_icon(self, draw, x, y):
        """绘制攻击力图标"""
        try:
            icon_path = self.resources_dir / 'attack_icon.png'
            if icon_path.exists():
                icon = Image.open(icon_path).convert('RGBA')
                icon = icon.resize((40, 40))  # 调整图标大小
                return icon
            else:
                # 如果图标不存在，绘制一个简单的替代图标
                size = 40
                icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                icon_draw = ImageDraw.Draw(icon)
                icon_draw.ellipse([(0, 0), (size, size)], 
                                fill=(255, 69, 0, 200))  # 火红色
                icon_draw.text((size//4, size//4), "⚔️", 
                            fill=(255, 255, 255, 255))
                return icon
                
        except Exception as e:
            logger.error(f"Error drawing attack icon: {str(e)}")
            return None

    def _draw_defense_icon(self, draw, x, y):
        """绘制防御力图标"""
        try:
            icon_path = self.resources_dir / 'defense_icon.png'
            if icon_path.exists():
                icon = Image.open(icon_path).convert('RGBA')
                icon = icon.resize((40, 40))  # 调整图标大小
                return icon
            else:
                # 如果图标不存在，绘制一个简单的替代图标
                size = 40
                icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                icon_draw = ImageDraw.Draw(icon)
                icon_draw.ellipse([(0, 0), (size, size)], 
                                fill=(0, 119, 190, 200))  # 水蓝色
                icon_draw.text((size//4, size//4), "🛡️", 
                            fill=(255, 255, 255, 255))
                return icon
                
        except Exception as e:
            logger.error(f"Error drawing defense icon: {str(e)}")
            return None

    def _draw_corner_decoration(self, draw, x, y, size, style):
        """绘制角落装饰"""
        points = [
            (x, y),
            (x + size, y),
            (x + size//2, y + size//2),
            (x, y + size)
        ]
        draw.polygon(points, fill=style['border_color'])

    def add_stats_frame(self, image, rarity):
        """添加属性框架（宝可梦风格）"""
        draw = ImageDraw.Draw(image)
        style = self.rarity_styles[rarity]
        
        # 生成随机属性值
        attack = random.randint(50, 200)
        defense = random.randint(30, 150)
        
        # 属性框位置
        stats_y = self.card_height - 250
        frame_height = 200
        frame_padding = 40
        
        # 绘制属性框背景
        self._draw_stats_background(draw, stats_y, frame_height, style)
        
        # 添加攻击力图标和数值
        attack_x = frame_padding + 60
        attack_y = stats_y + 50
        
        attack_icon = self._draw_attack_icon(draw, attack_x - 40, attack_y + 10)
        if attack_icon:
            image.paste(attack_icon, (attack_x - 40, attack_y + 10), attack_icon)
        
        # 添加防御力图标和数值
        defense_x = self.card_width // 2 + 60
        defense_y = stats_y + 50
        
        defense_icon = self._draw_defense_icon(draw, defense_x - 40, defense_y + 10)
        if defense_icon:
            image.paste(defense_icon, (defense_x - 40, defense_y + 10), defense_icon)
        
        # 添加属性值文本（带阴影效果）
        text_color = (255, 255, 255)
        shadow_color = (0, 0, 0, 180)
        
        # 攻击力文本
        draw.text((attack_x+3, attack_y+3), str(attack), 
                font=self.stats_font, fill=shadow_color)
        draw.text((attack_x, attack_y), str(attack), 
                font=self.stats_font, fill=text_color)
        
        # 防御力文本
        draw.text((defense_x+3, defense_y+3), str(defense), 
                font=self.stats_font, fill=shadow_color)
        draw.text((defense_x, defense_y), str(defense), 
                font=self.stats_font, fill=text_color)
        
        return image
    
    def _draw_stats_background(self, draw, y, height, style):
        """绘制属性区域的装饰性背景"""
        # 渐变背景
        for i in range(height):
            alpha = int(200 * (1 - i/height))  # 渐变透明度
            color = (*style['border_color'], alpha)
            draw.line([(40, y+i), (self.card_width-40, y+i)], fill=color)
        
        # 添加装饰性图案
        pattern_color = (*style['border_color'], 100)
        # 这里可以添加更多装饰性图案

 
    def add_rarity_mark(self, image, rarity):
        """添加稀有度标记"""
        style = self.rarity_styles[rarity]
        draw = ImageDraw.Draw(image)
        
        # 文本位置（左上角）
        margin = 25
        x, y = margin, margin
        
        # 获取文本大小
        text = style['text']
        bbox = draw.textbbox((x, y), text, font=self.rarity_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 添加发光背景
        glow_padding = 15
        draw.rectangle(
            [(x-glow_padding, y-glow_padding),
             (x+text_width+glow_padding, y+text_height+glow_padding)],
            fill=style['glow_color']
        )
        
        # 添加文本阴影
        shadow_offset = 3
        draw.text(
            (x+shadow_offset, y+shadow_offset),
            text,
            font=self.rarity_font,
            fill=(0, 0, 0, 180)
        )
        
        # 添加主文本
        draw.text(
            (x, y),
            text,
            font=self.rarity_font,
            fill=style['color']
        )
        
        return image

    def add_holographic_effect(self, image):
        """添加全息效果"""
        # 创建彩虹渐变
        gradient = Image.new('RGBA', image.size)
        draw = ImageDraw.Draw(gradient)
        
        # 添加彩虹色渐变
        colors = [
            (255, 0, 0, 50),    # 红
            (255, 127, 0, 50),  # 橙
            (255, 255, 0, 50),  # 黄
            (0, 255, 0, 50),    # 绿
            (0, 0, 255, 50),    # 蓝
            (75, 0, 130, 50),   # 靛
            (148, 0, 211, 50)   # 紫
        ]
        
        height = image.height
        for i, color in enumerate(colors):
            y0 = int(height * i / len(colors))
            y1 = int(height * (i + 1) / len(colors))
            draw.rectangle([(0, y0), (image.width, y1)], fill=color)
        
        # 将渐变叠加到原图
        return Image.alpha_composite(image, gradient)

    def save_card_image(self, image, rarity):
        """保存卡片图像"""
        try:
            # 确保目录存在
            media_path = Path("media/cards")
            media_path.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"card_{timestamp}_{rarity}.png"
            filepath = media_path / filename
            
            # 保存图像
            image.save(filepath, "PNG")
            logger.info(f"Saved card image to: {filepath}")
            
            return f"cards/{filename}"
            
        except Exception as e:
            logger.error(f"Error saving card image: {str(e)}")
            raise

    def determine_rarity(self):
        """确定卡片稀有度"""
        rand = random.random()
        cumulative = 0
        for rarity, weight in self.rarity_weights.items():
            cumulative += weight
            if rand <= cumulative:
                return rarity
        return 'C'