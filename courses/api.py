from ninja import NinjaAPI
from ninja.errors import HttpError
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.conf import settings
import pymongo
import time
from typing import List

from .models import Course, Enrollment, Lesson, Progress
from .schemas import (
    RegisterIn, UserOut, ProfileUpdateIn, 
    CourseIn, CourseOut, ProgressIn
)
from .tasks import send_enrollment_email, generate_certificate, export_course_report

# Inisialisasi API Ninja
api = NinjaAPI(
    title="Simple LMS Advanced API", 
    version="2.0.0",
    description="REST API Simple LMS yang terintegrasi dengan Redis, MongoDB, dan Celery"
)

# JWT Authentication handler
apiAuth = HttpJwtAuth()

# --- HELPER: MONGODB LOGGING ---
def log_activity(user_id: int, action: str, details: str):
    """Menyimpan log aktivitas secara terstruktur ke MongoDB."""
    try:
        client = pymongo.MongoClient(settings.MONGO_URL)
        db = client['lms_logs']
        db.activity_logs.insert_one({
            "user_id": user_id,
            "action": action,
            "details": details,
            "timestamp": time.time()
        })
    except Exception:
        # Menghindari crash aplikasi jika koneksi database log NoSQL terganggu
        pass

# --- HELPER: RATE LIMITER (60 requests/minute) ---
def check_rate_limit(request):
    """Membatasi request user maksimal 60 kali per menit menggunakan Redis Cache."""
    user_ip = request.META.get('REMOTE_ADDR', 'anonymous')
    cache_key = f"ratelimit_{user_ip}"
    request_count = cache.get(cache_key, 0)
    
    if request_count >= 60:
        raise HttpError(429, "Too Many Requests! Batas limit Anda adalah 60 request/menit.")
    
    cache.set(cache_key, request_count + 1, timeout=60)

# --- 1. AUTHENTICATION (Register, Login, Me) ---

# Menggunakan router bawaan jwt untuk sign-in dan refresh token
api.add_router("/auth/", mobile_auth_router)

@api.post("/auth/register", response={201: UserOut}, tags=["Authentication"])
def register(request, data: RegisterIn):
    """Mendaftarkan akun user baru."""
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username already taken")
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email already registered")
    
    user = User.objects.create_user(**data.dict())
    log_activity(user.id, "register", f"User {user.username} successfully registered.")
    return 201, user

@api.get("/auth/me", auth=apiAuth, response=UserOut, tags=["Authentication"])
def get_me(request):
    """Retrieves profile info for the currently authenticated user."""
    db_user = User.objects.get(id=request.user.id)
    log_activity(db_user.id, "get_profile", "User retrieved profile info.")
    return db_user

@api.put("/auth/me", auth=apiAuth, response=UserOut, tags=["Authentication"])
def update_profile(request, data: ProfileUpdateIn):
    """Updates profile info for the current user."""
    db_user = User.objects.get(id=request.user.id)
    for attr, value in data.dict(exclude_none=True).items():
        setattr(db_user, attr, value)
    db_user.save()
    log_activity(db_user.id, "update_profile", "User updated profile info.")
    return db_user

# --- 2. COURSES MANAGEMENT (Redis Cache Pattern & Invalidation) ---

@api.get("/courses", response=List[CourseOut], tags=["Courses"])
def list_courses(request, search: str = None):
    """Melihat daftar semua kursus (Menggunakan Cache-Aside Redis)."""
    check_rate_limit(request)
    
    cache_key = "course_list_cache"
    if not search:
        cached_courses = cache.get(cache_key)
        if cached_courses:
            log_activity(0, "list_courses", "Fetched courses list from Redis Cache (Cache Hit).")
            return cached_courses

    qs = list(Course.objects.select_related('instructor').all())
    if search:
        qs = [c for c in qs if search.lower() in c.title.lower()]
    
    if not search:
        cache.set(cache_key, qs, timeout=300)
        log_activity(0, "list_courses", "Fetched courses list from PostgreSQL Database (Cache Miss).")
    
    return qs

@api.get("/courses/{id}", response=CourseOut, tags=["Courses"])
def get_course_detail(request, id: int):
    """Melihat detail satu kursus berdasarkan ID (Menggunakan Caching Redis)."""
    check_rate_limit(request)
    
    cache_key = f"course_detail_{id}"
    cached_course = cache.get(cache_key)
    
    if cached_course:
        log_activity(0, "course_detail", f"Fetched course {id} detail from Redis Cache (Cache Hit).")
        return cached_course
        
    course = get_object_or_404(Course, id=id)
    cache.set(cache_key, course, timeout=600)
    log_activity(0, "course_detail", f"Fetched course {id} detail from PostgreSQL Database (Cache Miss).")
    return course

@api.post("/courses", auth=apiAuth, response={201: CourseOut}, tags=["Courses"])
def create_course(request, data: CourseIn):
    """Membuat kursus baru dan mengosongkan cache daftar kursus lama."""
    db_user = User.objects.get(id=request.user.id)
    
    # --- VALIDASI PINTAR KATEGORI ---
    if hasattr(data, 'category_id') and data.category_id:
        try:
            from .models import Category
            if not Category.objects.filter(id=data.category_id).exists():
                raise HttpError(400, f"Kategori dengan ID {data.category_id} tidak ditemukan. Silakan buat Kategori terlebih dahulu melalui Django Admin (http://localhost:8000/admin).")
        except ImportError:
            # Lewati jika model Category tidak didefinisikan secara eksplisit
            pass
            
    course = Course.objects.create(
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        instructor=db_user
    )
    
    cache.delete("course_list_cache")
    log_activity(db_user.id, "create_course", f"Created new course ID {course.id} & invalidated list cache.")
    return 201, course

