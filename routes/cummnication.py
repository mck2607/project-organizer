from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from models import Employee, ProjectMaster, ProjectAssignment, ProjectData, ProjectUpdates
from sqlalchemy import select, and_, or_
from credentials import database as db
from typing import List, Union, Optional
from fastapi import APIRouter, Request, Form, UploadFile, File, Depends, Query
import os
import shutil
from datetime import datetime
import json
import bleach
from bleach.css_sanitizer import CSSSanitizer

with open("credentials\secret_config.json") as f:
    file_d = json.loads(f.read())
user_data_file_path = file_d['user_data_file_path']

templates = Jinja2Templates(directory="templates")
router = APIRouter()

# Allowed HTML tags and attributes for sanitization
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'a', 'blockquote', 'code', 'pre',
    'span', 'div'
]

ALLOWED_ATTRS = {
    'a': ['href', 'title', 'target'],
    'span': ['style'],
    'p': ['style'],
    'code': ['class'],
    'pre': ['class']
}

ALLOWED_STYLES = ['color', 'background-color']


def sanitize_html(html_content: str) -> str:
    """Sanitize HTML content to prevent XSS attacks while preserving formatting"""

    # Create a CSSSanitizer instance with the allowed styles
    css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_STYLES)

    return bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        css_sanitizer=css_sanitizer,  # Use css_sanitizer instead of styles
        strip=True
    )


def process_message_images(message_dict):
    """Process message images from JSON string to list"""
    if message_dict.get('images') and message_dict['images'] != 'N/A':
        try:
            message_dict['images'] = json.loads(message_dict['images'])
        except:
            message_dict['images'] = []
    else:
        message_dict['images'] = []
    return message_dict


def format_message_date(message_dict):
    """Format the created_at field properly"""
    if message_dict.get('created_at'):
        date_obj = message_dict['created_at']

        # If it's a string, convert it to datetime
        if isinstance(date_obj, str):
            try:
                date_obj = datetime.strptime(date_obj, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Try alternative format
                try:
                    date_obj = datetime.fromisoformat(date_obj)
                except:
                    pass

        # Format the datetime object
        if isinstance(date_obj, datetime):
            message_dict['created_at'] = date_obj.strftime('%b %d, %Y at %I:%M %p')

    return message_dict

@router.post("/send-communication")
async def send_communication(
        # Changed from sending_type to feedback_type to match HTML name="feedback_type"
        feedback_type: str = Form(...),
        message: str = Form(...),
        # Changed to match JavaScript formData.append('images', ...)
        feedback_images: Union[List[UploadFile], None] = File(default=None),
        sender_username: str = Form(...),
        sender_name: str = Form(default="Anonymous"),  # Added default or ensure it's sent
        project_id: str = Form(...),
        db_con: AsyncSession = Depends(db.get_db)
):
    """Handle message submission with rich text content"""
    try:
        try:
            p_id = int(project_id)
        except ValueError:
            return {"success": False, "message": "Invalid Project ID format"}

        # 2. Sanitize
        sanitized_message = sanitize_html(message)

        # 3. Handle Images
        file_dir = os.path.join(user_data_file_path, "UPDATES")
        os.makedirs(file_dir, exist_ok=True)

        saved_files_list = []
        if feedback_images:
            for img in feedback_images:
                if img.filename:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{img.filename}"
                    file_path = os.path.join(file_dir, filename)
                    with open(file_path, "wb") as f:
                        shutil.copyfileobj(img.file, f)
                    saved_files_list.append(filename)  # Store just filename or relative path

            saved_files_str = json.dumps(saved_files_list) if saved_files_list else "N/A"
        # 4. Get Project Info
        else:
            saved_files_str = "N/A"

        created_at = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Get project information
        pr_q = await db_con.execute(
            select(ProjectMaster).where(ProjectMaster.project_id == p_id)
        )
        project_info = pr_q.scalars().first()
        if not project_info:
            pr_q = await db_con.execute(
                select(ProjectData).where(ProjectData.project_id == p_id)
            )
            project_info = pr_q.scalars().first()

        if project_info:
            project_info = db.orm_to_dict(project_info)
        else:
            return {"success": False, "message": "Project not found"}

        # 5. Insert with correct types
        insert_update = ProjectUpdates(
            project_id=p_id,
            project_name=project_info['project_name'],
            sender_username=sender_username,
            sender_name=sender_name,
            text=sanitized_message,
            images=saved_files_str,
            type_of_text=feedback_type,
            created_at=created_at,  # Use datetime object, let SQLAlchemy format it
            department='project',
        )

        db_con.add(insert_update)
        await db_con.commit()

        return {
            "success": True,
            "message": f"{feedback_type.capitalize()} sent successfully!"
        }
    except Exception as e:
        print(f"Error in send_communication: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}


@router.get("/get-feedbacks/{project_id}")
async def get_feedbacks(project_id: str, db_session: AsyncSession = Depends(db.get_db)):
    # 1. Convert the incoming string project_id to an integer
    try:
        project_id_int = int(project_id)
    except ValueError:
        return {"success": False, "message": "Invalid Project ID format"}

    query = (
        select(ProjectUpdates)
        .where(
            and_(
                # 2. Use the integer variable here
                ProjectUpdates.project_id == project_id_int,
                ProjectUpdates.department == 'project'
            )
        )
    )

    result = await db_session.execute(query)
    rows = result.scalars().all()

    feedbacks = []
    if rows:
        rows = [db.orm_to_dict(x) for x in rows]
        for record in rows:
            record['type'] = record['type_of_text']
            record['message'] = record['text']
            if record['images'] == "N/A":
                record['file_paths'] = None
            else:
                record['file_paths'] = json.loads(record['images'])
            feedbacks.append(record)

    return feedbacks