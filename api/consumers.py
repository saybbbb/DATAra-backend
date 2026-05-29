import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework.authtoken.models import Token
from .predictor import DataUsagePredictor

logger = logging.getLogger(__name__)

@database_sync_to_async
def get_user_from_token(token_key):
    try:
        token = Token.objects.select_related('user').get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        return None

class PredictionConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize the ML predictor
        self.predictor = DataUsagePredictor()

    async def connect(self):
        # Extract query parameters
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        params = parse_qs(query_string)
        token_keys = params.get('token', [])
        
        user = None
        if token_keys:
            token_key = token_keys[0]
            user = await get_user_from_token(token_key)
            
        if not user:
            logger.warning("WebSocket connection rejected: Invalid or missing authentication token.")
            await self.close(code=4003)  # Custom code for Unauthorized
            return
            
        self.scope['user'] = user
        await self.accept()
        logger.info(f"WebSocket connection established for User: {user.username}")
        
        # Send initial success greeting
        await self.send_json({
            "status": "connected",
            "message": f"Real-time DATAra Live Prediction service active. Logged in as {user.username}."
        })

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")

    async def receive_json(self, content):
        """
        Receives real-time stats from the mobile client and returns predictions.
        
        Expected payload format:
        {
            "remaining_mb": 5000.0,
            "expiry_time": "2026-05-30T12:00:00",
            "screen_on": 0.8,
            "battery_level": 75.0
        }
        """
        try:
            remaining_mb = float(content.get("remaining_mb", 0.0))
            expiry_time = content.get("expiry_time", "")
            screen_on = float(content.get("screen_on", 0.5))
            battery_level = float(content.get("battery_level", 80.0))
            
            # Input validation checks
            if remaining_mb < 0:
                await self.send_json({
                    "error": "Input validation error: 'remaining_mb' cannot be negative."
                })
                return
            if not (0.0 <= screen_on <= 24.0):
                await self.send_json({
                    "error": "Input validation error: 'screen_on' must be between 0.0 and 24.0 hours."
                })
                return
            if not (0.0 <= battery_level <= 100.0):
                await self.send_json({
                    "error": "Input validation error: 'battery_level' must be between 0.0 and 100.0 percent."
                })
                return
            
            if not expiry_time:
                await self.send_json({
                    "error": "Missing 'expiry_time' field in ISO format (YYYY-MM-DDTHH:MM:SS)."
                })
                return
                
            # Perform prediction using ML model / fallback
            # We run this in a threadpool so it doesn't block the async event loop
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(
                    pool,
                    self.predictor.project_depletion,
                    remaining_mb,
                    expiry_time,
                    screen_on,
                    battery_level
                )
            
            # Send prediction results back to the client
            await self.send_json({
                "status": "prediction_updated",
                "remaining_mb": remaining_mb,
                "hours_remaining": result["hours_remaining"],
                "depletion_time": result["depletion_time"],
                "runs_out_before_expiry": result["runs_out_before_expiry"],
                "usage_pace": result["usage_pace"],
                "hours_to_expiry": result["hours_to_expiry"],
                "predicted_trajectory": result["predicted_trajectory"]
            })
            
        except ValueError as ve:
            await self.send_json({
                "error": f"Invalid input value type: {str(ve)}"
            })
        except Exception as e:
            logger.error(f"WebSocket prediction error: {e}", exc_info=True)
            await self.send_json({
                "error": f"Internal prediction server error: {str(e)}"
            })
