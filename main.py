import os, json
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Form, UploadFile, File, HTTPException, Depends
from fastapi import Request
from models import TodoMaster, TodoAssignment
from sqlalchemy import select, update, and_
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, HTMLResponse, JSONResponse
from starlette.status import HTTP_303_SEE_OTHER
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import uvicorn
# custom files imports & classes...................................
from routes import auth, project_form, cummnication, dashboard, too_routes, knowledge, qa_routes, notification
from models import Employee, ProjectCodebase, ProjectAssignment
from credentials import database as db


# this file you have to make.
with open(r"credentials\secret_config.json") as f:
    file_d = json.loads(f.read())
secret_key= file_d['secret_key']
user_data_file_path = file_d['user_data_file_path']
static_file_path = file_d['static_file_path']
os.makedirs(user_data_file_path, exist_ok=True)
os.makedirs(static_file_path, exist_ok=True)
# app configs.......
app = FastAPI(debug=True)
app.include_router(auth.router, tags=['Auth'])
app.include_router(dashboard.router, tags=['Home & Dashboard'])
app.include_router(project_form.router, tags=['Project Form'])
app.include_router(cummnication.router, tags=['Project Updates'])
app.include_router(too_routes.router, tags=['Todo Routes'])
app.include_router(knowledge.router, tags=['knowledge Routes'])
app.include_router(qa_routes.router, tags=['QA Routes'])
app.include_router(notification.router, tags=['Notifications Routes'])
templates = Jinja2Templates(directory="templates")
app.mount(f'/{static_file_path}', StaticFiles(directory="static"), name="static")
app.mount(f'/{user_data_file_path}', StaticFiles(directory="USER_DATA"), name="images")

app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key,
    max_age=86400,  # 1 day in seconds
    # https_only=True,  # Only send over HTTPS
    path="/",  # Cookie available across the whole app
)


def get_initials(name):
    """Generates up to two initials from a user's full name."""
    if not name:
        return "??"
    # Split the name, get the first letter of each part, convert to uppercase, and join
    initials = "".join(part[0].upper() for part in name.split()).strip()
    # Return the first two characters
    return initials[:2]


@app.get("/")
async def home_page(request: Request, db_con : AsyncSession = Depends(db.get_db)):
    user_username = request.session.get("username", None)
    if not user_username:
        return RedirectResponse(url="/login", status_code=302)
    else:
        user_access = request.session.get("access_level", None)
        user_position = request.session.get("position", '')
        user_name = request.session.get("name", None)
        user_initials = get_initials(user_name)
        # Fetch todos
        assigned_to_query = (
            select(
                TodoAssignment.id,
                TodoMaster.todo_title,
                TodoMaster.todo_descr,
                TodoMaster.priority,
                TodoMaster.color,
                TodoAssignment.assignee_username,
                TodoAssignment.project_id,
                TodoAssignment.project_name,
                TodoAssignment.todo_created_date,
                TodoAssignment.todo_completed_date,
                TodoAssignment.status,
            )
            .join(TodoMaster, TodoAssignment.todo_id == TodoMaster.id)
            .where(and_(
                TodoAssignment.assignee_username == user_username,
                TodoAssignment.show_or_not == True
            ))
            .order_by(TodoAssignment.todo_created_date.desc())
        )
        result = await db_con.execute(assigned_to_query)
        todos = result.mappings().all()
        return templates.TemplateResponse("home.html",
        {"request": request,
            "user_access": user_access,
            'user_username': user_username,
            'user_position': user_position.lower(),
            'user_name': user_name,
            'user_initials': user_initials,
            "todos": todos
        })

@app.get("/profile/{user_username}")
async  def profile_page(request:Request, 
                        user_username: str=None,
                        db_con : AsyncSession = Depends(db.get_db),
                        ):
    username = request.session.get('username', "unknown")
    user_access_level = request.session.get('access_level', "unknown")
    user = {}
    if not username:
        return RedirectResponse(url="/login", status_code=302)
    if user_access_level == "level1":
        result = await db_con.execute(select(Employee).where(Employee.username == user_username))
        user = result.scalars().first()
    elif user_username == username:
        result = await db_con.execute(select(Employee).where(Employee.username == username))
        user = result.scalars().first()
    if not user:
        return templates.TemplateResponse("profile.html", {"request": request, "user": {}})
    if user:
        return templates.TemplateResponse("profile.html", {"request": request, "user": user})

