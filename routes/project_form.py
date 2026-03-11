import json
from fastapi import APIRouter, Request, Form, UploadFile, File, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import JSONResponse
from credentials import database as db
import os
from sqlalchemy.ext.asyncio import AsyncSession
from models import Employee, ProjectAssignment, ProjectMaster
from typing import Optional, List
from sqlalchemy import select
import shutil
from datetime import datetime

with open("credentials\secret_config.json") as f:
    file_d = json.loads(f.read())
user_data_file_path = file_d['user_data_file_path']

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/project-form")
async def project_submit(request: Request, db_con : AsyncSession = Depends(db.get_db)):
    username = request.session.get("username", None)
    position = request.session.get("position", None)
    user_access_level = request.session.get("access_level", 'level4')
    if not username:
        return RedirectResponse(url="/", status_code=302)
    if user_access_level == "level2" or "sales" in position.lower():
        result = await db_con.execute(select(Employee).where(Employee.username == username))
        user_details = result.scalars().first()
        user_details = db.orm_to_dict(user_details)
        if "sales" in position.lower():
            stmt = (
                select(Employee.username,
                       Employee.email,
                       Employee.name,
                       Employee.position
                       )
                .where(Employee.position.ilike("%Project Manager%"))
            )
            result2 = await db_con.execute(stmt)
        else:
            stmt = (
                select(Employee.username,
                       Employee.email,
                       Employee.name,
                       Employee.position
                       )
                .where(Employee.reporting_person_username == username)
            )
            result2 = await db_con.execute(stmt)
        persons = result2.mappings().all()
        return templates.TemplateResponse("project_form.html", {"request": request, "user":user_details, 'developers':persons})
    else:
        return RedirectResponse(url="/", status_code=302)


@router.post("/project-form-submit")
async def project_submit_form(
    request: Request,
    project_name: str = Form(...),
    project_assigner_name: str = Form(...),
    project_assigner_email: str = Form(...),
    project_assigner_username: str = Form(...),
    assigned_person_username: str = Form(...),
    project_assigner_position: str = Form(...),
    expected_date_time: str = Form(...),
    estimated_date_time: str = Form(...),
    platform_type: str = Form(...),
    frequency_type: str = Form(...),
    project_state: str = Form(...),
    project_key_points: str = Form(...),
    project_files: Optional[List[UploadFile]] = File(None),
    project_videos: Optional[List[UploadFile]] = File(None),
    db_con : AsyncSession = Depends(db.get_db)
    ):
    project_key_points = project_key_points.replace("\n", '').split("||")
    file_paths = []
    video_paths = []
    # -------- Save multiple files --------
    if project_files:
        file_dir = os.path.join(user_data_file_path, "PROJECT_DOCUMENTS")
        os.makedirs(file_dir, exist_ok=True)
        for file in project_files:
            if file and file.filename:
                file_path = os.path.join(file_dir, file.filename)
                with open(file_path, "wb") as f:
                    shutil.copyfileobj(file.file, f)
                file_paths.append(file_path)

    # -------- Save multiple videos --------
    if project_videos:
        video_dir = os.path.join(user_data_file_path, "PROJECT_VIDEOS")
        os.makedirs(video_dir, exist_ok=True)
        for video in project_videos:
            if video and video.filename:
                video_path = os.path.join(video_dir, video.filename)
                with open(video_path, "wb") as f:
                    shutil.copyfileobj(video.file, f)
                video_paths.append(video_path)
    deadline_date_time = estimated_date_time.replace("T", ' ').strip()
    expected_date_time = expected_date_time.replace("T", ' ').strip()
    estimated_date = str(datetime.strptime(deadline_date_time, "%Y-%m-%d %H:%M"))
    expected_date_time = str(datetime.strptime(expected_date_time, "%Y-%m-%d %H:%M")) if expected_date_time or expected_date_time != '' else " "
    project_create_date = str(datetime.now().strftime("%Y-%m-%d %H:%M"))
    # project_id = db.hash_string(input_string=f"{project_name}{project_create_date}")
    key_points_json = json.dumps(project_key_points)  # ✅ save list as JSON
    file_paths_json = json.dumps(file_paths)  # ✅ save list as JSON
    video_paths_json = json.dumps(video_paths)  # ✅ save list as JSON
    # Insert into DB
    resu = await db_con.execute(select(Employee).where(Employee.username == str(assigned_person_username)))
    to_dev_details = resu.scalars().first()
    new_recor = ProjectMaster(
        project_name=project_name,
        project_estimated_date_time =estimated_date,
        project_expected_date_time =expected_date_time,
        frequency_type =frequency_type,
        platform_type =platform_type,
        project_key_points =key_points_json,
        document_file =file_paths_json,
        videos =video_paths_json,
        project_created_date=project_create_date,
        project_state=project_state
    )
    db_con.add(new_recor)
    await db_con.commit()
    await db_con.refresh(new_recor)
    project_id = new_recor.project_id
    insert_assign = ProjectAssignment(
        project_id=project_id,
        project_name = project_name,
        assigned_person_name = to_dev_details.name,
        task_detail = "-",
        assigned_person_email= to_dev_details.email,
        assigned_person_username = to_dev_details.username,
        assigned_person_position = to_dev_details.position,
        project_assigner_position = project_assigner_position,
        project_assigner_name = project_assigner_name,
        project_assigner_email = project_assigner_email,
        person_assigner_username = project_assigner_username,
        assigning_date = project_create_date
    )
    db_con.add(insert_assign)
    await db_con.commit()
    return JSONResponse({"success": True, "message": "Data uploaded successfully!"})

