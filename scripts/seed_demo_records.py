from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GENERATED_DIR = PROJECT_ROOT / "data" / ".seed_tmp"
MANIFEST_PATH = PROJECT_ROOT / "data" / "demo_seed_manifest.json"

DEFAULT_API_URL = "http://127.0.0.1:8000"
DEFAULT_WALLET_KEY_ENV = "DEMO_WALLET_PRIVATE_KEY"


# ============================================================
# SYNTHETIC RECORD DATA
# ============================================================

RECORDS: list[dict[str, Any]] = [
    {
        "age": 45,
        "gender": "Male",
        "condition": "Primary Hypertension",
        "complaint": "Recurring headaches, dizziness, and fatigue over the past two weeks.",
        "vitals": {
            "Blood Pressure": "158/96 mmHg",
            "Heart Rate": "82 bpm",
            "Temperature": "36.8 C",
            "Oxygen Saturation": "98%",
        },
        "assessment": (
            "Persistently elevated blood pressure consistent with Stage 2 hypertension. "
            "No evidence of acute cardiovascular distress."
        ),
        "medication": "Amlodipine 5 mg orally once daily.",
        "recommendation": (
            "Reduce dietary sodium intake, exercise regularly, monitor blood pressure "
            "at home, and maintain adequate hydration."
        ),
        "follow_up": "Follow-up consultation in four weeks.",
    },
    {
        "age": 57,
        "gender": "Female",
        "condition": "Type 2 Diabetes Mellitus",
        "complaint": "Increased thirst, frequent urination, and persistent fatigue.",
        "vitals": {
            "Blood Pressure": "136/84 mmHg",
            "Heart Rate": "78 bpm",
            "Temperature": "36.7 C",
            "HbA1c": "8.4%",
        },
        "assessment": (
            "Poorly controlled Type 2 diabetes with elevated HbA1c requiring "
            "medication and dietary management."
        ),
        "medication": "Metformin 500 mg orally twice daily with meals.",
        "recommendation": (
            "Reduce refined carbohydrates, maintain regular physical activity, "
            "and monitor fasting glucose."
        ),
        "follow_up": "Repeat HbA1c and clinical review in three months.",
    },
    {
        "age": 29,
        "gender": "Male",
        "condition": "Bronchial Asthma",
        "complaint": "Intermittent wheezing and shortness of breath, especially at night.",
        "vitals": {
            "Blood Pressure": "124/78 mmHg",
            "Heart Rate": "88 bpm",
            "Temperature": "36.6 C",
            "Oxygen Saturation": "96%",
        },
        "assessment": "Mild persistent asthma with nocturnal respiratory symptoms.",
        "medication": "Budesonide inhaler 200 mcg twice daily and salbutamol as needed.",
        "recommendation": "Avoid known triggers and use inhaler with correct technique.",
        "follow_up": "Review asthma control in six weeks.",
    },
    {
        "age": 33,
        "gender": "Female",
        "condition": "Migraine Without Aura",
        "complaint": "Recurrent unilateral throbbing headaches with nausea and light sensitivity.",
        "vitals": {
            "Blood Pressure": "118/76 mmHg",
            "Heart Rate": "74 bpm",
            "Temperature": "36.5 C",
            "Neurological Exam": "Normal",
        },
        "assessment": "Clinical features are consistent with episodic migraine without aura.",
        "medication": "Sumatriptan 50 mg orally at onset of severe migraine.",
        "recommendation": "Maintain hydration, regular sleep, and a headache trigger diary.",
        "follow_up": "Neurology review in eight weeks if attacks remain frequent.",
    },
    {
        "age": 62,
        "gender": "Male",
        "condition": "Hyperlipidemia",
        "complaint": "Routine cardiovascular risk assessment with elevated cholesterol.",
        "vitals": {
            "Blood Pressure": "142/86 mmHg",
            "Heart Rate": "76 bpm",
            "LDL Cholesterol": "178 mg/dL",
            "HDL Cholesterol": "41 mg/dL",
        },
        "assessment": "Elevated LDL cholesterol with increased cardiovascular risk.",
        "medication": "Atorvastatin 20 mg orally once nightly.",
        "recommendation": "Adopt a heart-healthy diet and increase aerobic physical activity.",
        "follow_up": "Repeat fasting lipid profile in twelve weeks.",
    },
    {
        "age": 39,
        "gender": "Female",
        "condition": "Iron Deficiency Anemia",
        "complaint": "Fatigue, reduced exercise tolerance, and occasional dizziness.",
        "vitals": {
            "Blood Pressure": "108/70 mmHg",
            "Heart Rate": "92 bpm",
            "Hemoglobin": "9.8 g/dL",
            "Ferritin": "8 ng/mL",
        },
        "assessment": "Laboratory findings are consistent with iron deficiency anemia.",
        "medication": "Ferrous sulfate 325 mg orally once daily.",
        "recommendation": "Increase dietary iron intake and take iron with vitamin C.",
        "follow_up": "Repeat complete blood count in six weeks.",
    },
    {
        "age": 51,
        "gender": "Male",
        "condition": "Gastroesophageal Reflux Disease",
        "complaint": "Burning chest discomfort after meals and sour taste at night.",
        "vitals": {
            "Blood Pressure": "128/80 mmHg",
            "Heart Rate": "72 bpm",
            "Temperature": "36.7 C",
            "Weight": "84 kg",
        },
        "assessment": "Symptoms are consistent with uncomplicated gastroesophageal reflux disease.",
        "medication": "Pantoprazole 40 mg orally once daily before breakfast.",
        "recommendation": "Avoid late meals, spicy foods, excessive caffeine, and lying down after eating.",
        "follow_up": "Review symptoms after four weeks.",
    },
    {
        "age": 42,
        "gender": "Female",
        "condition": "Hypothyroidism",
        "complaint": "Fatigue, cold intolerance, weight gain, and dry skin.",
        "vitals": {
            "Blood Pressure": "116/74 mmHg",
            "Heart Rate": "64 bpm",
            "TSH": "9.6 mIU/L",
            "Free T4": "Low",
        },
        "assessment": "Primary hypothyroidism supported by elevated TSH and reduced free T4.",
        "medication": "Levothyroxine 50 mcg orally every morning.",
        "recommendation": "Take medication on an empty stomach and separate it from iron supplements.",
        "follow_up": "Repeat thyroid function tests in eight weeks.",
    },
    {
        "age": 68,
        "gender": "Male",
        "condition": "Community-Acquired Pneumonia",
        "complaint": "Productive cough, fever, chills, and shortness of breath.",
        "vitals": {
            "Blood Pressure": "126/78 mmHg",
            "Heart Rate": "96 bpm",
            "Temperature": "38.4 C",
            "Oxygen Saturation": "93%",
        },
        "assessment": "Clinical presentation suggests uncomplicated community-acquired pneumonia.",
        "medication": "Amoxicillin-clavulanate 625 mg orally three times daily.",
        "recommendation": "Rest, maintain hydration, and seek urgent care if breathing worsens.",
        "follow_up": "Clinical reassessment in five days.",
    },
    {
        "age": 27,
        "gender": "Female",
        "condition": "Urinary Tract Infection",
        "complaint": "Burning urination, urinary frequency, and lower abdominal discomfort.",
        "vitals": {
            "Blood Pressure": "112/72 mmHg",
            "Heart Rate": "80 bpm",
            "Temperature": "37.1 C",
            "Urinalysis": "Positive leukocyte esterase",
        },
        "assessment": "Symptoms and urinalysis support uncomplicated lower urinary tract infection.",
        "medication": "Nitrofurantoin 100 mg orally twice daily for five days.",
        "recommendation": "Increase water intake and complete the full antibiotic course.",
        "follow_up": "Return if symptoms persist beyond three days.",
    },
    {
        "age": 36,
        "gender": "Male",
        "condition": "Acute Sinusitis",
        "complaint": "Facial pressure, nasal congestion, and thick nasal discharge.",
        "vitals": {
            "Blood Pressure": "122/76 mmHg",
            "Heart Rate": "76 bpm",
            "Temperature": "37.4 C",
            "Oxygen Saturation": "99%",
        },
        "assessment": "Acute rhinosinusitis without evidence of orbital or neurological complication.",
        "medication": "Saline nasal irrigation and paracetamol 500 mg as needed.",
        "recommendation": "Maintain hydration and use steam inhalation for symptom relief.",
        "follow_up": "Review if symptoms worsen or persist beyond ten days.",
    },
    {
        "age": 31,
        "gender": "Female",
        "condition": "Allergic Rhinitis",
        "complaint": "Sneezing, itchy eyes, and clear nasal discharge after dust exposure.",
        "vitals": {
            "Blood Pressure": "114/72 mmHg",
            "Heart Rate": "70 bpm",
            "Temperature": "36.5 C",
            "Oxygen Saturation": "99%",
        },
        "assessment": "Seasonal allergic rhinitis likely triggered by environmental allergens.",
        "medication": "Cetirizine 10 mg orally once daily as required.",
        "recommendation": "Reduce allergen exposure and keep bedding clean.",
        "follow_up": "Review in six weeks if symptoms remain uncontrolled.",
    },
    {
        "age": 59,
        "gender": "Male",
        "condition": "Osteoarthritis of the Knee",
        "complaint": "Progressive knee pain and stiffness while climbing stairs.",
        "vitals": {
            "Blood Pressure": "134/82 mmHg",
            "Heart Rate": "72 bpm",
            "Pain Score": "6/10",
            "BMI": "29.8",
        },
        "assessment": "Clinical findings are consistent with degenerative osteoarthritis of the knee.",
        "medication": "Paracetamol 650 mg orally as needed for pain.",
        "recommendation": "Weight reduction, quadriceps-strengthening exercises, and physiotherapy.",
        "follow_up": "Orthopedic review in eight weeks.",
    },
    {
        "age": 25,
        "gender": "Female",
        "condition": "Vitamin D Deficiency",
        "complaint": "Generalized muscle aches and fatigue.",
        "vitals": {
            "Blood Pressure": "110/70 mmHg",
            "Heart Rate": "72 bpm",
            "Vitamin D": "12 ng/mL",
            "Calcium": "Normal",
        },
        "assessment": "Vitamin D deficiency without evidence of severe metabolic bone disease.",
        "medication": "Cholecalciferol 60,000 IU orally once weekly for eight weeks.",
        "recommendation": "Regular safe sunlight exposure and adequate dietary calcium.",
        "follow_up": "Repeat vitamin D measurement after twelve weeks.",
    },
    {
        "age": 48,
        "gender": "Male",
        "condition": "Acute Bronchitis",
        "complaint": "Persistent cough following an upper respiratory infection.",
        "vitals": {
            "Blood Pressure": "126/80 mmHg",
            "Heart Rate": "82 bpm",
            "Temperature": "37.2 C",
            "Oxygen Saturation": "97%",
        },
        "assessment": "Likely viral acute bronchitis with no evidence of pneumonia.",
        "medication": "Dextromethorphan syrup as needed for troublesome cough.",
        "recommendation": "Rest, hydration, and avoidance of smoke exposure.",
        "follow_up": "Return if fever or shortness of breath develops.",
    },
    {
        "age": 34,
        "gender": "Female",
        "condition": "Atopic Dermatitis",
        "complaint": "Itchy dry patches over the arms and neck.",
        "vitals": {
            "Blood Pressure": "116/74 mmHg",
            "Heart Rate": "68 bpm",
            "Temperature": "36.4 C",
            "Skin Exam": "Dry erythematous patches",
        },
        "assessment": "Mild flare of atopic dermatitis without secondary infection.",
        "medication": "Hydrocortisone 1% cream applied twice daily for seven days.",
        "recommendation": "Use fragrance-free moisturizers and avoid harsh soaps.",
        "follow_up": "Dermatology review if not improved within two weeks.",
    },
    {
        "age": 44,
        "gender": "Male",
        "condition": "Gout",
        "complaint": "Sudden severe pain and swelling of the right great toe.",
        "vitals": {
            "Blood Pressure": "130/84 mmHg",
            "Heart Rate": "86 bpm",
            "Temperature": "37.0 C",
            "Uric Acid": "8.9 mg/dL",
        },
        "assessment": "Acute gout flare involving the first metatarsophalangeal joint.",
        "medication": "Naproxen 500 mg orally twice daily with food for five days.",
        "recommendation": "Increase hydration and reduce high-purine food intake.",
        "follow_up": "Review uric acid management after the acute flare resolves.",
    },
    {
        "age": 52,
        "gender": "Female",
        "condition": "Insomnia",
        "complaint": "Difficulty initiating sleep and frequent nighttime awakening.",
        "vitals": {
            "Blood Pressure": "120/78 mmHg",
            "Heart Rate": "70 bpm",
            "Temperature": "36.6 C",
            "Average Sleep": "4.5 hours/night",
        },
        "assessment": "Chronic insomnia likely associated with poor sleep hygiene and stress.",
        "medication": "Melatonin 3 mg orally thirty minutes before bedtime as needed.",
        "recommendation": "Maintain a fixed sleep schedule and avoid screens before bedtime.",
        "follow_up": "Sleep review in four weeks.",
    },
    {
        "age": 41,
        "gender": "Male",
        "condition": "Lumbar Muscle Strain",
        "complaint": "Lower back pain after lifting a heavy object.",
        "vitals": {
            "Blood Pressure": "128/82 mmHg",
            "Heart Rate": "78 bpm",
            "Temperature": "36.7 C",
            "Pain Score": "7/10",
        },
        "assessment": "Mechanical lower back pain without neurological deficit.",
        "medication": "Ibuprofen 400 mg orally every eight hours as needed with food.",
        "recommendation": "Avoid heavy lifting temporarily and begin gentle stretching.",
        "follow_up": "Review in two weeks if symptoms persist.",
    },
    {
        "age": 30,
        "gender": "Female",
        "condition": "Tension-Type Headache",
        "complaint": "Bilateral pressure-like headache associated with prolonged computer work.",
        "vitals": {
            "Blood Pressure": "112/74 mmHg",
            "Heart Rate": "72 bpm",
            "Temperature": "36.5 C",
            "Neurological Exam": "Normal",
        },
        "assessment": "Symptoms are consistent with episodic tension-type headache.",
        "medication": "Paracetamol 500 mg orally as needed.",
        "recommendation": "Improve workstation ergonomics and take regular screen breaks.",
        "follow_up": "Return if headache pattern changes or becomes more severe.",
    },
    {
        "age": 55,
        "gender": "Male",
        "condition": "Nephrolithiasis",
        "complaint": "Severe intermittent flank pain radiating toward the groin.",
        "vitals": {
            "Blood Pressure": "146/88 mmHg",
            "Heart Rate": "94 bpm",
            "Temperature": "36.8 C",
            "Urinalysis": "Microscopic hematuria",
        },
        "assessment": "Presentation is consistent with uncomplicated ureteric stone disease.",
        "medication": "Tamsulosin 0.4 mg orally once daily and analgesia as required.",
        "recommendation": "Increase fluid intake and strain urine for passage of stone.",
        "follow_up": "Urology review in two weeks.",
    },
    {
        "age": 46,
        "gender": "Female",
        "condition": "Essential Hypertension",
        "complaint": "Elevated home blood pressure readings without acute symptoms.",
        "vitals": {
            "Blood Pressure": "166/100 mmHg",
            "Heart Rate": "80 bpm",
            "Temperature": "36.6 C",
            "BMI": "31.1",
        },
        "assessment": "Poorly controlled hypertension with obesity as an additional risk factor.",
        "medication": "Losartan 50 mg orally once daily.",
        "recommendation": "Weight reduction, sodium restriction, and daily blood pressure logging.",
        "follow_up": "Blood pressure review in three weeks.",
    },
    {
        "age": 63,
        "gender": "Male",
        "condition": "Type 2 Diabetes Mellitus",
        "complaint": "Routine diabetic follow-up with elevated fasting glucose.",
        "vitals": {
            "Blood Pressure": "132/80 mmHg",
            "Heart Rate": "74 bpm",
            "Fasting Glucose": "172 mg/dL",
            "HbA1c": "7.9%",
        },
        "assessment": "Type 2 diabetes above target despite existing lifestyle measures.",
        "medication": "Metformin 1000 mg orally twice daily.",
        "recommendation": "Continue glucose monitoring and reduce high-glycemic-index foods.",
        "follow_up": "Diabetes review in three months.",
    },
    {
        "age": 28,
        "gender": "Female",
        "condition": "Mild Persistent Asthma",
        "complaint": "Exercise-induced wheezing occurring several times each week.",
        "vitals": {
            "Blood Pressure": "110/72 mmHg",
            "Heart Rate": "84 bpm",
            "Oxygen Saturation": "97%",
            "Peak Flow": "Reduced",
        },
        "assessment": "Mild persistent asthma insufficiently controlled with rescue therapy alone.",
        "medication": "Beclomethasone inhaler twice daily with salbutamol rescue inhaler.",
        "recommendation": "Use a spacer and perform peak-flow monitoring.",
        "follow_up": "Review in four weeks.",
    },
    {
        "age": 61,
        "gender": "Male",
        "condition": "Benign Prostatic Hyperplasia",
        "complaint": "Weak urinary stream, nocturia, and urinary hesitancy.",
        "vitals": {
            "Blood Pressure": "130/78 mmHg",
            "Heart Rate": "70 bpm",
            "Temperature": "36.5 C",
            "PSA": "Within expected range",
        },
        "assessment": "Lower urinary tract symptoms consistent with benign prostatic hyperplasia.",
        "medication": "Tamsulosin 0.4 mg orally once daily.",
        "recommendation": "Reduce evening fluid intake and monitor urinary retention symptoms.",
        "follow_up": "Urology review in six weeks.",
    },
    {
        "age": 37,
        "gender": "Female",
        "condition": "Generalized Anxiety Symptoms",
        "complaint": "Persistent worry, muscle tension, and difficulty concentrating.",
        "vitals": {
            "Blood Pressure": "118/76 mmHg",
            "Heart Rate": "86 bpm",
            "Temperature": "36.6 C",
            "Sleep": "Poor",
        },
        "assessment": "Symptoms warrant continued evaluation for generalized anxiety disorder.",
        "medication": "No pharmacological treatment initiated at this visit.",
        "recommendation": "Begin structured relaxation techniques and cognitive behavioral therapy referral.",
        "follow_up": "Mental health review in four weeks.",
    },
    {
        "age": 50,
        "gender": "Male",
        "condition": "Non-Alcoholic Fatty Liver Disease",
        "complaint": "Incidental elevated liver enzymes during routine screening.",
        "vitals": {
            "Blood Pressure": "138/84 mmHg",
            "Heart Rate": "74 bpm",
            "ALT": "68 U/L",
            "BMI": "32.4",
        },
        "assessment": "Metabolic risk factors and laboratory findings are compatible with fatty liver disease.",
        "medication": "No disease-specific medication initiated.",
        "recommendation": "Target gradual weight loss through diet and physical activity.",
        "follow_up": "Repeat liver enzymes in three months.",
    },
    {
        "age": 24,
        "gender": "Female",
        "condition": "Acute Viral Pharyngitis",
        "complaint": "Sore throat, mild fever, and painful swallowing.",
        "vitals": {
            "Blood Pressure": "108/68 mmHg",
            "Heart Rate": "82 bpm",
            "Temperature": "37.8 C",
            "Oxygen Saturation": "99%",
        },
        "assessment": "Clinical findings are most consistent with viral pharyngitis.",
        "medication": "Paracetamol 500 mg orally as needed for pain or fever.",
        "recommendation": "Warm saline gargles, hydration, and adequate rest.",
        "follow_up": "Return if symptoms persist beyond one week.",
    },
    {
        "age": 43,
        "gender": "Male",
        "condition": "Prediabetes",
        "complaint": "Routine metabolic screening due to family history of diabetes.",
        "vitals": {
            "Blood Pressure": "126/82 mmHg",
            "Heart Rate": "72 bpm",
            "Fasting Glucose": "112 mg/dL",
            "HbA1c": "6.1%",
        },
        "assessment": "Laboratory findings fall within the prediabetes range.",
        "medication": "No glucose-lowering medication prescribed.",
        "recommendation": "Weight management and at least 150 minutes of exercise each week.",
        "follow_up": "Repeat HbA1c in six months.",
    },
    {
        "age": 56,
        "gender": "Female",
        "condition": "Osteoporosis",
        "complaint": "Low bone density detected during screening.",
        "vitals": {
            "Blood Pressure": "122/76 mmHg",
            "Heart Rate": "70 bpm",
            "DEXA T Score": "-2.7",
            "Vitamin D": "24 ng/mL",
        },
        "assessment": "Bone mineral density meets diagnostic criteria for osteoporosis.",
        "medication": "Alendronate 70 mg orally once weekly.",
        "recommendation": "Adequate calcium and vitamin D intake with weight-bearing exercise.",
        "follow_up": "Bone health review in six months.",
    },
    {
        "age": 38,
        "gender": "Male",
        "condition": "Seborrheic Dermatitis",
        "complaint": "Flaking and itching of the scalp.",
        "vitals": {
            "Blood Pressure": "120/76 mmHg",
            "Heart Rate": "68 bpm",
            "Temperature": "36.5 C",
            "Skin Exam": "Scalp scaling",
        },
        "assessment": "Findings are consistent with mild seborrheic dermatitis.",
        "medication": "Ketoconazole 2% shampoo twice weekly.",
        "recommendation": "Avoid scratching and use gentle scalp-care products.",
        "follow_up": "Review after four weeks if symptoms continue.",
    },
    {
        "age": 49,
        "gender": "Female",
        "condition": "Carpal Tunnel Syndrome",
        "complaint": "Nighttime tingling and numbness of the thumb, index, and middle fingers.",
        "vitals": {
            "Blood Pressure": "124/80 mmHg",
            "Heart Rate": "72 bpm",
            "Grip Strength": "Mildly reduced",
            "Phalen Test": "Positive",
        },
        "assessment": "Symptoms are consistent with median nerve compression at the wrist.",
        "medication": "No systemic medication required.",
        "recommendation": "Night wrist splint and ergonomic modifications.",
        "follow_up": "Review in six weeks.",
    },
    {
        "age": 35,
        "gender": "Male",
        "condition": "Acute Gastritis",
        "complaint": "Upper abdominal burning and nausea after frequent NSAID use.",
        "vitals": {
            "Blood Pressure": "122/78 mmHg",
            "Heart Rate": "76 bpm",
            "Temperature": "36.6 C",
            "Abdominal Exam": "Mild epigastric tenderness",
        },
        "assessment": "Likely NSAID-associated acute gastritis without gastrointestinal bleeding.",
        "medication": "Omeprazole 20 mg orally once daily.",
        "recommendation": "Stop unnecessary NSAIDs and avoid alcohol and irritating foods.",
        "follow_up": "Review in two weeks.",
    },
    {
        "age": 40,
        "gender": "Female",
        "condition": "Irritable Bowel Syndrome",
        "complaint": "Intermittent abdominal cramping with alternating constipation and loose stools.",
        "vitals": {
            "Blood Pressure": "116/72 mmHg",
            "Heart Rate": "70 bpm",
            "Temperature": "36.5 C",
            "Weight": "Stable",
        },
        "assessment": "Symptoms are compatible with irritable bowel syndrome without alarm features.",
        "medication": "Mebeverine 135 mg orally as needed before meals.",
        "recommendation": "Keep a food-symptom diary and increase soluble fiber gradually.",
        "follow_up": "Gastroenterology review in eight weeks.",
    },
    {
        "age": 65,
        "gender": "Male",
        "condition": "Chronic Obstructive Pulmonary Disease",
        "complaint": "Chronic productive cough and gradually increasing exertional breathlessness.",
        "vitals": {
            "Blood Pressure": "132/78 mmHg",
            "Heart Rate": "84 bpm",
            "Oxygen Saturation": "94%",
            "Smoking History": "35 pack-years",
        },
        "assessment": "Stable COPD with chronic respiratory symptoms.",
        "medication": "Tiotropium inhaler 18 mcg once daily.",
        "recommendation": "Smoking cessation, pulmonary rehabilitation, and annual influenza vaccination.",
        "follow_up": "Respiratory review in eight weeks.",
    },
    {
        "age": 54,
        "gender": "Female",
        "condition": "Hypertension",
        "complaint": "Routine review after previously elevated clinic blood pressure.",
        "vitals": {
            "Blood Pressure": "150/92 mmHg",
            "Heart Rate": "76 bpm",
            "Temperature": "36.5 C",
            "Kidney Function": "Normal",
        },
        "assessment": "Persistent hypertension despite lifestyle modification.",
        "medication": "Amlodipine 10 mg orally once daily.",
        "recommendation": "Continue home blood pressure monitoring and sodium restriction.",
        "follow_up": "Review in four weeks.",
    },
    {
        "age": 32,
        "gender": "Male",
        "condition": "Acute Conjunctivitis",
        "complaint": "Redness, irritation, and watery discharge from both eyes.",
        "vitals": {
            "Blood Pressure": "118/74 mmHg",
            "Heart Rate": "72 bpm",
            "Temperature": "36.7 C",
            "Vision": "Preserved",
        },
        "assessment": "Likely viral conjunctivitis without visual impairment.",
        "medication": "Lubricating eye drops as required.",
        "recommendation": "Frequent hand washing and avoid sharing towels.",
        "follow_up": "Urgent review if pain or visual changes develop.",
    },
    {
        "age": 47,
        "gender": "Female",
        "condition": "Hyperlipidemia",
        "complaint": "Follow-up for elevated LDL cholesterol.",
        "vitals": {
            "Blood Pressure": "126/78 mmHg",
            "Heart Rate": "72 bpm",
            "LDL Cholesterol": "162 mg/dL",
            "Triglycerides": "196 mg/dL",
        },
        "assessment": "Mixed dyslipidemia requiring risk-factor modification and statin therapy.",
        "medication": "Rosuvastatin 10 mg orally once daily.",
        "recommendation": "Reduce saturated fat intake and increase regular aerobic exercise.",
        "follow_up": "Repeat lipid profile in twelve weeks.",
    },
    {
        "age": 58,
        "gender": "Male",
        "condition": "Peripheral Neuropathy Associated With Diabetes",
        "complaint": "Burning and tingling sensation in both feet, worse at night.",
        "vitals": {
            "Blood Pressure": "134/82 mmHg",
            "Heart Rate": "74 bpm",
            "HbA1c": "8.2%",
            "Foot Exam": "Reduced distal sensation",
        },
        "assessment": "Distal symmetric sensory neuropathy associated with poorly controlled diabetes.",
        "medication": "Pregabalin 75 mg orally at night.",
        "recommendation": "Improve glucose control and perform daily foot inspection.",
        "follow_up": "Review neuropathic symptoms in six weeks.",
    },
    {
        "age": 26,
        "gender": "Female",
        "condition": "Polycystic Ovary Syndrome",
        "complaint": "Irregular menstrual cycles, acne, and gradual weight gain.",
        "vitals": {
            "Blood Pressure": "118/74 mmHg",
            "Heart Rate": "72 bpm",
            "BMI": "28.2",
            "Fasting Glucose": "101 mg/dL",
        },
        "assessment": "Clinical features are compatible with polycystic ovary syndrome.",
        "medication": "Metformin 500 mg orally once daily initially.",
        "recommendation": "Weight management through diet and regular physical activity.",
        "follow_up": "Gynecology review in three months.",
    },
    {
        "age": 60,
        "gender": "Male",
        "condition": "Hypertension With Type 2 Diabetes",
        "complaint": "Routine chronic disease follow-up.",
        "vitals": {
            "Blood Pressure": "154/94 mmHg",
            "Heart Rate": "76 bpm",
            "HbA1c": "7.5%",
            "Creatinine": "Normal",
        },
        "assessment": "Hypertension remains above target in a patient with Type 2 diabetes.",
        "medication": "Losartan 50 mg once daily and metformin 500 mg twice daily.",
        "recommendation": "Home blood pressure and glucose monitoring with dietary sodium reduction.",
        "follow_up": "Review both blood pressure and glucose control in four weeks.",
    },
]


