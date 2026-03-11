from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
import json
from models import Employee, ProjectAssignment, TodoMaster, TodoAssignment, TodoEscalation
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Request,HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from credentials import database as db
from routes.notification import notify

templates = Jinja2Templates(directory="templates")
UPLOAD_DIR  =  "INPUT_DATA"
router = APIRouter()


# Utility functions for response management
def get_responses_from_json(responses_json: str) -> List[dict]:
    """Parse responses JSON string to list of response objects"""
    if not responses_json:
        return []
    try:
        return json.loads(responses_json)
    except (json.JSONDecodeError, TypeError):
        return []

def save_responses_to_json(responses: List[dict]) -> str:
    """Convert responses list to JSON string"""
    return json.dumps(responses, ensure_ascii=False)

def generate_response_id() -> str:
    """Generate unique response ID"""
    return f"resp_{int(datetime.now().timestamp() * 1000)}"



# --------------------------------------

# ----------TO-DO API Routes ----------
@router.get("/my-to-do", response_class=HTMLResponse)
async def todo_page(request: Request, db_con: AsyncSession = Depends(db.get_db)):
    username = request.session.get("username", None)
    access_level = request.session.get("access_level", None)
    name = request.session.get("name", "Unknown").split(" ")[0].strip()
    if not username:
        return RedirectResponse(url="/", status_code=302)
    res = await db_con.execute(select(ProjectAssignment).where(ProjectAssignment.assigned_person_username == username))
    projects = res.scalars().all()
    projects = [db.orm_to_dict(x) for x in projects]
    res2 = await db_con.execute(select(Employee))
    developers = res2.scalars().all()
    developers = [db.orm_to_dict(x) for x in developers]
    return templates.TemplateResponse("todo_kanaban.html", {"request": request, "username": username,
                                                            'projects': projects,
                                                            'developers': developers,
                                                            "access_level": access_level,
                                                            'name': name})


# ====== API ======
@router.get("/api/todos")
async def get_todos(username, db_con: AsyncSession = Depends(db.get_db)):
    try:
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
                TodoAssignment.assignee_name,
                TodoAssignment.created_by_username,
                TodoAssignment.created_by_name,
                TodoAssignment.reporting_person_username,
                TodoAssignment.todo_created_date,
                TodoAssignment.todo_completed_date,
                TodoAssignment.status,
                TodoAssignment.show_or_not,
                TodoAssignment.access_level,
            )
            .join(TodoMaster, TodoAssignment.todo_id == TodoMaster.id)
            .where(and_(TodoAssignment.assignee_username == username, TodoAssignment.show_or_not == True))
        )
        assigned_to_result = await db_con.execute(assigned_to_query)
        assigned_to_todos = assigned_to_result.mappings().all()
        print(assigned_to_todos)
        return assigned_to_todos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching todos: {str(e)}")


