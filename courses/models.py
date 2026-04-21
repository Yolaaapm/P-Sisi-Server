from django.db import models
from django.contrib.auth.models import User
from django.db.models import Count

# --- Custom QuerySets & Managers ---

class CourseQuerySet(models.QuerySet):
    def for_listing(self):
        # Optimasi: ambil data category dan instructor sekaligus (select_related)
        return self.select_related('category', 'instructor').annotate(
            lesson_count=Count('lessons')
        )

class EnrollmentQuerySet(models.QuerySet):
    def for_student_dashboard(self, user):
        return self.filter(student=user).select_related('course').prefetch_related('course__lessons')

# --- Models ---

class Category(models.Model):
    name = models.CharField(max_length=100)
    # Self-referencing untuk hierarchy (Sub-category)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='instructed_courses')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='courses')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CourseQuerySet.as_manager()

    def __str__(self):
        return self.title

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0) # Untuk ordering

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='students')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    objects = EnrollmentQuerySet.as_manager()

    class Meta:
        unique_together = ('student', 'course') # Unique constraint

class Progress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'lesson')
        verbose_name_plural = "Progresses"