from django.contrib import admin
from .models import Category, Course, Lesson, Enrollment

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'category', 'created_at')
    search_fields = ('title', 'description')
    list_filter = ('category', 'instructor')
    inlines = [LessonInline]

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')

admin.site.register(Enrollment)