import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import Course
from django.db import connection, reset_queries

def run_demo():
    # 1. Scenario N+1 (Tanpa Optimasi)
    reset_queries()
    print("\n--- SCENARIO N+1 (Tanpa Optimasi) ---")
    courses = Course.objects.all()
    for c in courses:
        print(f"Course: {c.title} | Instructor: {c.instructor.username} | Category: {c.category.name}")
    
    queries_n1 = len(connection.queries)
    print(f"Total Queries: {queries_n1}")

    # 2. Scenario Optimized (Dengan select_related)
    reset_queries()
    print("\n--- SCENARIO OPTIMIZED (select_related) ---")
    courses_opt = Course.objects.for_listing()
    for c in courses_opt:
        print(f"Course: {c.title} | Instructor: {c.instructor.username} | Category: {c.category.name}")
    
    queries_opt = len(connection.queries)
    print(f"Total Queries: {queries_opt}")
    
    print(f"\nKesimpulan: Optimasi berhasil memangkas dari {queries_n1} query menjadi {queries_opt} query saja!")

if __name__ == "__main__":
    run_demo()