# ASDI Multi-Role Portal (Student, Teacher, Admin)

ASDI (Asian Skill Development Institute) ka mukammal multi-role portal jahan har user apni zaroorat ke mutabiq strictly apna data dekh sakta hai.

---

## 👥 3 Mukhtalif Roles & Unke Ikhtiyarat

### 1. 🎓 Student Role (Strictly Zaati Record):
- **Access:** Student sirf aur sirf apna record dekh sakta hai.
- **Kya dikhta hai:**
  - Apna Profile, Course, Roll No, Batch.
  - Apni Fee status (Kul fees, jama shuda, baqi balance).
  - Apni digital payment receipts (Raseedein).
  - Apni attendance (Hazri) percentage & log.
  - Apna timetable aur exam results (DMC).
- **Login Credentials:**
  - Admission No (e.g. `ASDI-2026-0001` ya `1`), **YA**
  - Registered Mobile Number (e.g. `0311-8386393`).

---

### 2. 👨‍🏫 Teacher / Staff Role (Apne Students & Unki Fees):
- **Access:** Teacher sirf aur sirf apne assigned students ka record dekh sakta hai.
- **Kya dikhta hai:**
  - Total Assigned Students count.
  - In students ne kul kitni fees jama karwai (Total Collected Fee).
  - Teacher ka share % aur total earning (agar share set ho jaise 75%).
  - Students ki baqi pending fees.
  - Assigned students ki poori list (Searchable by Name / Roll #).
  - Students ki payment receipts ka live feed.
- **Privacy:** Ek teacher doosre teacher ke students ya unki earnings nahi dekh sakta.
- **Login Credentials:**
  - Teacher ka Registered Mobile Number (e.g. `03329854273` for Mam Tayyba, `03451208361` for Sir Qasim) ya Teacher Name.

---

### 3. 🛡️ Admin / Management Role (SUB KUCH):
- **Access:** Pure institute ka mukammal control aur report ("SUB KUCH").
- **Kya dikhta hai:**
  - **KPIs:** Total Students, Active Students, Total Institute Revenue, Pending Receivables, Total Expenses, Net Cash Balance.
  - **All Students Directory:** Institute ke tamam 63+ students ki searchable list, unki fees, roll numbers, aur status.
  - **Faculty Performance:** Har teacher ke kitne students hain, unhone institute ko kitna revenue generate kar ke diya, aur teacher ka share % / payout kitna banta hai.
  - **All Payments Stream:** Tamam 67+ receipts ka complete ledger.
  - **Institute Expenses:** Har qisam ke kharchay (rent, utilities, etc.).
- **Login Credentials:**
  - **Admin Security PIN:** `1234` ya `9999` (Principal PIN).

---

## 🚀 Portal Chalane Ka Tareeqa

1. `asdi_student_portal` folder mein jayein.
2. `run_portal.bat` par double-click karein.
3. Mobile phone ya computer par link kholein:
   - **Local Computer:** `http://localhost:5000`
   - **Mobile Phone (Same Wi-Fi):** `http://192.168.18.21:5000`