@api.patch("/courses/{id}", auth=apiAuth, response=CourseOut, tags=["Courses"])
def update_course(request, id: int, data: CourseIn):
    """Memperbarui kursus (Owner-Only) dan melakukan cache invalidation."""
    course = get_object_or_404(Course, id=id)
    db_user = User.objects.get(id=request.user.id)
    
    if course.instructor != db_user:
        raise HttpError(403, "Forbidden: You do not own this course")
    
    for attr, value in data.dict(exclude_none=True).items():
        setattr(course, attr, value)
    course.save()
    
    cache.delete("course_list_cache")
    cache.delete(f"course_detail_{id}")
    
    log_activity(db_user.id, "update_course", f"Updated course ID {id} & cleared cache.")
    return course

@api.delete("/courses/{id}", auth=apiAuth, tags=["Courses"])
def delete_course(request, id: int):
    """Menghapus kursus (Admin-Only) dan melakukan cache invalidation."""
    course = get_object_or_404(Course, id=id)
    db_user = User.objects.get(id=request.user.id)
    
    if not db_user.is_superuser:
        raise HttpError(403, "Forbidden: Only admins can delete courses")
    
    course_id = course.id
    course.delete()
    
    cache.delete("course_list_cache")
    cache.delete(f"course_detail_{course_id}")
    
    log_activity(db_user.id, "delete_course", f"Deleted course ID {course_id} & cleared cache.")
    return {"message": "Course deleted successfully"}

# --- 3. ENROLLMENTS & PROGRESS (Celery Background Tasks & Analytics Log) ---

@api.post("/enrollments", auth=apiAuth, tags=["Enrollments"])
def enroll_to_course(request, course_id: int):
    """Mendaftar kursus dan memicu pengiriman email secara asinkron lewat Celery."""
    db_user = User.objects.get(id=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    
    if Enrollment.objects.filter(student=db_user, course=course).exists():
        raise HttpError(400, "Already enrolled in this course")
    
    Enrollment.objects.create(student=db_user, course=course)
    send_enrollment_email.delay(db_user.id, course.id)
    
    log_activity(db_user.id, "enroll_course", f"Enrolled student into course {course.title} and queued welcome email.")
    return {"message": "Successfully enrolled! Welcome email is being processed in the background."}

@api.get("/enrollments/my-courses", auth=apiAuth, response=List[CourseOut], tags=["Enrollments"])
def my_enrolled_courses(request):
    """Melihat kursus yang sedang diikuti."""
    db_user = User.objects.get(id=request.user.id)
    enrollments = Enrollment.objects.filter(student=db_user).select_related('course')
    return [e.course for e in enrollments]

@api.post("/enrollments/progress", auth=apiAuth, tags=["Enrollments"])
def mark_lesson_complete(request, data: ProgressIn):
    """Menyelesaikan pelajaran dan memicu Celery Task pembuatan sertifikat."""
    lesson = get_object_or_404(Lesson, id=data.lesson_id)
    db_user = User.objects.get(id=request.user.id)
    
    if not Enrollment.objects.filter(student=db_user, course=lesson.course).exists():
        raise HttpError(403, "Forbidden: You must enroll in the course first")
    
    Progress.objects.get_or_create(student=db_user, lesson=lesson)
    generate_certificate.delay(db_user.id, lesson.course.id)
    
    log_activity(db_user.id, "complete_lesson", f"Completed lesson {lesson.id} & queued async certificate generation.")
    return {"message": "Progress saved successfully! Certificate processing queued."}

# --- 4. EXPORT & REPORT (MongoDB Aggregations & Async Export) ---

@api.get("/report/export", auth=apiAuth, tags=["Analytics & Reports"])
def trigger_report_export(request):
    """Memicu Celery Task asinkron untuk pembuatan dokumen laporan CSV."""
    db_user = User.objects.get(id=request.user.id)
    if not db_user.is_staff:
        raise HttpError(403, "Forbidden: Only staff can export report.")
        
    task = export_course_report.delay()
    log_activity(db_user.id, "export_report", f"Scheduled Excel/CSV course export. Task ID: {task.id}")
    return {"message": "CSV export has been scheduled in the background.", "task_id": task.id}

@api.get("/report/analytics", auth=apiAuth, tags=["Analytics & Reports"])
def get_learning_analytics(request):
    """Melakukan agregasi rekapan aktivitas pembelajaran langsung dari MongoDB."""
    db_user = User.objects.get(id=request.user.id)
    if not db_user.is_staff:
        raise HttpError(403, "Forbidden: Only staff can access analytics.")
        
    try:
        client = pymongo.MongoClient(settings.MONGO_URL)
        db = client['lms_logs']
        
        pipeline = [
            {"$group": {"_id": "$event", "count": {"$sum": 1}}}
        ]
        
        analytics_result = list(db.learning_analytics.aggregate(pipeline))
        formatted_report = {item["_id"]: item["count"] for item in analytics_result}
        return {"learning_analytics_report": formatted_report}
    except Exception as e:
        raise HttpError(500, f"Error gathering analytics data: {str(e)}")