# ============================================================
# PDF GENERATION
# ============================================================

def wrap_text(text: str, font_name: str, font_size: int, max_width: float) -> list[str]:
    words = text.split()

    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]

    for word in words[1:]:
        candidate = f"{current} {word}"

        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines


def draw_wrapped(
    pdf: canvas.Canvas,
    text: str,
    y: float,
    *,
    font_name: str = "Helvetica",
    font_size: int = 10,
    left: float = 55,
    right: float = 55,
    line_height: float = 15,
) -> float:
    page_width, page_height = A4
    max_width = page_width - left - right

    pdf.setFont(font_name, font_size)

    for line in wrap_text(text, font_name, font_size, max_width):
        if y < 60:
            pdf.showPage()
            y = page_height - 55
            pdf.setFont(font_name, font_size)

        pdf.drawString(left, y, line)
        y -= line_height

    return y


def generate_pdf(record: dict[str, Any], index: int, batch_id: str) -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    filename = (
        f"{index:02d}_"
        f"{record['condition'].lower().replace(' ', '_').replace('-', '_')}.pdf"
    )

    output_path = GENERATED_DIR / filename

    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    _, page_height = A4

    y = page_height - 55

    pdf.setTitle(f"Synthetic Medical Record - {record['condition']}")
    pdf.setAuthor("rag_blockchain_medical_records demo seeder")

    y = draw_wrapped(
        pdf,
        "SYNTHETIC MEDICAL RECORD - FOR TESTING ONLY",
        y,
        font_name="Helvetica-Bold",
        font_size=14,
        line_height=20,
    )

    y -= 8

    fields = [
        f"Record Number: {index:02d}",
        f"Batch ID: {batch_id}",
        f"Age: {record['age']}",
        f"Gender: {record['gender']}",
        f"Encounter Date: {date.today().strftime('%d %B %Y')}",
    ]

    for field in fields:
        y = draw_wrapped(pdf, field, y)

    y -= 8

    sections = [
        ("Chief Complaint", record["complaint"]),
        (
            "Vital Signs",
            "; ".join(f"{key}: {value}" for key, value in record["vitals"].items()),
        ),
        ("Clinical Assessment", record["assessment"]),
        ("Diagnosis", record["condition"]),
        ("Medication", record["medication"]),
        ("Recommendations", record["recommendation"]),
        ("Follow-Up", record["follow_up"]),
        (
            "Additional Notes",
            (
                "This document contains entirely synthetic information created only "
                "for software testing, retrieval evaluation, and demonstration."
            ),
        ),
    ]

    for heading, body in sections:
        y -= 7

        y = draw_wrapped(
            pdf,
            f"{heading}:",
            y,
            font_name="Helvetica-Bold",
            font_size=10,
        )

        y = draw_wrapped(
            pdf,
            body,
            y,
            font_name="Helvetica",
            font_size=10,
        )

    y -= 12

    draw_wrapped(
        pdf,
        "END OF SYNTHETIC RECORD",
        y,
        font_name="Helvetica-Bold",
        font_size=10,
    )

    pdf.save()

    return output_path