@router.post("/api/todos")
async def create_task(request: Request, db_con: AsyncSession = Depends(db.get_db)):
    data = await request.json()
    todo_created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    assignee_list = []
    try:
        # Get creator details
        project_de = None
        dev_d = await db_con.execute(select(Employee).where(Employee.username == data['username']))
        dev_details = dev_d.scalars().first()
        project_id = data.get("project_id")
        if project_id and project_id != "N/A":
            pro_d = await db_con.execute(select(ProjectAssignment).where(
                and_(ProjectAssignment.project_id == project_id,
                ProjectAssignment.assigned_person_username == data['username']))
                )
            project_de = pro_d.scalars().first()
        # Insert into todo_master_table (creator's main task)
        new_record = TodoMaster(
            project_id=project_de.project_id if project_de else None,
            project_name=project_de.project_name if project_de else None,
            todo_title=data["title"],
            todo_descr=data.get("description"),
            priority=data.get("priority"),
            color=data.get("color", "purple"),
            status=data.get("status", "todo"),
            created_by=data['username'],
            created_at=todo_created_date
        )
        db_con.add(new_record)
        await db_con.flush()
        master_todo_id = new_record.id
        # ---- Insert into todo_assignment_table ----
        assignees = data.get("assignee_username", None)
        if assignees:
            assignee_list.append(assignees)
        if assignee_list:
            for assignee in assignee_list:
                assig_que = await db_con.execute(select(Employee).where(Employee.username == assignee))
                assi_det = assig_que.scalars().first()
                escalation = data.get("escalation")
                if escalation == 'yes':
                    new_record_esc = TodoEscalation(
                        created_by_username=data['username'],
                        created_by_name=dev_details.name,
                        todo_id=master_todo_id,
                        project_id=project_de.project_id if project_de else None,
                        project_name=project_de.project_name if project_de else None,
                        assignee_username=assi_det.username,
                        assignee_name=assi_det.name,
                        todo_created_date=todo_created_date,
                        todo_completed_date=None,
                        status=data.get("status", "todo"),
                        show_or_not=True,
                        access_level=assi_det.access_level
                    )
                    db_con.add(new_record_esc)
                else:
                    new_record_as = TodoAssignment(
                        todo_id=master_todo_id,
                        project_id=project_de.project_id if project_de else None,
                        project_name=project_de.project_name if project_de else None,
                        created_by_username=dev_details.username,
                        created_by_name=dev_details.name,
                        assignee_username=assi_det.username,
                        assignee_name=assi_det.name,
                        reporting_person_username=assi_det.reporting_person_username,
                        todo_created_date=todo_created_date,
                        todo_completed_date=None,
                        status=data.get("status", "todo"),
                        show_or_not=True,
                        access_level=assi_det.access_level
                    )
                    db_con.add(new_record_as)
                    await notify(
                        db_con = db_con,
                        user_id = assi_det.username,
                        sender_id=dev_details.username,
                        sender_name=dev_details.name,
                        type = "task",
                        title=f"Todo Assigned to you by {dev_details.name}",
                        message=(
                            f"Todo: {data['title']}"
                            # f"Assigned to: {assigned_user_name} (ID: {assigned_user_id})"
                        ),
                    )
        else:
            new_record_as = TodoAssignment(
                todo_id=master_todo_id,
                project_id=project_de.project_id if project_de else None,
                project_name=project_de.project_name if project_de else None,
                created_by_username=dev_details.username,
                created_by_name=dev_details.name,
                assignee_username=dev_details.username,
                assignee_name="self",
                reporting_person_username=dev_details.reporting_person_username,
                todo_created_date=todo_created_date,
                todo_completed_date=None,
                status=data.get("status", "todo"),
                show_or_not=True,
                access_level=dev_details.access_level
            )
            db_con.add(new_record_as)
        await db_con.commit()
        return {"message": "Task created", "todo_id": master_todo_id, "assignees": assignees}
    except Exception as e:
        await db_con.rollback()
        return {"error": str(e)}


@router.patch("/api/todos/{task_id}")
async def update_task_status(task_id: int, request: Request,
                             db_con: AsyncSession = Depends(db.get_db)):
    data = await request.json()
    todo_completed_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if data['status'] == "done":
            stmt = (update(TodoAssignment).where(TodoAssignment.id == task_id).values(
                status="done",
                todo_completed_date=todo_completed_date
            ))
        else:
            stmt = (update(TodoAssignment).where(TodoAssignment.id == task_id).values(**data))
        await db_con.execute(stmt)
        await db_con.commit()
        return {"message": "Task updated"}
    except Exception as e:
        return {"message": f"Error: {str(e)}"}


@router.delete("/api/todos/{task_id}")
async def soft_delete_task(task_id: int, db_con: AsyncSession = Depends(db.get_db)):
    try:
        stmt = (update(TodoAssignment).where(TodoAssignment.id == task_id).values(show_or_not=False))
        await db_con.execute(stmt)
        await db_con.commit()
        return {"message": "Task hidden"}
    except Exception as e:
        return {"message": f"Error: {str(e)}"}


# this endpoint is for manager/tl who want to see their dev.'s progress/todos
@router.get('/dev-todo')
async def dev_manager_todo(request: Request, db_con: AsyncSession = Depends(db.get_db)):
    username = request.session.get("username", None)
    user_access_level = request.session.get("access_level", None)
    if not username:
        return RedirectResponse(url="/", status_code=302)
    if user_access_level in ['level2', 'level1']:
        # means manager can see their employees todos...
        stmt = (select(Employee).where(Employee.reporting_person_username == username))
        res = await db_con.execute(stmt)
        developers = res.scalars().all()
        return templates.TemplateResponse("manager_todo_dash2.html", {"request": request, "username": username,
                                                                      "developers": developers})
    else:
        return RedirectResponse(url="/", status_code=302)



