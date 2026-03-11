import json
from fastapi import APIRouter, HTTPException, Request, Form, UploadFile, File, Depends
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import JSONResponse
from credentials import database as db
import os
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from sqlalchemy import select, func, and_, or_, ForeignKey
from sqlalchemy.orm import selectinload
import shutil
from datetime import datetime, date
from models import (
    KnowledgePost, PostFile, PostFeedback, PostLike
)

with open("credentials\secret_config.json") as f:
    file_d = json.loads(f.read())
user_data_file_path = file_d['user_data_file_path']


UPLOAD_DIR = f"{user_data_file_path}/uploads-knowledge"
os.makedirs(UPLOAD_DIR, exist_ok=True)


router = APIRouter()
templates = Jinja2Templates(directory="templates")

knowledge_categories = [
    'Blocking',
    'Other',
    'Documentation',
    'Developement',
    'Api',
    'Database',
    'Automation',
    'Research',
    'Updates'
]


def get_initials(name):
    """Generates up to two initials from a user's full name."""
    if not name:
        return "??"
    # Split the name, get the first letter of each part, convert to uppercase, and join
    initials = "".join(part[0].upper() for part in name.split()).strip()
    # Return the first two characters
    return initials[:2]

@router.get("/knowledge-hub")
async def get_knowledge_hub(request: Request):
    user_username = request.session.get("username", None)
    if not user_username:
        return RedirectResponse(url="/login", status_code=302)
    else:
        user_access = request.session.get("access_level", None)
        user_position = request.session.get("position", '')
        user_name = request.session.get("name", "Uknknown Person")
        post_access = request.session.get("post_access", False)
        user_initials = get_initials(user_name)
        if user_username:
            return templates.TemplateResponse("knowledge_hub_home.html", {"request": request,
                                                            "user_access": user_access,
                                                            'user_username': user_username,
                                                            'user_position': user_position.lower(),
                                                            'user_name': user_name,
                                                            'user_initials': user_initials,
                                                            'knowledge_categories':knowledge_categories,
                                                            'post_access':post_access
                                                            })
# ---------------- CREATE POST ----------------
@router.post("/knowledge-posts")
async def create_post(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    files: list[UploadFile] = File(None),
    db_con: AsyncSession = Depends(db.get_db)
):
    
    author_username = request.session["username"]
    author = request.session["name"]

    post = KnowledgePost(
        title=title,
        description=description,
        category=category,
        author=author,
        author_username=author_username
    )
    db_con.add(post)
    await db_con.commit()
    await db_con.refresh(post)

    if files:
        post_dir = f"{UPLOAD_DIR}/{post.id}"
        os.makedirs(post_dir, exist_ok=True)

        for file in files:
            path = f"{post_dir}/{file.filename}"
            with open(path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            db_con.add(PostFile(
                post_id=post.id,
                file_name=file.filename,
                file_path=path,
                file_type=file.content_type,
                file_size=os.path.getsize(path)
            ))

        await db_con.commit()

    return {"status": "ok"}


# ---------------- LIST POSTS ----------------
@router.get("/knowledge-posts")
async def list_posts(
    request: Request,
    page: int = 1,
    limit: int = 10,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db_con: AsyncSession = Depends(db.get_db)
):
    try:
        username = request.session.get("username")
        if not username:
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated", "data": []}
            )

        # Load relationships eagerly
        stmt = select(KnowledgePost).options(
            selectinload(KnowledgePost.files),
            selectinload(KnowledgePost.likes),
            selectinload(KnowledgePost.feedbacks)
        ).order_by(KnowledgePost.created_at.desc())

        if category:
            stmt = stmt.where(KnowledgePost.category == category)
        if date_from:
            stmt = stmt.where(KnowledgePost.created_at >= date_from)
        if date_to:
            stmt = stmt.where(KnowledgePost.created_at <= date_to)

        stmt = stmt.offset((page - 1) * limit).limit(limit)

        res = await db_con.execute(stmt)
        posts = res.scalars().unique().all()

        return {
            "data": [
                {
                    "id": p.id,
                    "title": p.title,
                    "description": p.description,
                    "category": p.category,
                    "author": p.author,  # Add author
                    "date": p.created_at.date().isoformat(),
                    "files": [
                        {"id": f.id, "name": f.file_name}
                        for f in p.files
                    ],
                    "likes": len(p.likes),
                    "liked_by_me": any(
                        l.author_username == username for l in p.likes
                    ),
                    "feedbacks": [  # Add feedbacks
                        {
                            "author": fb.author,
                            "text": fb.text,
                            "date": fb.created_at.date().isoformat()
                        }
                        for fb in p.feedbacks
                    ]
                }
                for p in posts
            ]
        }
    except Exception as e:
        print(f"Error in list_posts: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "data": []}
        )


# ---------------- LIKE ----------------
@router.post("/knowledge-posts/{post_id}/like")
async def toggle_like(
    request: Request,
    post_id: int,
    db_con: AsyncSession = Depends(db.get_db)
):
    username = request.session["username"]
    name = request.session["name"]

    like = await db_con.scalar(
        select(PostLike).where(
            PostLike.post_id == post_id,
            PostLike.author_username == username
        )
    )

    if like:
        await db_con.delete(like)
        await db_con.commit()
        return {"liked": False}

    db_con.add(PostLike(post_id=post_id, author_username=username, author=name))
    await db_con.commit()
    return {"liked": True}


# ---------------- FEEDBACK ----------------
@router.post("/knowledge-posts/{post_id}/feedback")
async def add_feedback(
    request: Request,
    post_id: int,
    text: str = Form(...),
    db_con: AsyncSession = Depends(db.get_db)
):
    db_con.add(PostFeedback(
        post_id=post_id,
        text=text,
        author=request.session["name"],
        author_username=request.session["username"]
    ))
    await db_con.commit()
    return {"status": "ok"}


# ---------------- DOWNLOAD ----------------
@router.get("/knowledge-posts/files/{file_id}/download")
async def download_file(
    file_id: int,
    db_con: AsyncSession = Depends(db.get_db)
):
    file = await db_con.get(PostFile, file_id)
    if not file:
        raise HTTPException(404)

    return FileResponse(file.file_path, filename=file.file_name)


# ---------------- DELETE FILE ----------------
@router.delete("/knowledge-posts/files/{file_id}")
async def delete_file(
    request: Request,
    file_id: int,
    db_con: AsyncSession = Depends(db.get_db)
):
    username = request.session["username"]
    file = await db_con.get(PostFile, file_id)
    post = await db_con.get(KnowledgePost, file.post_id)

    if post.author_username != username:
        raise HTTPException(403)

    os.remove(file.file_path)
    await db_con.delete(file)
    await db_con.commit()
    return {"status": "deleted"}