# ============================================================
# WALLET AUTH + API
# ============================================================


def load_demo_wallet_private_key() -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    key = os.getenv(DEFAULT_WALLET_KEY_ENV, "").strip()
    if not key:
        key = os.getenv("DEPLOYER_PRIVATE_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "No demo wallet key found. Set DEMO_WALLET_PRIVATE_KEY "
            "or use DEPLOYER_PRIVATE_KEY for local testing."
        )
    return key


def wallet_login(
    client: httpx.Client,
    api_url: str,
    private_key: str,
) -> tuple[str, str]:
    account = Account.from_key(private_key)
    wallet_address = account.address

    challenge_response = client.post(
        f"{api_url}/api/auth/challenge",
        json={"wallet_address": wallet_address},
    )
    challenge_response.raise_for_status()
    challenge = challenge_response.json()

    message = str(challenge["message"])
    signature = account.sign_message(
        encode_defunct(text=message)
    ).signature.hex()

    verify_response = client.post(
        f"{api_url}/api/auth/verify",
        json={
            "wallet_address": wallet_address,
            "signature": signature,
            "challenge_token": challenge["challenge_token"],
        },
    )
    verify_response.raise_for_status()
    payload = verify_response.json()

    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Wallet verification succeeded but no access token was returned.")

    return token, wallet_address


