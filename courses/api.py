from ninja import NinjaAPI
from ninja.errors import HttpError
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from .models import Course, Enrollment, Lesson, Progress
from .schemas import (
    RegisterIn, UserOut, ProfileUpdateIn, 
    CourseIn, CourseOut, ProgressIn
)
from typing import List

# Initialize Ninja API
api = NinjaAPI(
    title="Simple LMS API", 
    version="1.0.0",
    description="REST API documentation for Simple LMS with JWT Authentication"
)

# JWT Authentication handler
apiAuth = HttpJwtAuth()

# --- 1. AUTHENTICATION (Register, Login, Me) ---

# Register the built-in mobile auth router (provides sign-in and token-refresh)
api.add_router("/auth/", mobile_auth_router)

@api.post("/auth/register", response={201: UserOut}, tags=["Authentication"])
def register(request, data: RegisterIn):
    """Registers a new user account."""
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username already taken")
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email already registered")
    
    # create_user hashes the password automatically
    user = User.objects.create_user(**data.dict())
    return 201, user

@api.get("/auth/me", auth=apiAuth, response=UserOut, tags=["Authentication"])
def get_me(request):
    """Retrieves profile info for the currently authenticated user."""
    return request.user

@api.put("/auth/me", auth=apiAuth, response=UserOut, tags=["Authentication"])
def update_profile(request, data: ProfileUpdateIn):
    """Updates profile info for the current user."""
    user = request.user
    for attr, value in data.dict(exclude_none=True).items():
        setattr(user, attr, value)
    user.save()
    return user

# --- 2. COURSES MANAGEMENT (RBAC) ---

@api.get("/courses", response=List[CourseOut], tags=["Courses"])
def list_courses(request, search: str = None):
    """Lists all available courses (Public)."""
    qs = Course.objects.select_related('instructor').all()
    if search:
        qs = qs.filter(title__icontains=search)
    return qs

@api.get("/courses/{id}", response=CourseOut, tags=["Courses"])
def get_course_detail(request, id: int):
    """Retrieves detailed info for a specific course."""
    return get_object_or_404(Course, id=id)

@api.post("/courses", auth=apiAuth, response={201: CourseOut}, tags=["Courses"])
def create_course(request, data: CourseIn):
    """Creates a new course (Authenticated users)."""
    course = Course.objects.create(**data.dict(), instructor=request.user)
    return 201, course

@api.patch("/courses/{id}", auth=apiAuth, response=CourseOut, tags=["Courses"])
def update_course(request, id: int, data: CourseIn):
    """Updates a course (Course owners only)."""
    course = get_object_or_404(Course, id=id)
    
    # Ownership Check
    if course.instructor != request.user:
        raise HttpError(403, "Forbidden: You do not own this course")
    
    for attr, value in data.dict(exclude_none=True).items():
        setattr(course, attr, value)
    course.save()
    return course

@api.delete("/courses/{id}", auth=apiAuth, tags=["Courses"])
def delete_course(request, id: int):
    """Deletes a course (Admin only)."""
    course = get_object_or_404(Course, id=id)
    
    # Role Check
    if not request.user.is_superuser:
        raise HttpError(403, "Forbidden: Only admins can delete courses")
    
    course.delete()
    return {"message": "Course deleted successfully"}

# --- 3. ENROLLMENTS & PROGRESS ---

@api.post("/enrollments", auth=apiAuth, tags=["Enrollments"])
def enroll_to_course(request, course_id: int):
    """Enrolls the current student into a course."""
    course = get_object_or_404(Course, id=course_id)
    if Enrollment.objects.filter(student=request.user, course=course).exists():
        raise HttpError(400, "Already enrolled in this course")
    
    Enrollment.objects.create(student=request.user, course=course)
    return {"message": "Successfully enrolled"}

@api.get("/enrollments/my-courses", auth=apiAuth, response=List[CourseOut], tags=["Enrollments"])
def my_enrolled_courses(request):
    """Lists courses the current user is enrolled in."""
    enrollments = Enrollment.objects.filter(student=request.user).select_related('course')
    return [e.course for e in enrollments]

@api.post("/enrollments/progress", auth=apiAuth, tags=["Enrollments"])
def mark_lesson_complete(request, data: ProgressIn):
    """Marks a lesson as completed for the current student."""
    lesson = get_object_or_404(Lesson, id=data.lesson_id)
    
    # Verification: Student must be enrolled in the course
    if not Enrollment.objects.filter(student=request.user, course=lesson.course).exists():
        raise HttpError(403, "Forbidden: You must enroll in the course first")
    
    Progress.objects.get_or_create(student=request.user, lesson=lesson)
    return {"message": "Progress saved successfully"}