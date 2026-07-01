import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            self.user_group_name = f"user_{self.user.id}"
            await self.channel_layer.group_add(self.user_group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            "type": "notification",
            "message": event["message"],
            "title": event.get("title", "Notification"),
            "url": event.get("url"),
            "timestamp": timezone.now().isoformat()
        }))


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.classroom_slug = self.scope["url_route"]["kwargs"]["classroom_slug"]
        self.chat_group_name = f"chat_{self.classroom_slug}"
        self.user = self.scope["user"]

        if self.user.is_authenticated:
            await self.channel_layer.group_add(self.chat_group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "chat_group_name"):
            await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                "type": "chat_message",
                "message": message,
                "username": self.user.get_full_name() or self.user.username,
                "user_id": self.user.id,
                "timestamp": timezone.now().isoformat()
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat",
            "message": event["message"],
            "username": event["username"],
            "user_id": event["user_id"],
            "timestamp": event["timestamp"]
        }))