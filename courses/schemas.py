from ninja import Schema
from typing import Optional, List
from datetime import datetime

# --- User & Authentication Schemas ---

class UserOut(Schema):
    """Schema for returning user data (without password)."""
    id: int
    username: str
    email: str
    first_name: str
    last_name: str

class RegisterIn(Schema):
    """Schema for new user registration input."""
    username: str
    password: str
    email: str
    first_name: str
    last_name: str

class ProfileUpdateIn(Schema):
    """Schema for updating current user profile."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None

# --- Course Schemas ---

class CourseIn(Schema):
    """Schema for creating or updating a course."""
    title: str
    description: str
    category_id: int

class CourseOut(Schema):
    """Detailed course schema including instructor info."""
    id: int
    title: str
    description: str
    instructor: UserOut
    created_at: datetime

# --- Enrollment & Progress Schemas ---

class ProgressIn(Schema):
    """Schema for marking a lesson as completed."""
    lesson_id: int