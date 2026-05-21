import csv
import time
from celery import shared_task
from django.core.mail import send_mail
from django.contrib.auth.models import User
from .models import Course, Enrollment
import pymongo
from django.conf import settings

# Helper untuk mendapatkan koneksi database MongoDB
def get_mongodb_connection():
    client = pymongo.MongoClient(settings.MONGO_URL)
    return client['lms_logs']

@shared_task
def send_enrollment_email(student_id, course_id):
    """
    Task 1: Mengirim email selamat datang secara asynchronous ketika siswa mendaftar (enroll) kursus.
    """
    try:
        student = User.objects.get(id=student_id)
        course = Course.objects.get(id=course_id)
        
        subject = f"Selamat Datang di Kelas {course.title}!"
        message = f"Halo {student.first_name or student.username},\n\nPendaftaran Anda untuk kelas '{course.title}' telah berhasil dilakukan. Selamat belajar dan semoga sukses!"
        from_email = "no-reply@simplelms.com"
        recipient_list = [student.email]
        
        # Simulasi jeda pengiriman email (heavy task)
        time.sleep(3)
        
        send_mail(subject, message, from_email, recipient_list, fail_silently=True)
        
        # Catat analitik ke MongoDB
        db = get_mongodb_connection()
        db.learning_analytics.insert_one({
            "event": "send_enrollment_email",
            "student_id": student_id,
            "course_id": course_id,
            "status": "success",
            "timestamp": time.time()
        })
        return f"Email pendaftaran sukses dikirim ke {student.email} untuk kelas {course.title}."
    except Exception as e:
        return f"Gagal mengirim email pendaftaran: {str(e)}"

@shared_task
def generate_certificate(student_id, course_id):
    """
    Task 2: Menghasilkan sertifikat kelulusan dalam format simulasi ketika progres belajar diselesaikan.
    """
    try:
        student = User.objects.get(id=student_id)
        course = Course.objects.get(id=course_id)
        
        # Simulasi pembuatan file sertifikat PDF yang berat
        time.sleep(5)
        
        certificate_id = f"CERT-{course_id:03d}-{student_id:05d}-{int(time.time())}"
        
        # Simpan data sertifikat ke MongoDB Learning Analytics
        db = get_mongodb_connection()
        db.learning_analytics.insert_one({
            "event": "generate_certificate",
            "student_id": student_id,
            "course_id": course_id,
            "certificate_id": certificate_id,
            "status": "generated",
            "timestamp": time.time()
        })
        return f"Sertifikat {certificate_id} berhasil diterbitkan untuk {student.username}."
    except Exception as e:
        return f"Gagal menerbitkan sertifikat: {str(e)}"

@shared_task
def update_course_statistics():
    """
    Task 3: Scheduled Task (Celery Beat) untuk memperbarui statistik jumlah pendaftar kursus berkala.
    """
    try:
        courses = Course.objects.all()
        db = get_mongodb_connection()
        records_updated = 0
        
        for course in courses:
            enrollment_count = Enrollment.objects.filter(course=course).count()
            
            # Simpan snapshot statistik ke MongoDB untuk analitik histori
            db.course_snapshots.insert_one({
                "course_id": course.id,
                "title": course.title,
                "total_students": enrollment_count,
                "timestamp": time.time()
            })
            records_updated += 1
        
        return f"Statistik diperbarui untuk {records_updated} kursus pada snapshot MongoDB."
    except Exception as e:
        return f"Gagal memperbarui statistik kursus: {str(e)}"

@shared_task
def export_course_report():
    """
    Task 4: Mengekspor laporan data kursus secara asinkron ke dalam format CSV.
    """
    try:
        courses = Course.objects.select_related('instructor').all()
        file_path = "course_report.csv"
        
        # Simulasi pembuatan laporan data skala besar
        time.sleep(4)
        
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['ID Kelas', 'Judul Kelas', 'Pengajar (Username)', 'Email Pengajar', 'Tanggal Dibuat'])
            
            for c in courses:
                writer.writerow([
                    c.id, 
                    c.title, 
                    c.instructor.username, 
                    c.instructor.email, 
                    c.created_at.strftime('%Y-%m-%d %H:%M:%S') if c.created_at else '-'
                ])
        
        # Catat aktivitas ekspor di MongoDB
        db = get_mongodb_connection()
        db.activity_logs.insert_one({
            "action": "export_course_report",
            "details": "Laporan CSV berhasil diekspor di background task.",
            "timestamp": time.time()
        })
        return f"Laporan CSV berhasil dibuat di {file_path}."
    except Exception as e:
        return f"Gagal mengekspor laporan: {str(e)}"