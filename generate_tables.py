import asyncio
from credentials import database as db
from models import Base, Employee
from sqlalchemy.ext.asyncio import AsyncSession
# this file only made for executing models.py to create database table becase if...
# if i use this code on main.py it will create and run this code everytime when main file reloads.
# that will impact the performance.

async def init_models():
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
async def insert_first_user():
    async for db_con in db.get_db():  
        input_pass = str(db.hash_string('12345678'))
        position = 'ceo'
        username = 'Act000'
        name = "Kunal Santani"
        email = "ceo@gmail.com"
        department = "Operation"
        # --------------
        access_level = "level4"
        if "project manager" in position.lower():
            access_level = "level2"
        if "team leader" in position.lower() or "project coordinator" in position.lower() or "sales" in position.lower(): 
            access_level = "level3"
        if "ceo" in position.lower():
            access_level = "level1"
        new_employee = Employee(
            username=username,
            email=email,
            name=name,
            date_joined='01-01-2019',
            profile_image='/static/USER_PROFILES/user.png',
            position=position,
            phone=None,
            department=department,
            password=input_pass,
            reporting_person_name=None,
            reporting_person_email=None,
            reporting_person_position=None,
            reporting_person_username=None,
            access_level=access_level,
            post_access=True
        )
        db_con.add(new_employee)                
        await db_con.commit()
        print("sccuessfully inserted first user.")

if __name__ == "__main__":
    asyncio.run(init_models())
    # asyncio.run(insert_first_user())