# Escalation to_do endpoins----------------------------------------------

@router.get("/show-esclated-todo")
async def show_esclated_todo(request: Request, db_con: AsyncSession = Depends(db.get_db)):
    username = request.session.get('username', None)
    name = request.session.get('name', None)
    if not username:
        return RedirectResponse(url="/login", status_code=303)
    else:
        res2 = await db_con.execute(select(Employee))
        developers = res2.scalars().all()
        developers = [db.orm_to_dict(x) for x in developers]
        return templates.TemplateResponse("show_escalate_todo.html", {'request': request,
        'username': username,"name":name, "developers":developers
        })

@router.get("/show-esclated-todo_fetch/{username}")
async def get_escalated_todos(username: str, db_con: AsyncSession = Depends(db.get_db)):
    """
    Fetch all escalated todos for a user (both assigned by and assigned to)
    """
    try:
        # Get todos assigned by this user
        assigned_by_query = (
                    select(
                        TodoEscalation.id,
                        TodoMaster.todo_title,
                        TodoMaster.todo_descr,
                        TodoMaster.priority,
                        TodoMaster.color,
                        TodoEscalation.project_id,
                        TodoEscalation.project_name,
                        TodoEscalation.created_by_username,
                        TodoEscalation.created_by_name,
                        TodoEscalation.assignee_username,
                        TodoEscalation.assignee_name,
                        TodoEscalation.todo_created_date,
                        TodoEscalation.todo_completed_date,
                        TodoEscalation.responses,
                        TodoEscalation.response_updated_at,
                        TodoEscalation.status,
                        TodoEscalation.show_or_not,
                        TodoEscalation.is_started,
                        TodoEscalation.access_level,
                    )
                    .join(TodoMaster, TodoEscalation.todo_id == TodoMaster.id)
                    .where(and_(TodoEscalation.created_by_username == username, TodoEscalation.show_or_not == True))
                )
        assigned_by_result = await db_con.execute(assigned_by_query)
        assigned_by_todos = assigned_by_result.mappings().all()
        stmt2 = (
                    select(
                        TodoEscalation.id,
                        TodoMaster.todo_title,
                        TodoMaster.todo_descr,
                        TodoMaster.priority,
                        TodoMaster.color,
                        TodoEscalation.project_id,
                        TodoEscalation.project_name,
                        TodoEscalation.created_by_username,
                        TodoEscalation.created_by_name,
                        TodoEscalation.assignee_username,
                        TodoEscalation.assignee_name,
                        TodoEscalation.todo_created_date,
                        TodoEscalation.todo_completed_date,
                        TodoEscalation.responses,
                        TodoEscalation.response_updated_at,
                        TodoEscalation.status,
                        TodoEscalation.show_or_not,
                        TodoEscalation.is_started,
                        TodoEscalation.access_level,
                    )
                    .join(TodoMaster, TodoEscalation.todo_id == TodoMaster.id)
                    .where(and_(TodoEscalation.assignee_username == username, TodoEscalation.show_or_not == True))
                )
        assigned_to_result = await db_con.execute(stmt2)
        assigned_to_todos = assigned_to_result.mappings().all()

        def format_todo(todo):
            # Parse responses from JSON - handle None case
            responses_data = todo['responses'] if todo['responses'] else None
            responses_list = get_responses_from_json(responses_data) if responses_data else []

            return {
                "todo_id": todo['id'],
                "todo_title": todo['todo_title'] or "Untitled Task",
                "project_id": todo['project_id'],
                "project_name": todo['project_name'] or "No Project",
                "created_by_name": todo['created_by_name'] or "Unknown",
                "assignee_name": todo['assignee_name'] or "Unassigned",
                "created_by_username": todo['created_by_username'],
                "assignee_username": todo['assignee_username'],
                "todo_descr": todo['todo_descr'],
                "status": todo['status'] if todo['status'] else 'todo',
                "todo_created_date": str(todo['todo_created_date']) if todo['todo_created_date'] else None,
                "todo_completed_date": str(todo['todo_completed_date']) if todo['todo_completed_date'] else None,
                "is_started": bool(todo['is_started']) if todo['is_started'] is not None else False,
                "access_level": todo['access_level'] if todo['access_level'] else 'level4',
                "responses": [
                    {
                        "id": resp.get("id", ""),
                        "response_text": resp.get("response_text", ""),
                        "user_id": resp.get("user_id", ""),
                        "user_name": resp.get("user_name", "Unknown"),
                        "created_at": resp.get("created_at", ""),
                        "updated_at": resp.get("updated_at", resp.get("created_at", ""))
                    } for resp in responses_list
                ] if responses_list else []
            }

        main_data = {
            "assigned_by_todos": [format_todo(todo) for todo in assigned_by_todos],
            "assigned_to_todos": [format_todo(todo) for todo in assigned_to_todos]
        }
        return main_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching todos: {str(e)}")


