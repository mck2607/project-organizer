import json
from fastapi import APIRouter, HTTPException, Request, Form, UploadFile, File, Depends, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import JSONResponse
from credentials import database as db
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, ForeignKey, update
from sqlalchemy.orm import selectinload
from datetime import datetime, date, timedelta


from models import (QAPosts, QAFiles, QAFeedback, ProjectMaster, ProjectAssignment
                    )

with open("credentials\secret_config.json") as f:
    file_d = json.loads(f.read())
user_data_file_path = file_d['user_data_file_path']

UPLOAD_DIR = f"{user_data_file_path}/qa-uploads"
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


@router.get("/qa-portal")
async def get_qa_portal(request: Request, db_con: AsyncSession = Depends(db.get_db)):
    user_username = request.session.get("username", None)
    if not user_username:
        return RedirectResponse(url="/login", status_code=302)
    else:
        projects = []
        user_access = request.session.get("access_level", None)
        user_position = request.session.get("position", '')
        user_name = request.session.get("name", "Uknknown Person")
        post_access = request.session.get("post_access", False)
        user_initials = get_initials(user_name)
        if user_username:
            queri = await db_con.execute(select(ProjectAssignment).where(ProjectAssignment.assigned_person_username == user_username))
            results = queri.scalars().all()
            if results:
                projects = [db.orm_to_dict(x) for x in results]
            return templates.TemplateResponse("qa_portal.html", {"request": request,
                                                                          "user_access": user_access,
                                                                          'user_username': user_username,
                                                                          'user_position': user_position.lower(),
                                                                          'user_name': user_name,
                                                                          'user_initials': user_initials,
                                                                          'knowledge_categories': knowledge_categories,
                                                                          'post_access': post_access,
                                                                          'projects': projects
                                                                          })


# ---------------- CREATE POST ----------------
@router.post("/qa-posts")
async def create_post_qa(
        request: Request,
        project_name: str = Form(...),
        project_id: str = Form(...),
        description: str = Form(...),
        frequency: str = Form(...),
        task_details: str = Form(...),
        files: list[UploadFile] = File(None),
        db_con: AsyncSession = Depends(db.get_db)
):
    try:
        # Get session data with error handling
        if "username" not in request.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        project_id = int(project_id) if project_id else project_id
        author_username = request.session["username"]
        author = request.session.get("name", author_username)  # Use username as fallback

        # Create post
        post = QAPosts(
            project_name=project_name,
            project_id=project_id,
            description=description,
            frequency=frequency,
            task_details=task_details,
            author=author,
            author_username=author_username
        )

        db_con.add(post)
        await db_con.commit()
        await db_con.refresh(post)
        try:
            stmt = (
                update(ProjectAssignment)
                .where(and_(ProjectAssignment.project_id == project_id, ProjectAssignment.assigned_person_username==author_username))
                .values(
                    qa_iteration_count=ProjectAssignment.qa_iteration_count + 1
                )
            )

            await db_con.execute(stmt)
            await db_con.commit()
        except:
            pass
        # Handle file uploads
        if files:
            post_dir = f"{UPLOAD_DIR}/{post.id}"
            os.makedirs(post_dir, exist_ok=True)

            for file in files:
                try:
                    path = f"{post_dir}/{file.filename}"
                    with open(path, "wb") as f:
                        # Read file content
                        content = await file.read()
                        f.write(content)

                    db_con.add(QAFiles(
                        post_id=post.id,
                        file_name=file.filename,
                        file_path=path,
                        file_type=file.content_type,
                        file_size=os.path.getsize(path)
                    ))
                except Exception as file_error:
                    print(f"Error processing file {file.filename}: {str(file_error)}")
                    # Continue with other files

            await db_con.commit()

        return {"status": "ok", "post_id": post.id}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the full error for debugging
        print(f"Error creating QA post: {str(e)}")
        # Return a proper JSON error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create QA post"
        )


