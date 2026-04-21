from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Max, Min
from .models import Course, Category, Enrollment

# --- LATIHAN INTI A & B: select_related (Relasi ForeignKey) ---
def course_list_baseline(request):
    courses = Course.objects.all()
    data = []
    for c in courses:
        data.append({
            'course': c.title,
            'teacher': c.instructor.username # Memicu N+1
        })
    return JsonResponse({'data': data})

def course_list_optimized(request):
    # Menggunakan select_related untuk JOIN data instructor
    courses = Course.objects.select_related('instructor').all()
    data = [{'course': c.title, 'teacher': c.instructor.username} for c in courses]
    return JsonResponse({'data': data})

# --- LATIHAN INTI B: prefetch_related (Relasi Many-to-Many / Reverse FK) ---
def course_members_baseline(request):
    courses = Course.objects.all()
    payload = []
    for c in courses:
        payload.append({
            'course': c.title,
            'member_count': c.students.count() # N+1 pada relasi Enrollment
        })
    return JsonResponse({'data': payload})

def course_members_optimized(request):
    # Menggunakan prefetch_related untuk mengambil data enrollment secara massal
    courses = Course.objects.prefetch_related('students').all()
    payload = [{'course': c.title, 'member_count': c.students.count()} for c in courses]
    return JsonResponse({'data': payload})

# --- LATIHAN INTI C: Aggregate & Annotate ---
def course_dashboard_baseline(request):
    courses = Course.objects.all()
    data = []
    for c in courses:
        # Menghitung manual di Python (Tidak efisien)
        data.append({
            'course': c.title,
            'enrollment_count': Enrollment.objects.filter(course=c).count()
        })
    return JsonResponse({'data': data})

def course_dashboard_optimized(request):
    # Menggunakan annotate agar database yang menghitung (1 Query)
    courses = Course.objects.annotate(enrollment_count=Count('students')).all()
    stats = Course.objects.aggregate(
        total_courses=Count('id'),
        # Tambahkan statistik lain jika diperlukan
    )
    data = [{'course': c.title, 'enrollment_count': c.enrollment_count} for c in courses]
    return JsonResponse({'data': data, 'global_stats': stats})