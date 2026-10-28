from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, background
from sqlalchemy.sql import cache_key
import time

from database import engine, Base, SessionLocal
import models
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from auth import  create_token, get_current_user
from models import Employee
from schemas import (EmployeeCreate , EmployeeResponse, EmployeeUpdate,
                     LeaveCreate, LeaveResponse, LeaveStatus, LoginRequest, LoginResponse)
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from cachetools import  TTLCache
from routes import router


Base.metadata.create_all(engine)
app = FastAPI()
app.include_router(router)
employee_cache = TTLCache(maxsize=100, ttl=30)

limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def send_welcome_notification(employee_name: str, email:str):
    print(
        f'Sending welcome notification to'
        f' {employee_name} ({email})'
    )
    time.sleep(3)
    print(''
          f'Welcome notification completed for {employee_name}')

def create_demo_users():

    db = SessionLocal()

    try:
        employee = db.query(models.User).filter(
            models.User.username == "employee"
        ).first()

        if employee is None:
            employee = models.User(
                username="employee",
                password="employee",
                role="employee"
            )
            db.add(employee)

        manager = db.query(models.User).filter(
            models.User.username == "manager"
        ).first()

        if manager is None:
            manager = models.User(
                username="manager",
                password="manager",
                role="manager"
            )
            db.add(manager)

        db.commit()

    finally:
        db.close()


create_demo_users()
        

@app.post("/login", response_model=LoginResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.username == data.username
    ).first()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if user.password != data.password:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    token = create_token({
        "sub": user.username,
        "role": user.role
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@app.get("/")
def home ():
    return {"message": "welcome to employee management API"}


@app.post("/employees", response_model=EmployeeResponse)
def create_employee(
        employee : EmployeeCreate,
        background_tasks : BackgroundTasks,
        db : Session = Depends(get_db)

):
    new_employee = models.Employee(
        name = employee.name,
        email = employee.email,
        department = employee.department
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    background_tasks.add_task(
        send_welcome_notification,
        new_employee.name,
        new_employee.email

    )
    return new_employee




# @app.get("/employees",response_model= list[EmployeeResponse])
# def get_employees(
#     db : Session = Depends(get_db)):
#     employees = db.query(models.Employee).all()
#     return employees

@app.get("/employees", response_model=list[EmployeeResponse])
@limiter.limit("5/minute")
def get_employees(
    request: Request,
    page: int = 1,
    limit: int = 2,
    db: Session = Depends(get_db)
):
    if page <1 or limit <1 or limit>100:
        raise HTTPException(
            status_code=400,detail='page must be between 1 and 100'
        )
    cache_key = (page,limit)
    if cache_key in employee_cache:
        print('returing employee from CACHE')
        return employee_cache[cache_key]
    skip = (page - 1) * limit

    employees = (
        db.query(models.Employee)
        .offset(skip)
        .limit(limit)
        .all()
    )
    result =[
        {
        'id':employee.id,
        'name': employee.name,
        'email':employee.email,
        'department':employee.department
        }
        for employee in employees
    ]
    employee_cache[cache_key] = result
    print('returing employees from database')

    return result
@app.get("/employees")
def get_employee(
        page :int =1,
        limit:int= 2,
        db:Session=Depends(get_db)
):
        #    1-2
    skip = (page-1)*limit
    employees = db.query(models.Employee).offset(skip).limit(limit).all()
    return {
        'page':page,
        'limit':limit,
        'employees':employees
    }


@app.put("/employees/{employee_id}", response_model=EmployeeResponse)
def update_employee(
        employee_id :int,
        employee : EmployeeCreate,
        db : Session = Depends(get_db)
):
    existing_employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    existing_employee.name = employee.name
    existing_employee.email = employee.email
    existing_employee.department = employee.department
    db.commit()
    db.refresh(existing_employee)
    return existing_employee
@app.patch("/employees/{employee_id}")
def update_employee_patical(employee_id:int,
                            employee:EmployeeUpdate,
                            db:Session = Depends(get_db)):
    existing_employee = db.query(models.Employee).filter(models.Employee.id == employee_id).first()
    if existing_employee is None:
        raise HTTPException(status_code=404, detail="Employee not exist")
    if employee.name is not None:
        existing_employee.name = employee.name
    if employee.email is not None:
        existing_employee.email = employee.email
    if employee.department is not None:
        existing_employee.department = employee.department
    db.commit()
    db.refresh(existing_employee)
    return existing_employee

# Delete employee
@app.delete("/employees/{employee_id}")
def delete_employee(
        employee_id: int,
        db: Session = Depends(get_db)
):
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id
    ).first()

    db.delete(employee)
    db.commit()

    return {
        "message": "Employee deleted successfully"
    }

@app.post("/leaves", response_model=LeaveResponse)
def create_leave(
        leave: LeaveCreate,
        db : Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
      if current_user['role'] != 'employee':
          raise HTTPException(status_code=403, detail="only employee can create leaves")
      new_leave = models.Leave(
                employee_id = leave.employee_id,
                leave_type = leave.leave_type,
                reason = leave.reason,
                #status = leave.status
            )

      db.add(new_leave)
      db.commit()
      db.refresh(new_leave)
      return new_leave

@app.put("/leaves/{leave_id}/status")
def upadte_leave_status(
        leave_id :int,
        data: LeaveStatus,
        db : Session = Depends(get_db),
        current_user: dict = Depends(get_current_user)
):
      if current_user['role'] != 'manager':
          raise HTTPException(status_code=403, detail="only manager can update leaves status")
      leave = db.query(models.Leave).filter(models.Leave.id == leave_id).first()
      if leave is None:
            raise HTTPException(status_code=404, detail="Leave not exist")
      leave.status = data.status
      db.commit()
      db.refresh(leave)
      return leave