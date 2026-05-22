# README - Implementasi Project Monitoring MikroTik ke Router Lain

Dokumentasi ini dibuat khusus sebagai catatan tambahan ketika project **Grafana Monitoring MikroTik + Prometheus + SNMP Exporter + Alertmanager + Webhook Telegram** ingin dipakai untuk MikroTik lain.

File ini **tidak menggantikan README utama**. README utama tetap dipakai untuk dokumentasi full project dari awal. File ini hanya fokus pada skenario:

```text
1. Mengganti MikroTik lama ke MikroTik baru
2. Menambahkan MikroTik lain
3. Menyesuaikan IP target MikroTik di Prometheus
4. Mengecek SNMP, Prometheus, Grafana, dan alert Telegram setelah pindah router
```

---

## 1. Inti Jawaban

Jika project sudah berjalan dan ingin dipakai untuk MikroTik lain, yang paling utama diubah adalah:

```text
prometheus/prometheus.yml
```

Bukan `docker-compose.yml`.

Contoh kondisi awal:

```text
MikroTik lama : 192.168.88.1
MikroTik baru : 192.168.87.1
```

Maka ubah semua target MikroTik di `prometheus/prometheus.yml` dari:

```yaml
- 192.168.88.1
```

menjadi:

```yaml
- 192.168.87.1
```

Setelah itu restart Prometheus.

---

## 2. File yang Perlu dan Tidak Perlu Diubah

| File | Perlu Diubah? | Keterangan |
|---|---:|---|
| `docker-compose.yml` | Tidak wajib | Service container tetap sama |
| `prometheus/prometheus.yml` | Wajib | Di sinilah IP target MikroTik disimpan |
| `snmp-exporter/snmp.yml` | Tidak wajib | Tidak perlu diubah jika community tetap sama |
| `alertmanager/alertmanager.yml` | Tidak wajib | Tetap mengarah ke webhook receiver |
| `webhook-receiver/.env` | Tidak wajib | Token bot Telegram tetap sama |
| `grafana/data/grafana.db` | Tidak wajib | Dashboard lama tetap bisa dipakai |
| `grafana/dashboards/*.json` | Opsional | Hanya jika ingin export/import dashboard |

Kesimpulan sederhananya:

```text
docker-compose.yml        : biarkan
snmp-exporter/snmp.yml    : biarkan kalau community sama
alertmanager.yml          : biarkan
webhook-receiver/.env     : biarkan
prometheus/prometheus.yml : ubah IP MikroTik di bagian targets
```

---

## 3. Syarat MikroTik Baru Sebelum Dimasukkan ke Prometheus

Sebelum mengganti IP di Prometheus, pastikan MikroTik baru sudah memenuhi syarat berikut:

```text
1. MikroTik baru bisa diping dari WSL Ubuntu / server monitoring
2. SNMP di MikroTik baru sudah aktif
3. Community SNMP sama dengan konfigurasi SNMP Exporter
4. UDP port 161 tidak diblok firewall MikroTik
5. IP monitoring server diizinkan oleh SNMP community MikroTik
```

Community yang dipakai di project ini:

```text
monitoring123
```

---

## 4. Cek Koneksi ke MikroTik Baru

Misalkan IP MikroTik baru adalah:

```text
192.168.87.1
```

Dari WSL Ubuntu / server monitoring, jalankan:

```bash
ping -c 4 192.168.87.1
```

Jika berhasil, contoh outputnya kira-kira seperti ini:

```text
64 bytes from 192.168.87.1: icmp_seq=1 ttl=64 time=1.2 ms
64 bytes from 192.168.87.1: icmp_seq=2 ttl=64 time=1.0 ms
```

Jika ping gagal, jangan lanjut dulu ke Prometheus. Perbaiki dulu koneksi jaringan antara WSL/server monitoring dan MikroTik baru.

---

## 5. Aktifkan SNMP di MikroTik Baru

Masuk ke MikroTik baru lewat WinBox, lalu buka:

```text
New Terminal
```

Jalankan:

```rsc
/snmp set enabled=yes contact="admin" location="Monitoring MikroTik Baru"
```

Cek status SNMP:

```rsc
/snmp print
```

Pastikan:

