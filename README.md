# AI-Driven Job Role Recommendation System

## Overview
An AI-powered web application that analyzes a candidate's resume (PDF) and predicts the most suitable job role using Natural Language Processing (NLP) and Machine Learning.

The application extracts resume text, preprocesses it, converts it into TF-IDF features, and uses a trained **Random Forest Classifier** to recommend a job role. It also provides user authentication, prediction history, and PDF report generation.

---

## Features

- User Signup & Login (secure password hashing)
- Upload Resume (PDF)
- Automatic Resume Text Extraction
- AI-Based Job Role Prediction
- TF-IDF based NLP preprocessing
- Random Forest Machine Learning model
- Prediction confidence score
- Resume upload history
- Prediction history dashboard
- PDF report generation
- SQLite database for user and prediction records
- Vercel deployment support

---

## Tech Stack

| Category | Technology |
|----------|------------|
| Backend | Flask |
| Machine Learning | Scikit-learn |
| NLP | TF-IDF Vectorizer |
| Model | Random Forest Classifier |
| PDF Processing | PyPDF |
| Database | SQLite |
| Model Storage | Joblib |
| Frontend | HTML, CSS, Jinja2 Templates |

---

## Project Structure

```text
JobRoleWebApp/
│── app.py                 # Main Flask application
│── train_model.py         # Model training script
│── generate_pdf.py        # PDF report generation
│── model.pkl              # Trained ML model
│── vectorizer.pkl         # TF-IDF vectorizer
│── database.db            # SQLite database
│── templates/             # HTML templates
│── static/                # CSS & static assets
│── uploads/               # Uploaded resumes
│── requirements.txt
```

## Machine Learning Pipeline

1. Upload resume in PDF format.
2. Extract text using PyPDF.
3. Clean and preprocess text.
4. Transform resume using TF-IDF Vectorizer.
5. Predict job role using Random Forest.
6. Store prediction and upload history in SQLite.
7. Display result and allow report generation.

---

## Dataset

The model is trained on a resume dataset containing:
- Resume text
- Corresponding job category

Training process:
- Text cleaning
- TF-IDF Vectorization (up to 10,000 features, 1-2 grams)
- Train/Test split
- Random Forest (300 estimators)

---

## Database

The application automatically creates:
- users
- resumes
- predictions

---

## Future Enhancements

- Resume skill gap analysis
- Personalized learning recommendations
- Multiple ML model comparison
- Resume scoring
- LLM-based career guidance
- Cloud database integration
- Email reports

---
