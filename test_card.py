# test_stability.py
import requests
import json
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_stability_api():
    # 加载环境变量
    load_dotenv()
    
    api_key = os.getenv('STABILITY_AI_API_KEY')
    if not api_key:
        logger.error("No API key found!")
        return
        
    api_url = "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/text-to-image"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "text_prompts": [
            {
                "text": "a majestic fire dragon pokemon, digital art style",
                "weight": 1
            }
        ],
        "cfg_scale": 7,
        "height": 512,
        "width": 512,
        "samples": 1,
        "steps": 30
    }
    
    try:
        logger.info("Sending test request to Stability AI API...")
        response = requests.post(api_url, headers=headers, json=payload)
        
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            logger.info("Successfully generated image!")
            return True
        else:
            logger.error(f"Error Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_stability_api()