```text
enabled: yes
```

---

## 6. Buat atau Update Community SNMP

Community harus sesuai dengan yang ada di `snmp-exporter/snmp.yml`.

Pada project ini community-nya:

```text
monitoring123
```

Jika belum ada, buat community:

```rsc
/snmp community add name=monitoring123 addresses=192.168.87.0/24 read-access=yes write-access=no
```

Jika community sudah ada, update saja:

```rsc
/snmp community set [find name="monitoring123"] addresses=192.168.87.0/24 read-access=yes write-access=no
```

### Catatan Penting tentang `addresses`

Bagian `addresses` adalah IP atau subnet yang diizinkan untuk melakukan request SNMP ke MikroTik.

Jadi yang harus masuk ke `addresses` adalah IP/subnet dari **server monitoring**, bukan asal isi IP router.

Contoh:

| Kondisi | Contoh `addresses` |
|---|---|
| WSL/server monitoring ada di subnet `192.168.87.0/24` | `192.168.87.0/24` |
| WSL/server monitoring ada di subnet `192.168.88.0/24` | `192.168.88.0/24` |
| IP server monitoring spesifik `192.168.87.10` | `192.168.87.10/32` |
| Testing sementara | `0.0.0.0/0` |

Untuk testing sementara boleh:

```rsc
/snmp community set [find name="monitoring123"] addresses=0.0.0.0/0 read-access=yes write-access=no
```

Setelah berhasil, sebaiknya kunci lagi ke IP/subnet monitoring server:

```rsc
/snmp community set [find name="monitoring123"] addresses=192.168.87.0/24 read-access=yes write-access=no
```

Jangan membuka SNMP ke publik internet.

---

## 7. Allow Firewall MikroTik untuk SNMP

Jika firewall MikroTik aktif, izinkan SNMP UDP 161 dari jaringan monitoring.

Contoh jika server monitoring ada di subnet `192.168.87.0/24`:

```rsc
/ip firewall filter add chain=input protocol=udp dst-port=161 src-address=192.168.87.0/24 action=accept comment="Allow SNMP from monitoring subnet"
```

Jika server monitoring memakai IP spesifik misalnya `192.168.87.10`:

```rsc
/ip firewall filter add chain=input protocol=udp dst-port=161 src-address=192.168.87.10 action=accept comment="Allow SNMP from monitoring server"
```

SNMP memakai:

```text
Protocol : UDP
Port     : 161
```

---

## 8. Test SNMP dari WSL / Server Monitoring

Install tool SNMP jika belum ada:

```bash
sudo apt update
sudo apt install -y snmp
```

Test ke MikroTik baru:

```bash
snmpwalk -v2c -c monitoring123 192.168.87.1 1.3.6.1.2.1.1.1.0
```

Jika berhasil, biasanya muncul informasi RouterOS, contoh:

```text
iso.3.6.1.2.1.1.1.0 = STRING: "RouterOS RB941-2nD"
```

Jika timeout, kemungkinan:

```text
1. SNMP belum aktif
2. Community salah
3. Firewall MikroTik belum allow UDP 161
4. addresses di SNMP community belum mengizinkan IP server monitoring
5. MikroTik tidak bisa dijangkau dari WSL/server
```

---

## 9. Skenario A - Mengganti MikroTik Lama ke MikroTik Baru

Skenario ini dipakai jika ingin dashboard yang sama dipakai untuk router baru saja.

Contoh:

```text
Dari : 192.168.88.1
Ke   : 192.168.87.1
```

Edit file:

```bash
nano prometheus/prometheus.yml
```

Cari semua target yang masih:

```yaml
- 192.168.88.1
```

Ubah menjadi:

```yaml
- 192.168.87.1
```

Karena project ini menggunakan beberapa job MikroTik, pastikan IP diganti pada semua job berikut:

```text
mikrotik_snmp
mikrotik_uptime
mikrotik_cpu
mikrotik_memory
```

Jika masih ada job tambahan seperti `mikrotik_health`, ganti juga IP di job tersebut.

---

## 10. Contoh Update Job `mikrotik_snmp`

Sebelum:

