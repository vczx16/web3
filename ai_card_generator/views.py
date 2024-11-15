from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from .services.ai_service import AICardGenerator
from .models import Card
from .serializers import CardSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
import json
import requests
logger = logging.getLogger(__name__)

class CardGeneratorView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'prompt': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Optional prompt for card generation'
                )
            },
            required=[]
        ),
        responses={
            201: 'Card generated successfully',
            400: 'Bad request',
            500: 'Server error'
        }
    )
    def post(self, request):
        try:
            # 获取请求参数
            prompt = request.data.get('prompt', 'string')
            logger.info(f"Generating card with prompt: {prompt}")

            # 创建生成器实例
            generator = AICardGenerator()
            logger.info("Created AICardGenerator instance")

            # 生成卡片
            final_image, card_info = generator.generate_card(prompt)
            logger.info(f"Generated card info: {card_info}")

            # 保存图片
            image_path = generator.save_card_image(final_image, card_info['rarity'])
            logger.info(f"Saved image to: {image_path}")

            # 创建数据库记录
            try:
                card = Card.objects.create(
                    name=card_info['name'],
                    description=card_info['description'],
                    image=image_path,
                    rarity=card_info['rarity'],
                    type=card_info['type'],
                    attack=card_info['attack'],
                    defense=card_info['defense'],
                    prompt=prompt
                )

                # 序列化响应数据
                serializer = CardSerializer(card)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"Database error: {str(e)}")
                return Response(
                    {'error': f'Database error: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Server error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class CardListView(ListAPIView):
    queryset = Card.objects.all().order_by('-created_at')
    serializer_class = CardSerializer
    
    @swagger_auto_schema(
        operation_description="Get list of all generated cards",
        responses={
            200: openapi.Response(
                description="Cards retrieved successfully",
                examples={
                    "application/json": {
                        "message": "Cards retrieved successfully",
                        "data": [
                            {
                                "id": "uuid",
                                "title": "string",
                                "description": "string",
                                "image_url": "string",
                                "rarity": "string",
                                "rarity_rate": "float",
                                "created_at": "datetime"
                            }
                        ]
                    }
                }
            ),
            500: 'Internal Server Error'
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            response = super().get(request, *args, **kwargs)
            logger.info("Successfully retrieved card list")
            return Response(
                {
                    'message': 'Cards retrieved successfully',
                    'data': response.data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error retrieving card list: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve cards'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )