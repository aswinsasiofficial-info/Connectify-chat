import json
import base64
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Message
from django.core.files.base import ContentFile

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.other_username = self.scope['url_route']['kwargs']['username']
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return

        # Room name should be unique for the two users
        users = sorted([self.user.username, self.other_username])
        self.room_name = f'chat_{users[0]}_{users[1]}'
        self.room_group_name = f'chat_{self.room_name}'
        self.user_group_name = f'user_{self.user.username}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        await self.accept()

        # Mark as read when connecting to a specific chat room
        await self.mark_messages_as_read()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

    async def mark_messages_as_read(self):
        other_user = await database_sync_to_async(User.objects.get)(username=self.other_username)
        await database_sync_to_async(Message.objects.filter(
            sender=other_user,
            receiver=self.user,
            is_read=False
        ).update)(is_read=True)
        
        # Notify the sender that their messages have been read
        await self.channel_layer.group_send(
            f'user_{self.other_username}',
            {
                'type': 'messages_read',
                'reader': self.user.username
            }
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        
        if data.get('type') == 'mark_read':
            await self.mark_messages_as_read()
            return

        message_text = data.get('message', '')
        image_data = data.get('image', None)
        
        sender = self.user
        receiver = await database_sync_to_async(User.objects.get)(username=self.other_username)

        image_url = None
        if image_data:
            format, imgstr = image_data.split(';base64,')
            ext = format.split('/')[-1]
            image_file = ContentFile(base64.b64decode(imgstr), name=f'{uuid.uuid4()}.{ext}')
            
            # Save message with image
            msg = await database_sync_to_async(Message.objects.create)(
                sender=sender,
                receiver=receiver,
                text=message_text,
                image=image_file
            )
            image_url = msg.image.url
        else:
            # Save text-only message
            msg = await database_sync_to_async(Message.objects.create)(
                sender=sender,
                receiver=receiver,
                text=message_text
            )

        # Broadcast to room group (sender and receiver if they are in the same room)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_text,
                'sender': sender.username,
                'image_url': image_url,
                'timestamp': msg.timestamp.isoformat(),
                'is_read': False
            }
        )
        
        # Also broadcast to receiver's private group for unread notification
        await self.channel_layer.group_send(
            f'user_{self.other_username}',
            {
                'type': 'unread_notification',
                'sender': sender.username,
                'message': message_text[:30] + '...' if len(message_text) > 30 else message_text
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
            'image_url': event['image_url'],
            'timestamp': event['timestamp']
        }))

    async def unread_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'unread_notification',
            'sender': event['sender'],
            'message': event['message']
        }))

    async def messages_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'reader': event['reader']
        }))