```yaml
  - job_name: "mikrotik_snmp"
    scrape_interval: 5s
    scrape_timeout: 4s
    metrics_path: /snmp
    params:
      module:
        - if_mib
      auth:
        - public_v2
    static_configs:
      - targets:
          - 192.168.88.1
        labels:
          router: "mikrotik_hap_lite"
          location: "lab_wsl"
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target

      - source_labels: [__param_target]
        target_label: instance

      - target_label: __address__
        replacement: snmp_exporter:9116
```

Sesudah:

```yaml
  - job_name: "mikrotik_snmp"
    scrape_interval: 5s
    scrape_timeout: 4s
    metrics_path: /snmp
    params:
      module:
        - if_mib
      auth:
        - public_v2
    static_configs:
      - targets:
          - 192.168.87.1
        labels:
          router: "mikrotik_baru"
          location: "lab_wsl"
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target

      - source_labels: [__param_target]
        target_label: instance

      - target_label: __address__
        replacement: snmp_exporter:9116
```

Yang berubah:

```text
targets : dari 192.168.88.1 menjadi 192.168.87.1
router  : dari mikrotik_hap_lite menjadi mikrotik_baru
```

Label `router` bebas, hanya untuk penanda di Prometheus/Grafana/Telegram alert.

---

## 11. Contoh Update Job `mikrotik_uptime`

```yaml
  - job_name: "mikrotik_uptime"
    scrape_interval: 5s
    scrape_timeout: 4s
    metrics_path: /snmp
    params:
      module:
        - mikrotik_uptime
      auth:
        - public_v2
    static_configs:
      - targets:
          - 192.168.87.1
        labels:
          router: "mikrotik_baru"
          location: "lab_wsl"
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target

      - source_labels: [__param_target]
        target_label: instance

      - target_label: __address__
        replacement: snmp_exporter:9116
```

---

## 12. Contoh Update Job `mikrotik_cpu`

```yaml
  - job_name: "mikrotik_cpu"
    scrape_interval: 5s
    scrape_timeout: 4s
    metrics_path: /snmp
    params:
      module:
        - mikrotik_cpu
      auth:
        - public_v2
    static_configs:
      - targets:
          - 192.168.87.1
        labels:
          router: "mikrotik_baru"
          location: "lab_wsl"
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target

      - source_labels: [__param_target]
        target_label: instance

      - target_label: __address__
        replacement: snmp_exporter:9116
```

---

## 13. Contoh Update Job `mikrotik_memory`

```yaml
  - job_name: "mikrotik_memory"
    scrape_interval: 5s
    scrape_timeout: 4s
    metrics_path: /snmp
    params:
      module:
        - mikrotik_memory
      auth:
        - public_v2
    static_configs:
      - targets:
          - 192.168.87.1
        labels:
          router: "mikrotik_baru"
          location: "lab_wsl"
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target

      - source_labels: [__param_target]
        target_label: instance

      - target_label: __address__
        replacement: snmp_exporter:9116
```

---

## 14. Validasi Konfigurasi Prometheus

Setelah mengubah `prometheus/prometheus.yml`, jangan langsung panik restart. Validasi dulu:

```bash
docker exec -it mikrotik_prometheus promtool check config /etc/prometheus/prometheus.yml
```

Jika berhasil, outputnya biasanya:

```text
SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax
```

Lalu restart Prometheus:

```bash
docker compose restart prometheus
```

Cek log jika perlu:

```bash
docker logs mikrotik_prometheus --tail=80
```

---

## 15. Cek Target Prometheus

Buka:

```text
http://localhost:9090/targets
```

Pastikan job berikut statusnya `UP`:

```text
mikrotik_snmp
mikrotik_uptime
mikrotik_cpu
mikrotik_memory
```

Jika semua sudah `UP`, berarti Prometheus sudah membaca MikroTik baru.

Cek query:

```promql
up{job="mikrotik_snmp"}
```

Hasil yang diharapkan:

```text
1
```

---

## 16. Test SNMP Exporter Manual

Test interface metric:

```bash
curl "http://localhost:9116/snmp?target=192.168.87.1&module=if_mib&auth=public_v2" | head
```

Test uptime:

```bash
curl -s "http://localhost:9116/snmp?target=192.168.87.1&module=mikrotik_uptime&auth=public_v2" | grep uptime
```

