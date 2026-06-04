import requests
import time
import redis
import json

# --- KONEKSI REDIS CLIENT ---
# Dibuat dinamis agar otomatis mendeteksi Redis di localhost maupun Docker
r = None
for host in ['localhost', 'redis', 'simple-lms-redis']:
    try:
        r = redis.Redis(host=host, port=6379, db=0, decode_responses=True)
        r.ping()  # Tes apakah koneksi aktif
        break
    except Exception:
        continue

def get_weather(city):
    """Fungsi get_weather yang sudah dimodifikasi dengan caching Redis"""
    cache_key = f"weather:{city.lower()}"
    
    # 1. Cek cache dulu di Redis (Cache-Aside Pattern)
    if r:
        try:
            cached_data = r.get(cache_key)
            if cached_data:
                # Jika ada, langsung kembalikan data dari cache (Sangat Cepat!)
                return json.loads(cached_data)
        except Exception:
            pass

    # 2. Jika tidak ada di cache (Cache Miss), jalankan API call yang lambat
    time.sleep(2)  # Simulasi API lambat dari dosen (2 detik)
    
    try:
        response = requests.get(f"https://api.example.com/weather/{city}", timeout=3)
        data = response.json()
    except Exception:
        # Fallback Mock Data jika internet kampus lambat atau API eksternal offline
        data = {
            "city": city,
            "temperature": "28°C",
            "condition": "Cerah Berawan"
        }
    
    # 3. Simpan hasil data baru tersebut ke cache Redis selama 5 menit (300 detik)
    if r:
        try:
            r.setex(cache_key, 300, json.dumps(data))
        except Exception:
            pass
            
    return data