# ---------------- LIST POSTS ----------------
@router.get("/qa-posts")
async def list_posts_qa(
        request: Request,
        page: int = 1,
        limit: int = 10,
        frequency: str | None = None,
        project_name: str | None = None,
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
        stmt = select(QAPosts).options(
            selectinload(QAPosts.qa_files),  # Fixed: should be qa_files (plural)
            selectinload(QAPosts.qa_feedbacks)  # Fixed: should be qa_feedbacks (plural)
        ).order_by(QAPosts.created_at.desc())

        if frequency:
            stmt = stmt.where(QAPosts.frequency == frequency)
        if project_name:
            stmt = stmt.where(QAPosts.project_name == project_name)
        if date_from:
            stmt = stmt.where(QAPosts.created_at >= date_from)
        if date_to:
            # Make sure to include the entire day
            stmt = stmt.where(QAPosts.created_at <= date_to + timedelta(days=1))

        # Get total count for pagination
        count_stmt = select(func.count()).select_from(QAPosts)
        total_result = await db_con.execute(count_stmt)
        total = total_result.scalar()

        # Apply pagination
        stmt = stmt.offset((page - 1) * limit).limit(limit)

        res = await db_con.execute(stmt)
        posts = res.scalars().unique().all()

        # Process posts for frontend
        posts_data = []
        for p in posts:
            post_data = {
                "id": p.id,
                "title": p.project_name,  # Frontend expects 'title'
                "description": p.description,
                "category": p.frequency,  # Frontend expects 'category' (not frequency)
                "author": p.author,
                "date": p.created_at.strftime("%Y-%m-%d"),  # Formatted date
                "task_details": p.task_details,
                "files": [
                    {
                        "id": f.id,
                        "name": f.file_name,
                        "type": f.file_type,
                        "size": f.file_size
                    }
                    for f in p.qa_files
                ] if p.qa_files else [],
                "feedbacks": [
                    {
                        "id": fb.id,
                        "author": fb.author,
                        "text": fb.text,
                        "date": fb.created_at.strftime("%Y-%m-%d")
                    }
                    for fb in p.qa_feedbacks
                ] if p.qa_feedbacks else []
            }
            posts_data.append(post_data)

        return {
            "data": posts_data,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit  # Ceiling division
        }

    except Exception as e:
        logger.error(f"Error in list_posts_qa: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to load posts",
                "data": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "pages": 0
            }
        )


# # ---------------- LIKE ----------------
# @router.post("/knowledge-posts/{post_id}/like")
# async def toggle_like(
#         request: Request,
#         post_id: int,
#         db_con: AsyncSession = Depends(db.get_db)
# ):
#     username = request.session["username"]
#     name = request.session["name"]
#
#     like = await db_con.scalar(
#         select(PostLike).where(
#             PostLike.post_id == post_id,
#             PostLike.author_username == username
#         )
#     )
#
#     if like:
#         await db_con.delete(like)
#         await db_con.commit()
#         return {"liked": False}
#
#     db_con.add(PostLike(post_id=post_id, author_username=username, author=name))
#     await db_con.commit()
#     return {"liked": True}


# ---------------- FEEDBACK ----------------
@router.post("/qa-posts/{post_id}/feedback")
async def add_feedback_qa(
        request: Request,
        post_id: int,
        text: str = Form(...),
        db_con: AsyncSession = Depends(db.get_db)
):
    db_con.add(QAFeedback(
        post_id=post_id,
        text=text,
        author=request.session["name"],
        author_username=request.session["username"]
    ))
    await db_con.commit()
    return {"status": "ok"}


# ---------------- DOWNLOAD ----------------
@router.get("/qa-posts/files/{file_id}/download")
async def download_file_qa(
        file_id: int,
        db_con: AsyncSession = Depends(db.get_db)
):
    file = await db_con.get(QAFiles, file_id)
    if not file:
        raise HTTPException(404)

    return FileResponse(file.file_path, filename=file.file_name)


# ---------------- DELETE FILE ----------------
@router.delete("/qa-posts/files/{file_id}")
async def delete_file_qa(
        request: Request,
        file_id: int,
        db_con: AsyncSession = Depends(db.get_db)
):
    username = request.session["username"]
    file = await db_con.get(QAFiles, file_id)
    post = await db_con.get(QAPosts, file.post_id)

    if post.author_username != username:
        raise HTTPException(403)

    os.remove(file.file_path)
    await db_con.delete(file)
    await db_con.commit()
    return {"status": "deleted"}


# @router.get("/api/user/projects")
# async def get_user_projects(
#         request: Request,
#         db_con: AsyncSession = Depends(db.get_db)
# ):
#     if "username" not in request.session:
#         raise HTTPException(status_code=401, detail="Not authenticated")
#
#     username = request.session["username"]
#
#     # Query projects where user is assigned or has access
#     query = text("""
#         SELECT p.project_id, p.project_name, p.status, p.frequency_type
#         FROM projects p
#         WHERE p.assigned_to = :username
#            OR p.created_by = :username
#            OR EXISTS (
#                SELECT 1 FROM working_developers_details w
#                WHERE w.project_id = p.project_id
#                AND w.assigned_person_username = :username
#            )
#         ORDER BY p.created_at DESC
#     """)
#
#     result = await db_con.execute(query, {"username": username})
#     projects = result.fetchall()
#
#     return [
#         {
#             "project_id": row[0],
#             "project_name": row[1],
#             "status": row[2],
#             "frequency_type": row[3]
#         }
#         for row in projects
#     ]