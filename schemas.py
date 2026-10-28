from pydantic import  BaseModel
class EmployeeCreate(BaseModel):
    name: str
    email: str
    department: str

class EmployeeUpdate(BaseModel):
    name: str |None = None
    email: str |None = None
    department: str |None = None


class EmployeeResponse(BaseModel):
    id : int
    name : str
    email : str
    department : str


class LeaveCreate(BaseModel):
    employee_id: int
    leave_type: str
    reason: str

class LeaveResponse(BaseModel):
    id : int
    employee_id : int
    leave_type: str
    reason: str
    status: str

class LeaveStatus(BaseModel):
    status: str

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str

class Config:
    from_attributes = True