Test CPU:

```bash
curl -s "http://localhost:9116/snmp?target=192.168.87.1&module=mikrotik_cpu&auth=public_v2" | grep mikrotik_cpu
```

Test memory:

```bash
curl -s "http://localhost:9116/snmp?target=192.168.87.1&module=mikrotik_memory&auth=public_v2" | grep mikrotik_memory
```

Jika command di atas mengeluarkan metrics, berarti SNMP Exporter sudah aman.

---

## 17. Skenario B - Menambahkan MikroTik Baru Tanpa Menghapus MikroTik Lama

Skenario ini dipakai jika ingin monitoring banyak MikroTik sekaligus.

Contoh:

```text
MikroTik 1 : 192.168.88.1
MikroTik 2 : 192.168.87.1
```

Jangan hapus IP lama. Tambahkan IP baru di `targets`.

Contoh sederhana:

```yaml
static_configs:
  - targets:
      - 192.168.88.1
      - 192.168.87.1
    labels:
      location: "multi_router"
```

Namun cara yang lebih rapi adalah memberi label router berbeda.

Contoh:

```yaml
static_configs:
  - targets:
      - 192.168.88.1
    labels:
      router: "mikrotik_lama"
      location: "rumah"

  - targets:
      - 192.168.87.1
    labels:
      router: "mikrotik_baru"
      location: "kantor"
```

Terapkan pola tersebut pada semua job MikroTik:

```text
mikrotik_snmp
mikrotik_uptime
mikrotik_cpu
mikrotik_memory
```

---

## 18. Contoh Multi-Router untuk Job `mikrotik_snmp`

```yaml
  - job_name: "mikrotik_snmp"
    scrape_interval: 5s
    scrape_timeout: 4s
    metrics_path: /snmp
    params:
      module:
        - if_mib
      auth:
        - public_v2
    static_configs:
      - targets:
          - 192.168.88.1
        labels:
          router: "mikrotik_rumah"
          location: "rumah"

      - targets:
          - 192.168.87.1
        labels:
          router: "mikrotik_kantor"
          location: "kantor"
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target

      - source_labels: [__param_target]
        target_label: instance

      - target_label: __address__
        replacement: snmp_exporter:9116
```

Dengan konfigurasi di atas:

```text
instance = 192.168.88.1 atau 192.168.87.1
router   = mikrotik_rumah atau mikrotik_kantor
location = rumah atau kantor
```

---

## 19. Dampak ke Grafana

Jika hanya mengganti IP dari `192.168.88.1` ke `192.168.87.1`, dashboard Grafana biasanya langsung ikut jalan karena query-nya memakai `job`.

Contoh query yang tetap aman:

```promql
up{job="mikrotik_snmp"}
```

```promql
avg(mikrotik_cpu_load_percent{job="mikrotik_cpu"})
```

```promql
mikrotik_sys_uptime_seconds{job="mikrotik_uptime"}
```

Tetapi kalau monitoring banyak MikroTik sekaligus, sebaiknya dashboard Grafana ditambah variable agar bisa memilih router.

---

## 20. Membuat Variable Router di Grafana untuk Multi-Router

Masuk ke dashboard Grafana:

```text
Dashboard settings > Variables > New variable
```

Isi:

```text
Name        : router
Type        : Query
Data source : Prometheus
Query       : label_values(up{job="mikrotik_snmp"}, instance)
Refresh     : On dashboard load
```

Lalu pada query panel Grafana, tambahkan filter:

```promql
up{job="mikrotik_snmp", instance="$router"}
```

Contoh download per interface:

```promql
rate(ifHCInOctets{job="mikrotik_snmp", instance="$router"}[30s]) * 8
```

Contoh upload per interface:

```promql
rate(ifHCOutOctets{job="mikrotik_snmp", instance="$router"}[30s]) * 8
```

Contoh uptime:

```promql
mikrotik_sys_uptime_seconds{job="mikrotik_uptime", instance="$router"}
```

Contoh CPU:

```promql
avg(mikrotik_cpu_load_percent{job="mikrotik_cpu", instance="$router"})
```

Contoh memory:

