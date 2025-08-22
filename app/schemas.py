from pydantic import BaseModel
from typing import Optional
from enum import Enum


# Drop-down options
class RoleEnum(str, Enum):
    admin = "Admin"
    staff = "Staff"
    visitor = "Visitor"
    security = "Security"


class DepartmentEnum(str, Enum):
    data_analyst = "Data Analyst"
    data_scientist = "Data Scientist"
    hr = "HR"
    ml_engineer = "ML Engineer"
    finance = "Finance"
    it_support = "IT Support"
    other = "Other"


# User creation schema
class UserCreate(BaseModel):
    full_name: Optional[str] = None      # not required
    email: Optional[str] = None          # not required
    role: Optional[RoleEnum] = None      # drop-down
    employee_id: str                     # required
    department: Optional[DepartmentEnum] = None  # drop-down, optional