"""Create the SQLite demo database used by the live demo.

All hospitals, doctors and stock levels are fictional.
Usage: python deploy/seed_demo_db.py demo/hospital.db
"""

import os
import sqlite3
import sys

HOSPITALS = [
    (1, "Hôpital Central de Tunis", "Tunis", 420, 37),
    (2, "Clinique du Lac", "Tunis", 120, 12),
    (3, "Hôpital Régional de Sfax", "Sfax", 350, 54),
    (4, "Centre Hospitalier de Sousse", "Sousse", 280, 9),
    (5, "Clinique Les Oliviers", "Nabeul", 90, 21),
]

DOCTORS = [
    (1, "Dr. Amira Ben Salah", "Cardiology", 1, "Mon, Wed, Fri"),
    (2, "Dr. Karim Trabelsi", "Cardiology", 3, "Tue, Thu"),
    (3, "Dr. Leila Haddad", "Pulmonology", 1, "Mon, Tue, Thu"),
    (4, "Dr. Youssef Mansour", "Pediatrics", 2, "Mon to Fri"),
    (5, "Dr. Sana Gharbi", "Neurology", 4, "Wed, Sat"),
    (6, "Dr. Mehdi Jaziri", "Endocrinology", 3, "Mon, Thu"),
    (7, "Dr. Ines Chaabane", "Dermatology", 5, "Tue, Fri"),
    (8, "Dr. Omar Belhadj", "Orthopedics", 4, "Mon, Wed"),
    (9, "Dr. Rim Ayari", "Pulmonology", 3, "Fri, Sat"),
    (10, "Dr. Hatem Kefi", "General Medicine", 2, "Mon to Sat"),
]

ILLNESSES = [
    (1, "Hypertension", "Persistently high blood pressure", "Cardiology"),
    (2, "Asthma", "Chronic inflammation of the airways", "Pulmonology"),
    (3, "Type 2 diabetes", "Insulin resistance and high blood sugar", "Endocrinology"),
    (4, "Migraine", "Recurrent severe headaches", "Neurology"),
    (5, "Eczema", "Inflamed, itchy skin", "Dermatology"),
    (6, "Bronchiolitis", "Viral lung infection in infants", "Pediatrics"),
]

MEDICATIONS = [
    (1, "Amlodipine", 1, "5-10 mg once daily", 640),
    (2, "Lisinopril", 1, "10-40 mg once daily", 0),
    (3, "Salbutamol inhaler", 2, "1-2 puffs as needed", 310),
    (4, "Budesonide inhaler", 2, "200-400 µg twice daily", 95),
    (5, "Metformin", 3, "500-1000 mg twice daily", 1200),
    (6, "Sumatriptan", 4, "50 mg at onset", 140),
    (7, "Hydrocortisone cream", 5, "Apply twice daily", 220),
    (8, "Paracetamol syrup", 6, "15 mg/kg every 6 hours", 480),
]


def main(path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE hospitals (id INTEGER PRIMARY KEY, name TEXT, city TEXT,
                                total_beds INTEGER, available_beds INTEGER);
        CREATE TABLE doctors (id INTEGER PRIMARY KEY, name TEXT, specialty TEXT,
                              hospital_id INTEGER REFERENCES hospitals(id), available_days TEXT);
        CREATE TABLE illnesses (id INTEGER PRIMARY KEY, name TEXT, description TEXT, specialty TEXT);
        CREATE TABLE medications (id INTEGER PRIMARY KEY, name TEXT,
                                  illness_id INTEGER REFERENCES illnesses(id), dosage TEXT, units_in_stock INTEGER);
    """)
    con.executemany("INSERT INTO hospitals VALUES (?,?,?,?,?)", HOSPITALS)
    con.executemany("INSERT INTO doctors VALUES (?,?,?,?,?)", DOCTORS)
    con.executemany("INSERT INTO illnesses VALUES (?,?,?,?)", ILLNESSES)
    con.executemany("INSERT INTO medications VALUES (?,?,?,?,?)", MEDICATIONS)
    con.commit()
    con.close()
    print(f"Demo database written to {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "demo/hospital.db")