def upload_record(
    client: httpx.Client,
    api_url: str,
    token: str,
    pdf_path: Path,
) -> dict[str, Any]:
    with pdf_path.open("rb") as pdf_file:
        response = client.post(
            f"{api_url}/api/records/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={
                "file": (
                    pdf_path.name,
                    pdf_file,
                    "application/pdf",
                )
            },
        )

    if not response.is_success:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")

    return response.json()


def verify_record(
    client: httpx.Client,
    api_url: str,
    token: str,
    record_hash: str,
) -> bool:
    response = client.get(
        f"{api_url}/api/verify/{record_hash}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if not response.is_success:
        return False
    return bool(response.json().get("verified"))


# ============================================================
# SEEDING
# ============================================================


def seed(api_url: str, count: int) -> None:
    if count < 1:
        raise ValueError("count must be at least 1")
    if count > len(RECORDS):
        raise ValueError(f"Only {len(RECORDS)} synthetic records are currently defined.")

    private_key = load_demo_wallet_private_key()
    batch_id = str(int(time.time()))
    selected_records = RECORDS[:count]

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 72)
    print("WALLET-AUTHENTICATED SYNTHETIC MEDICAL RECORD SEEDER")
    print("=" * 72)
    print(f"API:      {api_url}")
    print(f"Records:  {count}")
    print(f"Batch ID: {batch_id}")
    print("=" * 72)
    print()

    manifest: dict[str, Any] = {
        "batch_id": batch_id,
        "synthetic": True,
        "identity_model": "wallet",
        "records": [],
    }

    success_count = 0
    failure_count = 0

    with httpx.Client(timeout=180.0) as client:
        print("Authenticating wallet...")
        token, wallet_address = wallet_login(client, api_url, private_key)
        manifest["uploader_wallet"] = wallet_address
        print(f"Wallet authenticated: {wallet_address}")
        print()

        for index, record in enumerate(selected_records, start=1):
            condition = record["condition"]
            print(
                f"[{index:02d}/{count:02d}] {condition:<42}",
                end="",
                flush=True,
            )

            entry: dict[str, Any] = {
                "number": index,
                "condition": condition,
                "status": "failed",
            }

            pdf_path: Path | None = None

            try:
                pdf_path = generate_pdf(record=record, index=index, batch_id=batch_id)
                result = upload_record(
                    client=client,
                    api_url=api_url,
                    token=token,
                    pdf_path=pdf_path,
                )

                record_hash = result["record_hash"]
                indexing_warning = result.get("indexing_warning")
                verified = verify_record(client, api_url, token, record_hash)

                entry.update(
                    {
                        "status": "success",
                        "record_hash": record_hash,
                        "ipfs_cid": result["ipfs_cid"],
                        "tx_hash": result["tx_hash"],
                        "uploader_wallet": result["uploader_wallet"],
                        "blockchain_verified": verified,
                        "indexing_warning": indexing_warning,
                    }
                )
                success_count += 1

                print(
                    f"IPFS ✓  {'Besu ✓' if verified else 'Besu ?'}  "
                    f"{'Chroma ✓' if not indexing_warning else 'Chroma !'}"
                )
                if indexing_warning:
                    print(f"         Indexing warning: {indexing_warning}")

            except Exception as exc:
                failure_count += 1
                entry["error"] = str(exc)
                print("FAILED")
                print(f"         {exc}")

            if pdf_path is not None:
                try:
                    pdf_path.unlink(missing_ok=True)
                except Exception:
                    pass

            manifest["records"].append(entry)
            MANIFEST_PATH.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    manifest["summary"] = {
        "requested": count,
        "successful": success_count,
        "failed": failure_count,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print("SEED COMPLETE")
    print("=" * 72)
    print(f"Successful : {success_count}")
    print(f"Failed     : {failure_count}")
    print(f"Manifest   : {MANIFEST_PATH}")
    print("Local PDFs : deleted after upload")
    print("=" * 72)

    try:
        GENERATED_DIR.rmdir()
    except OSError:
        pass

    if failure_count:
        sys.exit(1)


# ============================================================
# CLI
# ============================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate synthetic PDFs and upload them through the wallet-authenticated "
            "FastAPI → IPFS → Besu → Chroma pipeline."
        )
    )
    parser.add_argument(
        "--count",
        type=int,
        default=40,
        help="Number of synthetic records to seed. Default: 40.",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"FastAPI base URL. Default: {DEFAULT_API_URL}",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    seed(api_url=args.api_url.rstrip("/"), count=args.count)