@router.post("/api/escalated-todos/{todo_id}/responses")
async def add_escalation_response(
        todo_id: int,
        request: Request,
        db_con: AsyncSession = Depends(db.get_db)
):
    """Add a response to an escalated to_do"""

    try:
        data = await request.json()
        response_text = data.get("response_text")
        user_id = data.get("user_id")
        user_name = data.get("user_name")

        if not response_text or not user_id:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Get the escalation record
        stmt = select(TodoEscalation).where(TodoEscalation.id == todo_id)
        result = await db_con.execute(stmt)
        escalation = result.scalar_one_or_none()

        if not escalation:
            raise HTTPException(status_code=404, detail="Task not found")

        # Parse existing responses or create new list
        existing_responses = get_responses_from_json(escalation.responses) if escalation.responses else []

        # Create new response
        new_response = {
            "id": str(len(existing_responses) + 1),
            "response_text": response_text,
            "user_id": user_id,
            "user_name": user_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Add to existing responses
        existing_responses.append(new_response)

        # Convert back to JSON string
        escalation.responses = json.dumps(existing_responses)
        escalation.response_updated_at = datetime.now()

        await db_con.commit()

        return {"message": "Response added successfully", "response": new_response}

    except Exception as e:
        await db_con.rollback()
        print("ERROR adding response:", str(e))
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error adding response: {str(e)}")


@router.patch("/api/escalated-todos/{todo_id}/responses/{response_id}")
async def update_escalation_response(
        todo_id: int,
        response_id: str,
        request: Request,
        db_con: AsyncSession = Depends(db.get_db)
):
    """Update a response"""
    try:
        data = await request.json()
        response_text = data.get("response_text")

        if not response_text:
            raise HTTPException(status_code=400, detail="Missing response text")

        # Get the escalation record
        stmt = select(TodoEscalation).where(TodoEscalation.id == todo_id)
        result = await db_con.execute(stmt)
        escalation = result.scalar_one_or_none()

        if not escalation:
            raise HTTPException(status_code=404, detail="Task not found")

        # Parse existing responses
        existing_responses = get_responses_from_json(escalation.responses) if escalation.responses else []

        # Find and update the response
        response_found = False
        for resp in existing_responses:
            if str(resp.get("id")) == str(response_id):
                resp["response_text"] = response_text
                resp["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                response_found = True
                break

        if not response_found:
            raise HTTPException(status_code=404, detail="Response not found")

        # Save back to database
        escalation.responses = json.dumps(existing_responses)
        escalation.response_updated_at = datetime.now()

        await db_con.commit()

        return {"message": "Response updated successfully"}

    except Exception as e:
        await db_con.rollback()
        print("ERROR updating response:", str(e))
        raise HTTPException(status_code=500, detail=f"Error updating response: {str(e)}")


@router.patch("/api/escalated-todos/{todo_id}")
async def update_escalated_todo(
        todo_id: int,
        request: Request,
        db_con: AsyncSession = Depends(db.get_db)
):
    """Update escalated todo (status, is_started, etc)"""
    try:
        data = await request.json()

        # Get the escalation record
        stmt = select(TodoEscalation).where(TodoEscalation.id == todo_id)
        result = await db_con.execute(stmt)
        escalation = result.scalar_one_or_none()

        if not escalation:
            raise HTTPException(status_code=404, detail="Task not found")

        # Update fields
        if "status" in data:
            escalation.status = data["status"]

        if "is_started" in data:
            escalation.is_started = data["is_started"]

        if "todo_completed_date" in data:
            escalation.todo_completed_date = data["todo_completed_date"]

        await db_con.commit()

        return {"message": "Task updated successfully"}

    except Exception as e:
        await db_con.rollback()
        print("ERROR updating task:", str(e))
        raise HTTPException(status_code=500, detail=f"Error updating task: {str(e)}")

@router.post("/api/escalated-todos/{todo_id}/forward")
async def forward_escalated_todo(
    todo_id: int,
    request: Request,
    db_con: AsyncSession = Depends(db.get_db)
):
    """Forward an escalated task to another developer"""
    try:
        data = await request.json()
        forward_to_username = data.get("forward_to_username")
        forward_to_name = data.get("forward_to_name")
        reason = data.get("reason")
        if not forward_to_username or not reason:
            raise HTTPException(status_code=400, detail="Missing fields")

        stmt = select(TodoEscalation).where(TodoEscalation.id == todo_id)
        result = await db_con.execute(stmt)
        todo = result.scalars().first()
        todo = db.orm_to_dict(todo)
        if not todo:
            raise HTTPException(status_code=404, detail="Task not found")
        selected_user = await db_con.execute(select(Employee).where(Employee.username == forward_to_username))
        selected_user_data = selected_user.scalars().first()
        selected_user_data = db.orm_to_dict(selected_user_data)
        # Update task
        old_username = todo['assignee_username']
        old_name = todo['assignee_name']
        todo['assignee_username'] = forward_to_username
        todo['assignee_name'] = forward_to_name
        todo['status'] = "forwarded"
        todo['response_updated_at'] = datetime.now()

        # Add system response entry
        responses = get_responses_from_json(todo['responses']) if todo['responses'] else []

        responses.append({
            "id": str(len(responses) + 1),
            "response_text": f"Task forwarded to {forward_to_name}. \nReason: \n{reason}",
            "user_id": old_username,
            "user_name": old_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        todo['responses'] = json.dumps(responses)
        try:
            await db_con.execute(
                update(TodoEscalation)
                .where(TodoEscalation.id == todo_id)
                .values(show_or_not=False)
            )
            await db_con.commit()
        except Exception as e:
            print("Update Error:", e)
        new_task = TodoEscalation(
            created_by_username = todo['created_by_username'],
            created_by_name = todo['created_by_name'],
            todo_id = todo['todo_id'],
            project_name = todo['project_name'],
            project_id = todo['project_id'],
            assignee_name = todo['assignee_name'],
            assignee_username = todo['assignee_username'],
            todo_created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            todo_completed_date = None,
            status = todo['status'],
            show_or_not = True,
            is_started = True,
            responses = todo['responses'],
            response_updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            access_level = selected_user_data['access_level'],
        )
        db_con.add(new_task)
        await db_con.commit()

        return {"message": "Task forwarded successfully"}

    except Exception as e:
        await db_con.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/api/todos2/{username}")
async def get_developer_todos(username: str, db_con: AsyncSession = Depends(db.get_db)):
    """
    Fetch todos specifically for the manager dashboard to view a developer's progress.
    This corresponds to the /api/todos2/{userId} fetch call in manager_todo_dash2.html.
    """
    try:
        query = (
            select(
                TodoAssignment.id,
                TodoMaster.todo_title,
                TodoMaster.todo_descr,
                TodoMaster.priority,
                TodoMaster.color,
                TodoAssignment.assignee_username,
                TodoAssignment.project_name,
                TodoAssignment.todo_created_date,
                TodoAssignment.todo_completed_date,
                TodoAssignment.status
            )
            .join(TodoMaster, TodoAssignment.todo_id == TodoMaster.id)
            .where(and_(
                TodoAssignment.assignee_username == username, 
                TodoAssignment.show_or_not == True
            ))
        )
        
        result = await db_con.execute(query)
        # Convert to list of dicts for JSON response
        todos = result.mappings().all()
        
        # FastAPI handles list of mappings automatically, but we ensure it's JSON serializable
        return list(todos)

    except Exception as e:
        print(f"Error in get_developer_todos: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")