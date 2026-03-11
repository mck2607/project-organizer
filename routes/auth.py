from fastapi import APIRouter, Request, Form, File, UploadFile, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from credentials import database as db
from datetime import datetime
import pandas as pd
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from models import Employee, LoginLog

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/add-user", response_class=HTMLResponse)
async def add_user_popup(request: Request):
    username = request.session.get('username', None)
    use_access_level = request.session.get('access_level', None)
    if not username:
        return  RedirectResponse(url="/", status_code=303)
    else:
        if use_access_level != "level1":
            return RedirectResponse(url="/", status_code=303)
        else:
            return templates.TemplateResponse("add_users.html", {"request": request})


@router.post("/signup-form")
async def input_user_from_excel(
    file: UploadFile = File(...),
    db_con: AsyncSession = Depends(db.get_db)
):
    try:
        successfull_addedd = []
        failed_list = []
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        for _, row in df.iterrows():
            try:
                row = row.where(pd.notnull(row), None)
                if row["date_joined"]:
                    row["date_joined"] = str(row["date_joined"])
                    if " " in row['date_joined']:
                        row["date_joined"] = row["date_joined"].split()[0].strip()
                if row['phone']:
                    row['phone'] = str(row['phone']).strip()
                    row['phone'] = row['phone'][:-2]
                input_pass = str(db.hash_string(row['password']))
                access_level = "level4"
                if "project manager" in row['position'].lower():
                    access_level = "level2"
                if "team leader" in row['position'].lower() or "project coordinator" in row['position'].lower() or "sales" in row['position'].lower(): 
                    access_level = "level3"
                if "ceo" in row['position'].lower():
                    access_level = "level1"
                new_employee = Employee(
                    username=row['username'],
                    email=row['email'],
                    name=row['name'],
                    date_joined= row["date_joined"] if row.get('date_joined') else None,
                    profile_image='/static/USER_PROFILES/user.png',
                    position=row.get('position'),
                    phone= row.get('phone'),
                    department=row.get('department'),
                    password=input_pass,
                    reporting_person_name=row.get('reporting_person_name'),
                    reporting_person_email=row.get('reporting_person_email'),
                    reporting_person_position=row.get('reporting_person_position'),
                    reporting_person_username=row.get('reporting_person_username'),
                    access_level=access_level,
                    post_access=True
                )
                db_con.add(new_employee)                
                await db_con.commit()
                successfull_addedd.append(1)
            except Exception as e:
                failed_list.append(1)
                print(e)
        return {"message": f"Successfully added {len(successfull_addedd)}, Failed {len(failed_list)}"}
    except Exception as signup_error:
        return {"message": f"Error: {signup_error}"}

@router.get("/login")
async def login_page(request: Request):
    username = request.session.get('username', None)
    if username:
        return RedirectResponse(url="/", status_code=303)
    else:
        response = templates.TemplateResponse("login.html", {"request": request})
        # 🔒 Disable caching so browser must revalidate
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

@router.post("/login-check")
async def login_check(request: Request, username: str = Form(...), password: str = Form(...), db_con: AsyncSession = Depends(db.get_db)):
    secure_pass = str(db.hash_string(password))
    try:
        # cursor.execute(f"SELECT * FROM `{db.employee_table}` WHERE username=%s", (username,))
        result = await db_con.execute(select(Employee).where(Employee.username == username))
        user = result.scalar_one_or_none()
        ip_address_user = str(db.get_client_ip(request=request))
        log_in_time = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        if user:
            if username == user.username and user.password == secure_pass:
                request.session['username'] = user.username
                request.session['position'] = user.position
                request.session['access_level'] = user.access_level
                request.session['name'] = user.name
                request.session['post_access'] = user.post_access
                log_lgin = LoginLog(
                    username = user.username,
                    name = user.name,
                    login_time = log_in_time,
                    logout_time = None,
                    position = user.position,
                    ip_address = ip_address_user if ip_address_user else None,
                )
                db_con.add(log_lgin)                
                await db_con.commit()
                # ✅ proper redirect after login
                response = RedirectResponse(url="/", status_code=303)
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                return response
            else:
                return templates.TemplateResponse("login.html",
                {"request": request, "success": False, 'message': 'Username or Password Does not match.'})
        else:
            return templates.TemplateResponse("login.html",
            {"request": request, "success": False, 'message':'User Not Found'})
    except Exception as e:
        return templates.TemplateResponse("login.html",
        {"request": request, "success": False, 'message':f'Error: {e}'})
    finally:
        pass


@router.get("/logout")
async def logout(request: Request, db_con : AsyncSession = Depends(db.get_db)):
    logout_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    username = request.session.get('username')
    if username:
            try:
                # Method 1: Using subquery (similar to your original SQL)
                # Find the most recent login record for the user
                subquery = (
                    select(LoginLog.id)
                    .where(LoginLog.username == username)
                    .order_by(desc(LoginLog.login_time))
                    .limit(1)
                ).scalar_subquery()
                
                # Update the logout time for that record
                stmt = (
                    update(LoginLog)
                    .where(LoginLog.id == subquery)
                    .values(logout_time=logout_time)
                )
                await db_con.execute(stmt)
                await db_con.commit()
            except Exception as e:
                print(e)
    request.session.clear()
    return RedirectResponse("/", status_code=303)