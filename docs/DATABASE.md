# Tables

Doctor
- id
- name
- email
- password

Patient
- id
- name
- age
- gender

MedicalRecord
- id
- patient_id
- doctor_id
- diagnosis
- hash
- file_path

AuditLog
- id
- doctor_id
- action
- timestamp