@app.get("/all_employee", response_class=HTMLResponse)
async def all_em(request:Request, db_con : AsyncSession = Depends(db.get_db)):
    username = request.session.get("username", None)
    user_access_level = request.session.get("access_level", None)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    if user_access_level == 'level1':
        user = await db_con.execute(select(Employee))
        user = user.scalars().all()
        return templates.TemplateResponse("all_employee.html", {"request": request, "developers": user})
    else:
        return RedirectResponse(url="/", status_code=302)
    
@app.get("/update_profile_huhh/{employee_id}")
async  def profile_page(request:Request, employee_id:str=None, db_con : AsyncSession = Depends(db.get_db)):
    username = request.session.get("username", None)
    user_access_level = request.session.get("access_level", None)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    if user_access_level == 'level1':
        res = await db_con.execute(select(Employee).where(Employee.username == employee_id))
        user = res.scalars().first()
        return templates.TemplateResponse("edit_profile.html", {"request": request, "user": user})
    else:
        res = await db_con.execute(select(Employee).where(Employee.username == username))
        user = res.scalars().first()
        return templates.TemplateResponse("edit_profile.html", {"request": request, "user": user})



@app.post("/update_profile2")
async def update_profile2(
    request: Request,
    username: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    position: str = Form(...),
    department: str = Form(...),
    reporting_person_name: str = Form(None),
    reporting_person_position: str = Form(None),
    reporting_person_email: str = Form(None),
    reporting_person_username: str = Form(None),
    db_con : AsyncSession = Depends(db.get_db)
):
    stmt = (
            update(Employee)
            .where(Employee.username == username)
            .values(
                name=name,
                email=email,
                phone=phone,
                position=position,
                department=department,
                reporting_person_name=reporting_person_name,
                reporting_person_email=reporting_person_email,
                reporting_person_position=reporting_person_position,
                reporting_person_username=reporting_person_username
            )
            )
    await db_con.execute(stmt)
    await db_con.commit() 
    return RedirectResponse(url="/all_employee", status_code=HTTP_303_SEE_OTHER)


@app.get("/code-area/{project_name}/{project_id}/{task_detail}")
async def get_upload_code(request:Request, 
                    project_id:str=None, 
                    project_name:str=None,
                    task_detail:str=None,
                    db_con : AsyncSession = Depends(db.get_db)):
    username = request.session.get("username", None)
    user_access_level = request.session.get("access_level", None)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    res = await db_con.execute(select(Employee).where(Employee.username == username))
    user = res.scalars().first()
    if user:
        user = db.orm_to_dict(user)
        user['project_id'] = project_id
        user['project_name'] = project_name
        user['task_detail'] = task_detail
        if user_access_level == "level4":
                return templates.TemplateResponse("upload_code.html", {"request": request, "user":user})
    else:
        return RedirectResponse(url="/", status_code=302)


@app.post("/upload-code")
async def upload_code(
    project_id: str = Form(...),
    project_name: str = Form(...),
    user_name: str = Form(...),
    task_detail: str = Form(...),
    user_id: str = Form(...),
    project_zip: UploadFile = File(...),
    db_con : AsyncSession = Depends(db.get_db)
):
    upload_code_path = f"{user_data_file_path}/CODEBASE"
    os.makedirs(upload_code_path, exist_ok=True)
    folder_time = str(datetime.now().strftime('%Y_%m_%d_%H_%M_%S'))
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not project_zip.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files allowed.")
    contents = await project_zip.read()
    if len(contents) > 2 * 1024 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (>2GB).")
    user_folder = os.path.join(upload_code_path, f"{user_id}/{project_name}/{folder_time}")
    os.makedirs(user_folder, exist_ok=True)
    file_path = os.path.join(user_folder, project_zip.filename)
    with open(file_path, "wb") as f:
        f.write(contents)
    new_record_codebase = ProjectCodebase(
        code_submit_person_username = user_id,
        code_submit_person_name = user_name,
        codebase_submit_date = current_date,
        code_file = file_path,
        project_id = project_id,
        project_name = project_name,
        task_detail = task_detail,
    )
    db_con.add(new_record_codebase)
    await db_con.commit()
    try:
        stmt = (
            update(ProjectAssignment)
            .where(and_(ProjectAssignment.assigned_person_username == user_id ,
                        ProjectAssignment.project_id == project_id))
            .values(
               code_uploaded="true"
            )
        )
        await db_con.execute(stmt)
        await db_con.commit()
    except:
        pass
    return JSONResponse({"message": "🎉 Project uploaded successfully!"})


if __name__ == '__main__':
    uvicorn.run("main:app",port=1111, host="172.27.131.168", reload=True)