```promql
avg(
  (
    mikrotik_memory_used_units{job="mikrotik_memory", instance="$router"}
    /
    mikrotik_memory_total_units{job="mikrotik_memory", instance="$router"}
  ) * 100
)
```

Dengan variable ini, dashboard bisa dipakai untuk memilih router mana yang ingin dilihat.

---

## 21. Dampak ke Alert Telegram

Alert Telegram tetap jalan karena alurnya tetap sama:

```text
Prometheus Alert Rules
↓
Alertmanager
↓
Webhook Receiver
↓
Telegram Bot
```

Jika alert rule memakai `instance`, maka pesan Telegram akan otomatis membawa IP router yang bermasalah.

Contoh rule router down:

```yaml
groups:
  - name: mikrotik-alerts
    rules:
      - alert: MikroTikRouterDown
        expr: up{job="mikrotik_snmp"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "MikroTik router down"
          description: "Router {{ $labels.instance }} tidak bisa diakses oleh Prometheus selama lebih dari 1 menit."
```

Jika ada 2 router:

```text
192.168.88.1
192.168.87.1
```

Lalu `192.168.87.1` down, maka alert akan mengarah ke instance tersebut.

---

## 22. Validasi Alert Telegram Setelah Ganti Router

Untuk memastikan alert Telegram tetap jalan:

1. Pastikan Prometheus target router baru sudah `UP`.
2. Matikan sementara MikroTik baru atau cabut koneksi jaringan.
3. Tunggu sesuai rule alert, misalnya `for: 1m`.
4. Cek halaman Alertmanager:

```text
http://localhost:9093
```

5. Cek group Telegram.

Jika alert masuk, berarti alur ini berhasil:

```text
MikroTik Baru Down
↓
Prometheus membaca up = 0
↓
Alertmanager menerima alert
↓
Webhook receiver menerima POST alert
↓
Telegram Bot mengirim pesan ke group
```

---

## 23. Troubleshooting

### 23.1 Prometheus Target DOWN

Cek target:

```text
http://localhost:9090/targets
```

Cek log Prometheus:

```bash
docker logs mikrotik_prometheus --tail=80
```

Cek SNMP Exporter langsung:

```bash
curl "http://localhost:9116/snmp?target=192.168.87.1&module=if_mib&auth=public_v2" | head
```

Jika curl gagal, masalah ada di jalur:

```text
SNMP Exporter → MikroTik baru
```

Kemungkinan penyebab:

```text
1. IP MikroTik salah
2. MikroTik tidak bisa diping
3. SNMP belum aktif
4. Community salah
5. UDP 161 diblok firewall
6. addresses di SNMP community salah
```

---

### 23.2 SNMPWalk Timeout

Command:

```bash
snmpwalk -v2c -c monitoring123 192.168.87.1 1.3.6.1.2.1.1.1.0
```

Jika timeout:

```text
- Cek ping ke MikroTik
- Cek SNMP enabled
- Cek community monitoring123
- Cek firewall input UDP 161
- Cek allowed addresses pada SNMP community
```

---

### 23.3 CPU atau Memory No Data

Jika CPU no data:

```bash
curl -s "http://localhost:9116/snmp?target=192.168.87.1&module=mikrotik_cpu&auth=public_v2" | grep -E "mikrotik_cpu|error"
```

Jika memory no data:

```bash
curl -s "http://localhost:9116/snmp?target=192.168.87.1&module=mikrotik_memory&auth=public_v2" | grep -E "mikrotik_memory|error"
```

Kemungkinan:

```text
1. Router baru tidak support OID yang sama
2. RouterOS berbeda versi
3. SNMP Exporter module perlu disesuaikan
4. Metric muncul tetapi storage_index berbeda
```

Untuk cek OID CPU:

```bash
snmpwalk -v2c -c monitoring123 192.168.87.1 1.3.6.1.2.1.25.3.3.1.2
```

Untuk cek OID memory:

```bash
snmpwalk -v2c -c monitoring123 192.168.87.1 1.3.6.1.2.1.25.2.3.1.3
snmpwalk -v2c -c monitoring123 192.168.87.1 1.3.6.1.2.1.25.2.3.1.5
snmpwalk -v2c -c monitoring123 192.168.87.1 1.3.6.1.2.1.25.2.3.1.6
```

