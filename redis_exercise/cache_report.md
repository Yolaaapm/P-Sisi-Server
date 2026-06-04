Laporan Praktikum: Redis Caching Exercise

Nama: Fiola Putri Monika
NIM: A11.2023.15413
Mata Kuliah: Pemrograman Sisi Server

1.  Kode Program yang Dimodifikasi (weather_api.py)

Berikut adalah fungsi get_weather bawaan soal yang telah dimodifikasi menggunakan logika Cache-Aside menggunakan Redis DB:

import requests
import time
import redis
import json

# Koneksi ke Redis Client lokal

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def get_weather(city):
cache_key = f"weather:{city.lower()}"

    # 1. Cek cache dulu di Redis
    cached_data = r.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    # 2. Kalau tidak ada (Cache Miss), panggil API asli (simulasi lambat 2 detik)
    time.sleep(2)  # Simulate slow API
    try:
        response = requests.get(f"[https://api.example.com/weather/](https://api.example.com/weather/){city}", timeout=3)
        data = response.json()
    except Exception:
        # Fallback jika API eksternal offline
        data = {
            "city": city,
            "temperature": "28°C",
            "condition": "Cerah Berawan"
        }

    # 3. Simpan ke Redis cache dengan masa aktif 5 menit (300 detik)
    r.setex(cache_key, 300, json.dumps(data))

    return data

2.  Hasil Output Pengujian (test_cache.py)

Berikut adalah bukti tangkapan layar hasil eksekusi pengujian kecepatan respon program:
[Hasil Pengujian Redis Caching](./redis_test.png)

Penjelasan Mengenai Third Call (Setelah 5 Menit):

Jika program dijalankan kembali setelah 5 menit (300 detik), maka pemanggilan data akan menjadi lambat kembali (~2.00 detik).
Hal ini dikarenakan data di dalam database Redis telah melewati batas kedaluwarsa (Time to Live) dan dihapus secara otomatis sesuai konfigurasi waktu penyimpanan setex selama 300 detik. Kondisi ini memaksa program untuk melakukan proses \*Cache Miss kembali dan mengambil data segar dari API luar.

3.  Perintah Redis yang Digunakan

GET weather:jakarta Digunakan untuk memeriksa keberadaan data di memori Redis berdasarkan kata kunci (key).

SETEX weather:jakarta 300 "{data_json}" Digunakan untuk menyimpan data string JSON ke dalam Redis sekaligus mengatur waktu kedalawarsa (Time to Live) selama 300 detik (5 menit).

4.  Jawaban Pertanyaan Dosen

Q1: Kenapa response time pemanggilan pertama dan kedua bisa berbeda?

Pemanggilan Pertama: Membutuhkan waktu 2.01s karena data belum ada di Redis (Cache Miss). Program harus menunggu proses simulasi time.sleep(2) dan request HTTP ke server API luar.

Pemanggilan Kedua: Membutuhkan waktu 0.00s karena data sudah tersimpan di Redis (Cache Hit). Program langsung mengambil data dari RAM lokal tanpa memicu fungsi time.sleep(2) ataupun request HTTP eksternal.

Q2: Apa keuntungan utama menggunakan caching pada aplikasi web?

Peningkatan Kecepatan (Akselerasi): Memotong waktu respon aplikasi dari hitungan detik menjadi milidetik saja (high-speed performance).

Pengurangan Beban Database/Server: Menghindari beban query berulang pada database utama (seperti PostgreSQL) atau API eksternal berbayar.

Skalabilitas Tinggi: Membantu sistem melayani ribuan request per detik secara bersamaan tanpa mengalami kelambatan.

Q3: Kapan sebaiknya kita tidak menggunakan cache untuk data tertentu?

Data Transaksional/Real-time: Data yang wajib up-to-date setiap milidetik seperti saldo rekening bank, kuota tiket konser, atau harga instrumen saham.

Data Rahasia/Sensitif: Informasi akun personal, halaman pembayaran (checkout), atau password demi alasan keamanan privasi data.

Data yang Sangat Jarang Diakses: Menumpuk data yang tidak populer di memori RAM cache hanya akan membuang-buang kapasitas RAM server secara sia-sia.
