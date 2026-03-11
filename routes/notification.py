from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from models import Notification
from fastapi.responses import RedirectResponse
import json
from fastapi.templating import Jinja2Templates
from credentials import database as db
from fastapi import WebSocket, Depends, APIRouter, WebSocketDisconnect
from sqlalchemy import select, func, and_, or_, ForeignKey, update
from typing import Dict

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"✅ WebSocket connected for user: {user_id}")

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)
        print(f"❌ WebSocket disconnected for user: {user_id}")

    async def send_to_user(self, user_id: str, message: str):
        websocket = self.active_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_text(message)
                return True
            except Exception as e:
                print(f"Error sending message to user {user_id}: {e}")
                self.disconnect(user_id)
                return False
        return False

manager = ConnectionManager()

templates = Jinja2Templates(directory="templates")
router = APIRouter()

@router.get('/notifications')
async def get_notification(request: Request):
    username = request.session.get('username', None)
    name = request.session.get('name', None)
    if not username:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("notification.html", {"request": request, "username": username,
                                                            "name":name,
                                                        })

@router.get('/fetch-notification/{user_id}')
async def get_notification_data(user_id:str=None,db_con: AsyncSession = Depends(db.get_db)):
    if user_id:
        query = select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(20)
        result = await db_con.execute(query)
        notification_data = [db.orm_to_dict(x) for x in  result.scalars().all()]
    else:
        notification_data = []
    return notification_data


# WebSocket endpoint for notifications
@router.websocket("/ws/notifications/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep connection alive and wait for messages
            data = await websocket.receive_text()
            # Echo back or handle client messages if needed
            print(f"Received from {user_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        print(f"User {user_id} disconnected")
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)


async def notify(
    db_con: AsyncSession = Depends(db.get_db),
    *,
    user_id: str,
    sender_id: str,
    sender_name: str | None = None,
    type: str | None = None,
    title: str | None = None,
    message: str,
):
    notification = Notification(
        user_id=user_id,
        sender_id=sender_id,
        sender_name=sender_name,
        type=type,
        title=title,
        message=message
    )

    db_con.add(notification)
    await db_con.commit()
    await db_con.refresh(notification)

    # Prepare payload with event wrapper for client-side handling
    payload = json.dumps({
        "event": "notification",
        "data": {
            "id": notification.id,
            "user_id": user_id,
            "type": type,
            "title": title,
            "message": message,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "created_at": str(notification.created_at)
        }
    })

    delivered = await manager.send_to_user(user_id, payload)

    return {
        "notification_id": notification.id,
        "delivered": delivered
    }