---

### 23.4 Grafana Masih Menampilkan Router Lama

Coba cek query panel. Jika query panel mengunci instance lama seperti ini:

```promql
up{job="mikrotik_snmp", instance="192.168.88.1"}
```

Ubah menjadi IP baru:

```promql
up{job="mikrotik_snmp", instance="192.168.87.1"}
```

Atau lebih fleksibel pakai variable:

```promql
up{job="mikrotik_snmp", instance="$router"}
```

Jika query hanya memakai `job`, biasanya tidak perlu diubah:

```promql
up{job="mikrotik_snmp"}
```

---

### 23.5 Alert Tidak Masuk ke Telegram

Cek status container:

```bash
docker ps
```

Pastikan container berikut hidup:

```text
mikrotik_prometheus
mikrotik_alertmanager
mikrotik_webhook_receiver
```

Cek log:

```bash
docker logs mikrotik_alertmanager --tail=80
docker logs mikrotik_webhook_receiver --tail=80
```

Cek Alertmanager:

```text
http://localhost:9093
```

Cek apakah alert sudah firing di Prometheus:

```text
http://localhost:9090/alerts
```

Jika alert firing di Prometheus tetapi tidak masuk Telegram, kemungkinan masalah ada di:

```text
Prometheus → Alertmanager → Webhook Receiver → Telegram Bot
```

---

## 24. Checklist Cepat Ganti MikroTik

Gunakan checklist ini setiap ingin pindah router.

```text
[ ] IP MikroTik baru sudah diketahui
[ ] MikroTik baru bisa diping dari WSL/server monitoring
[ ] SNMP MikroTik baru sudah enabled
[ ] Community SNMP sama: monitoring123
[ ] Firewall MikroTik allow UDP 161
[ ] snmpwalk ke MikroTik baru berhasil
[ ] prometheus/prometheus.yml sudah diganti IP targetnya
[ ] Semua job MikroTik sudah diganti IP-nya
[ ] promtool check config berhasil
[ ] docker compose restart prometheus sudah dijalankan
[ ] Prometheus target sudah UP
[ ] Grafana sudah menampilkan data router baru
[ ] Alert Telegram sudah dites
```

---

## 25. Perintah Cepat

Masuk folder project:

```bash
cd ~/grafana_monitoring_mikrotik
```

Edit Prometheus:

```bash
nano prometheus/prometheus.yml
```

Validasi config:

```bash
docker exec -it mikrotik_prometheus promtool check config /etc/prometheus/prometheus.yml
```

Restart Prometheus:

```bash
docker compose restart prometheus
```

Cek target:

```text
http://localhost:9090/targets
```

Test SNMP:

```bash
snmpwalk -v2c -c monitoring123 192.168.87.1 1.3.6.1.2.1.1.1.0
```

Test SNMP Exporter:

```bash
curl "http://localhost:9116/snmp?target=192.168.87.1&module=if_mib&auth=public_v2" | head
```

Cek alert:

```text
http://localhost:9090/alerts
http://localhost:9093
```

Cek log webhook:

```bash
docker logs mikrotik_webhook_receiver --tail=80
```

---

## 26. Kesimpulan

Untuk implementasi project ini ke MikroTik lain, prinsipnya sederhana:

```text
1. MikroTik baru harus bisa diakses dari server monitoring
2. SNMP MikroTik baru harus aktif
3. Community SNMP harus sama dengan SNMP Exporter
4. IP target di prometheus/prometheus.yml harus diganti atau ditambahkan
5. Prometheus harus divalidasi dan direstart
6. Grafana akan membaca data baru dari Prometheus
7. Alert Telegram tetap jalan selama alert rule dan Alertmanager aktif
```

Jika hanya mengganti router:

```text
192.168.88.1 → 192.168.87.1
```

Maka fokus utama adalah mengganti IP tersebut di semua job MikroTik pada:

```text
prometheus/prometheus.yml
```

Jika ingin multi-router, tambahkan IP baru tanpa menghapus IP lama, lalu gunakan label `router`, `location`, dan variable Grafana agar dashboard lebih rapi.
