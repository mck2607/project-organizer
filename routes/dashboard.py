import json
import os
import shutil
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.exc import IntegrityError
from models import Employee, ProjectMaster,ProjectAssignment, ProjectData, ProjectUpdates
from datetime import datetime
from typing import List, Union, Optional
from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from starlette.responses import JSONResponse
from credentials import database as db


with open("credentials\secret_config.json") as f:
    file_d = json.loads(f.read())
user_data_file_path = file_d['user_data_file_path']

templates = Jinja2Templates(directory="templates")
router = APIRouter()

@router.get("/dashboard")
async def dashboard(request: Request, db_con: AsyncSession = Depends(db.get_db)):
    employee_username = request.session.get('username')
    employee_position = request.session.get("position", '')
    employee_access_level = request.session.get("access_level", 'level4')

    if not employee_username:
        return RedirectResponse(url="/", status_code=302)

    employee_name = request.session.get('name', "Unknown")

    # Developers under this manager
    dev_query = await db_con.execute(
        select(Employee).where(Employee.reporting_person_username == employee_username)
    )
    developers = dev_query.scalars().all()

    # =========================
    # PROJECT QUERY
    # =========================
    if employee_access_level in ['level2', 'level3', 'level1'] and "sale" not in employee_position.lower():
        # Assigned TO me OR Assigned BY me
        query = (
            select(
                ProjectAssignment.project_id,
                ProjectAssignment.project_name,
                ProjectAssignment.task_detail,
                ProjectAssignment.project_progress,
                ProjectAssignment.code_uploaded,
                ProjectAssignment.qa_iteration_count,
                ProjectMaster.frequency_type,
                ProjectMaster.platform_type,
                ProjectMaster.project_key_points,
                ProjectMaster.document_file,
                ProjectMaster.videos,
                ProjectMaster.project_created_date,
                ProjectMaster.project_state,
            )
            .join(ProjectMaster, ProjectAssignment.project_id == ProjectMaster.project_id)
            .where(
                or_(
                    ProjectAssignment.assigned_person_username == employee_username,
                    ProjectAssignment.person_assigner_username == employee_username,
                )
            )
        )
    else:
        # Developer – only assigned to me
        query = (
            select(
                ProjectAssignment.project_id,
                ProjectAssignment.project_name,
                ProjectAssignment.task_detail,
                ProjectAssignment.project_progress,
                ProjectAssignment.code_uploaded,
                ProjectAssignment.qa_iteration_count,
                ProjectMaster.frequency_type,
                ProjectMaster.platform_type,
                ProjectMaster.project_key_points,
                ProjectMaster.document_file,
                ProjectMaster.videos,
                ProjectMaster.project_created_date,
                ProjectMaster.project_state,
            )
            .join(ProjectMaster, ProjectAssignment.project_id == ProjectMaster.project_id)
            .where(ProjectAssignment.assigned_person_username == employee_username)
        )

    result = await db_con.execute(query)
    rows = result.mappings().all()

    # =========================
    # FORCE UNIQUE PROJECTS
    # =========================
    project_map = {}  # project_id -> project data

    for row in rows:
        pid = row["project_id"]

        if pid not in project_map:
            project = dict(row)

            # JSON parsing (once per project)
            if project.get("project_key_points"):
                project["project_key_points"] = json.loads(project["project_key_points"])

            if project.get("document_file"):
                project["document_file"] = json.loads(project["document_file"])

            if project.get("videos"):
                project["videos"] = json.loads(project["videos"])

            project_map[pid] = project

    unique_projects = list(project_map.values())

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "name": employee_name,
            "projects": unique_projects,
            "developers": developers,
            "access_level": employee_access_level,
            "employee_username": employee_username,
        }
    )



