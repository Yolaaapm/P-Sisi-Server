from django.db import models
from django.contrib.auth.models import User
from django.db.models import Count

# --- Custom QuerySets & Managers (Dari Progress 2 untuk Optimasi) ---

class CourseQuerySet(models.QuerySet):
    def for_listing(self):
        # Optimasi: ambil data category dan instructor sekaligus (select_related)
        return self.select_related('category', 'instructor').annotate(
            lesson_count=Count('lessons')
        )

class EnrollmentQuerySet(models.QuerySet):
    def for_student_dashboard(self, user):
        return self.filter(student=user).select_related('course').prefetch_related('course__lessons')

# --- Models (Dengan Tambahan Indexing Modul 5) ---

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')

    class Meta:
        verbose_name_plural = "Categories"
        # LATIHAN INTI E: Indexing untuk pencarian nama kategori yang cepat
        indexes = [
            models.Index(fields=['name'], name='idx_category_name'),
        ]

    def __str__(self):
        return self.name

class Course(models.Model):
    # LATIHAN INTI E: Tambahkan db_index=True pada title
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='instructed_courses')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='courses')
    created_at = models.DateTimeField(auto_now_add=True)

    # Tetap gunakan Manager kustom dari Progress 2
    objects = CourseQuerySet.as_manager()

    class Meta:
        # LATIHAN INTI E: Index komposit sesuai pola query di modul
        indexes = [
            models.Index(fields=['instructor', 'category'], name='idx_course_inst_cat'),
            models.Index(fields=['created_at'], name='idx_course_created'),
        ]

    def __str__(self):
        return self.title

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='students')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    # Tetap gunakan Manager kustom dari Progress 2
    objects = EnrollmentQuerySet.as_manager()

    class Meta:
        unique_together = ('student', 'course')

class Progress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'lesson')
        verbose_name_plural = "Progresses"