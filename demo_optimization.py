# Script simulasi perbandingan query
from courses.models import Course
from django.db import connection, reset_queries

def run_demo():
    reset_queries()
    
    print("--- N+1 Problem Scenario ---")
    courses = Course.objects.all() # Tanpa optimasi
    for c in courses:
        print(f"Course: {c.title}, Instructor: {c.instructor.username}")
    print(f"Total Queries: {len(connection.queries)}")

    reset_queries()
    print("\n--- Optimized Scenario ---")
    courses_opt = Course.objects.for_listing() # Pakai select_related
    for c in courses_opt:
        print(f"Course: {c.title}, Instructor: {c.instructor.username}")
    print(f"Total Queries: {len(connection.queries)}")