@router.post("/assign-project")
async def assign_project_direct(
    project_id: str = Form(...),
    developer_id: str = Form(...),
    task_detail: str = Form(...),
    assigner_username: str = Form(...),
    db_con: AsyncSession = Depends(db.get_db)
):
    # Developer
    dev_q = await db_con.execute(select(Employee).where(Employee.username == developer_id))
    developer = dev_q.scalars().first()

    # Assigner
    assigner_q = await db_con.execute(select(Employee).where(Employee.username == assigner_username))
    assigner = assigner_q.scalars().first()

    if not developer:
        return JSONResponse(status_code=404, content={"assigned": False, "message": "Developer not found"})
    # Project Fetch
    project_id = int(project_id) if project_id else project_id
    pro_q = await db_con.execute(select(ProjectMaster).where(ProjectMaster.project_id == project_id))
    project_info = pro_q.scalars().first()
    if not project_info:
        pro_q = await db_con.execute(select(ProjectData).where(ProjectData.project_id == project_id))
        project_info = pro_q.scalars().first()
    try:
        insert_record = ProjectAssignment(
            project_id=project_id,
            project_name=project_info.project_name,
            task_detail=task_detail,
            assigned_person_name=developer.name,
            assigned_person_email=developer.email,
            assigned_person_username=developer.username,
            assigned_person_position=developer.position,
            project_assigner_position=assigner.position,
            project_assigner_name=assigner.name,
            project_assigner_email=assigner.email,
            person_assigner_username=assigner_username,
            assigning_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        db_con.add(insert_record)
        await db_con.commit()
        return JSONResponse(status_code=200, content={"assigned": True, "message": "✅ Project assigned successfully"})
    except IntegrityError:
        return JSONResponse(status_code=400, content={"assigned": False, "message": "Already assigned"})


@router.get("/info_project/{project_id}")
async def info_project(request: Request, project_id: str, db_con: AsyncSession = Depends(db.get_db)):
    employee_username = request.session.get('username', None)
    employee_position = request.session.get('position', " ")
    employee_name = request.session.get('name', "Unknown")
    if not employee_username:
        return RedirectResponse(url="/", status_code=302)
    project_id = int(project_id)
    que_p = await db_con.execute(select(ProjectData).where(ProjectData.project_id == project_id))
    projects = que_p.scalars().first()
    if not projects:
        que_p = await db_con.execute(select(ProjectMaster).where(ProjectMaster.project_id == project_id))
        projects = que_p.scalars().first()
    if projects:
        projects = db.orm_to_dict(projects)
        if projects["project_key_points"]:
            projects['project_key_points'] = json.loads(projects["project_key_points"])
        if projects["document_file"]:
            projects['document_file'] = json.loads(projects["document_file"])
        if projects["videos"]:
            projects['videos'] = json.loads(projects["videos"])
    if employee_position.lower() == "project coordinator":
        dev_q = (select(Employee).where(
            Employee.position.in_([
                "python developer consultant",
                "senior python developer",
                "team leader"
            ]),Employee.department == "operation"))
    else:
        dev_q = (select(Employee).where(Employee.reporting_person_username == employee_username))
    dev_ne = await db_con.execute(dev_q)
    developer_orm_objects = dev_ne.scalars().all()
    developers = [db.orm_to_dict(x) for x in developer_orm_objects]
    w_dev_q = await db_con.execute(select(ProjectAssignment).where(ProjectAssignment.project_id == project_id))
    working_developers_details = [db.orm_to_dict(row) for row in w_dev_q.scalars().all()]
    progress = projects.get('project_progress', 0) if projects else 0
    return templates.TemplateResponse("info_project.html", {
        "request": request,
        "user": {
            'name':employee_name,
            'position':employee_position,
            'username':request.session.get('username'),
            'access_level':request.session.get('access_level')
        },
        "project": projects,
        "project_id": project_id,
        "project_name": projects.get('project_name', '') if projects else '',
        "progress": progress,
        "developers": developers,
        "files": projects['document_file'],
        'working_developers_details':working_developers_details,
    })

@router.get("/download_doc/{project_id}")
async def download_doc(request: Request,project_id: str, file: str,db_con: AsyncSession = Depends(db.get_db)):
    if not request.session.get('username', None):
        return RedirectResponse(url="/", status_code=302)
    doc_path = file
    if os.path.exists(doc_path):
        return FileResponse(
            path=doc_path,
            filename=os.path.basename(doc_path),
            media_type="application/octet-stream"
        )
    else:
        return {"error": "File not found"}

@router.get("/project-level/{project_id}")
async def gaming_progress(request:Request, project_id:str=None, db_con: AsyncSession = Depends(db.get_db)):
    username = request.session.get('username', None)
    user_position = request.session.get('position', None)
    project_id = int(project_id) if project_id else project_id
    if not username and not project_id:
        return RedirectResponse(url="/", status_code=302)
    if "developer" in str(user_position).lower() or "consultant" in str(user_position).lower():
        allowed = True
    else:
        allowed = False
    que = await db_con.execute(select(ProjectAssignment).where(and_(ProjectAssignment.project_id == project_id , ProjectAssignment.assigned_person_username == username)))
    project = que.scalars().first()
    if project:
        project = db.orm_to_dict(project)
        project_pr = int(project.get('project_progress', 0))
        progress_map = {
            0:None,
            20:"step-1",
            40:"step-2",
            60:"step-3",
            70:"step-4",
            100:"step-5",
        }
        return templates.TemplateResponse("gaming_progress.html", {
            "request": request,
            'project_id': project_id,
            "step": progress_map.get(project_pr),
            "progress": project_pr,
            "allowed":allowed,
            'username':username
        })
    else:
        return templates.TemplateResponse("gaming_progress.html", {
            "request": request,
            'project_id': project_id,
            "step": {},
            "progress":None,
            "allowed": False,
            'username': username
        })

@router.get("/gaming-zone/{project_progress}/{project_id}/{username}")
async def update_project_progress(project_progress: str =None,
                                  project_id: str =None,
                                  username:str=None,
                                  db_con: AsyncSession = Depends(db.get_db)):
    try:
        project_id = int(project_id) if project_id else project_id
        query_project_info = await db_con.execute(select(ProjectMaster).where(ProjectMaster.project_id == project_id))
        project_de = query_project_info.scalars().first()
        if not project_de:
            query_project_info = await db_con.execute(
                select(ProjectMaster).where(ProjectData.project_id == project_id))
            project_de = query_project_info.scalars().first()
        if project_de:
            project_de = db.orm_to_dict(project_de)
        current_time_date = str(datetime.now().strftime("%Y-%m-%d %H:%M"))
        stmt = (update(ProjectAssignment)
                .where(and_(
                        ProjectAssignment.project_id == project_id,
                       ProjectAssignment.assigned_person_username == username)
                )
                .values(
            project_progress = project_progress,
            last_activity_date = current_time_date
        ))
        await db_con.execute(stmt)
        await db_con.commit()
        if project_progress == "100":
            db_time = datetime.strptime(project_de['project_expected_date_time'], "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            time_difference = now - db_time
            difference_in_minutes = int(time_difference.total_seconds() / 60)
            try:
                stmt = (update(ProjectAssignment)
                        .where(and_(ProjectAssignment.project_id == project_id,
                               ProjectAssignment.assigned_person_username == username))
                        .values(
                    project_delay_in_minutes = difference_in_minutes
                )
                        )
                await db_con.execute(stmt)
            except:
                pass
            try:
                stmt = (update(ProjectMaster)
                        .where(ProjectMaster.project_id == project_id)
                        .values(status='done')
                        )
                await db_con.execute(stmt)
            except:
                pass
            try:
                stmt = (update(ProjectData)
                        .where(ProjectData.project_id == project_id)
                        .values(status='done')
                        )
                await db_con.execute(stmt)
            except:
                pass
        await db_con.commit()
        return JSONResponse(status_code=200, content={"success": True, "message": "Level Upgraded successfully !"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"success": False, "message": f"Something went wrong: {e}"})


@router.get("/projects_all")
async def projects_all_show(request:Request,
                            db_con: AsyncSession = Depends(db.get_db)):
    username = request.session.get('username', None)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    query_project_info = await db_con.execute(select(ProjectMaster))
    data = query_project_info.scalars().all()
    if data:
        column = db.orm_to_dict(data[0]).keys()
        return templates.TemplateResponse("all_projects.html", {'request':request, 'data':data, 'column':column})
    else:
        return templates.TemplateResponse("all_projects.html", {'request': request})


@router.get("/view-form-project/{project_id}")
async def reccursive_project(request:Request, project_id:str=None, db_con: AsyncSession = Depends(db.get_db)):
    username = request.session.get('username', None)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    project_id = int(project_id) if project_id else project_id
    query_pr = await db_con.execute(select(ProjectMaster).where(ProjectMaster.project_id == project_id))
    data = query_pr.scalars().first()
    if not data:
        query_pr = await db_con.execute(select(ProjectData).where(ProjectData.project_id == project_id))
        data = query_pr.scalars().first()
    if data:
        return templates.TemplateResponse("reccursive_project_form.html", {'request':request, 'details':data})



@router.post("/reassign-project-form-submit", response_class=HTMLResponse)
async def project_submit_form_reassign(
    project_name: str = Form(...),
    project_assigner_email: str = Form(...),
    assigned_person_email: str = Form(...),
    start_date_time: str = Form(...),
    platform_type: str = Form(...),
    frequency_type: str = Form(...),
    expected_date_time: str = Form(...),
    estimated_date_time: str = Form(...),
    project_description: str = Form(...),
    project_key_points: str = Form(...),
    project_files: Optional[UploadFile] = File(None),
    project_videos: Optional[UploadFile] = File(None),
    db_con: AsyncSession = Depends(db.get_db)
    ):
    key_points_json = json.dumps(project_key_points)
    deadline_date_time = estimated_date_time.replace("T", ' ').strip()
    expected_date_time = expected_date_time.replace("T", ' ').strip()
    estimated_date = datetime.strptime(deadline_date_time, "%Y-%m-%d %H:%M")
    expected_date_time = datetime.strptime(expected_date_time, "%Y-%m-%d %H:%M") if expected_date_time or expected_date_time != '' else " "
    file_path = None
    video_path = None
    if project_files and project_files.filename:
        file_dir = os.path.join(user_data_file_path, "PROJECT_DOCUMENTS")
        os.makedirs(file_dir, exist_ok=True)
        file_path = os.path.join(file_dir, project_files.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(project_files.file, f)
    if project_videos and project_videos.filename:
        video_dir = os.path.join(user_data_file_path, "PROJECT_VIDEOS")
        os.makedirs(video_dir, exist_ok=True)
        video_path = os.path.join(video_dir, project_videos.filename)
        with open(video_path, "wb") as f:
            shutil.copyfileobj(project_videos.file, f)
    project_create_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    # Insert into DB
    # Assigned person details.
    query_dev = await db_con.execute(select(Employee).where(Employee.email == assigned_person_email))
    assigned_person_data = query_dev.scalars().first()
    # project assigner details.
    query_dev_as = await db_con.execute(select(Employee).where(Employee.email == project_assigner_email))
    project_assigner_data = query_dev_as.scalars().first()
    assigned_person_username = assigned_person_data['username'] if assigned_person_data else "N/A"
    assigned_person_name = assigned_person_data['name'] if assigned_person_data else "N/A"
    project_assigner_position = project_assigner_data['position']
    project_assigner_name = project_assigner_data['name']
    project_assigner_username = project_assigner_data['username']
    new_project_insert = ProjectData(
        project_name = project_name,
        project_estimated_date_time=estimated_date,
        project_expected_date_time=expected_date_time,
        project_start_date_time=start_date_time,
        frequency_type=frequency_type,
        platform_type= platform_type,
        project_key_points=key_points_json,
        document_file=file_path,
        videos=video_path,
        project_created_date=project_create_date,
        project_state=True,
    )
    await db_con.execute(new_project_insert)
    await db_con.commit()
    project_id = new_project_insert.project_id
    insert_assign = ProjectAssignment(
        project_id=project_id,
        project_name=project_name,
        assigned_person_name=assigned_person_name,
        assigned_person_email=assigned_person_email,
        assigned_person_username=assigned_person_username,
        project_assigner_position=project_assigner_position,
        project_assigner_name=project_assigner_name,
        project_assigner_email=project_assigner_email,
        person_assigner_username=project_assigner_username,
        assigning_date=project_create_date,
    )
    await db_con.execute(insert_assign)
    await db_con.commit()
    return JSONResponse(status_code=200,content={
        "message": "Form submitted successfully!",
        "project_name": project_name,
        "project_description": project_description
    })


@router.get("/all-developer-project-to-do")
async def developer_dashboard_projects(request: Request):
    position = request.session.get("position", None)
    username = request.session.get('username', None)
    if not position and not username:
        return RedirectResponse(url="/", status_code=302)
    position = str(position)
    if "manager" in position.lower() or "team leader" in position.lower():
        return templates.TemplateResponse("developer_project_dashboard.html", {'request': request, 'head_person_id':username})
    else:
        return RedirectResponse(url="/", status_code=302)

@router.get("/developers-projects-see/{head_person_id}")
async def html_view_dashboard_dev_project(head_person_id:str=None, db_con: AsyncSession = Depends(db.get_db)):
    basic_st = None
    if not head_person_id:
        return RedirectResponse(url="/", status_code=302)
    try:
        head_query = await db_con.execute(select(Employee).where(Employee.username == head_person_id))
        head_person_details = head_query.scalars().first()
        assi_que = await db_con.execute(
            select(Employee).where(Employee.reporting_manager_username == head_person_details['username']))
        assigned_devs = assi_que.scalars().all()
        basic_st = []
        for dev in assigned_devs:
            temp_dict = {}
            temp_dict['id'] = dev['username']
            temp_dict['name'] = dev['name']
            temp_dict['projects'] = []
            basic_st.append(temp_dict)
        for dev2 in basic_st:
            proj_que = await db_con.execute(
                select(ProjectAssignment).where(ProjectAssignment.assigned_person_username == dev2['id']))
            projects = proj_que.scalars().all()
            for pr in projects:
                temp_pro = {}
                temp_pro['name'] = pr['project_name']
                temp_pro['status'] = pr['project_progress']
                dev2['projects'].append(temp_pro)
        return JSONResponse(status_code=200, content=basic_st)
    except Exception as e:
        return JSONResponse(status_code=400, content=basic_st)


