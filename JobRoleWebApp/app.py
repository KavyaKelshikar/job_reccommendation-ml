from pydoc import text

from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import re
from pypdf import PdfReader
import os
import joblib
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import send_file
import io

# ---------------- INIT ----------------

app = Flask(__name__)
app.secret_key = "test123"


model = joblib.load("model.pkl")
vectorizer = joblib.load("vectorizer.pkl")


# ---------------- PDF TEXT EXTRACTION ----------------

def extract_text_from_pdf(filepath):
    reader = PdfReader(filepath)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text


# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS resumes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        filename TEXT,
        uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS predictions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        filename TEXT,
        role TEXT,
        confidence REAL,
        skills TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()


# ---------------- HOME ----------------

@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ---------------- SIGNUP ----------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":

        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$"

        if not re.match(pattern, password):
            flash("Weak password", "error")
            return render_template("signup.html")

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        try:
            c.execute(
                "INSERT INTO users(username,email,password) VALUES(?,?,?)",
                (username, email, hashed_password)
            )
            conn.commit()
            flash("Account created successfully!", "success")
            return redirect(url_for("login"))

        except:
            flash("Email already exists", "error")

        finally:
            conn.close()

    return render_template("signup.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE email=?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session["user"] = user[1]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "error")

    return render_template("login.html")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM predictions WHERE username=?", (session["user"],))
    predictions = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM resumes WHERE username=?", (session["user"],))
    resumes = c.fetchone()[0]

    c.execute(
        "SELECT filename, role, confidence, skills FROM predictions WHERE username=? ORDER BY id DESC LIMIT 2",
        (session["user"],)
    )
    recent_predictions = c.fetchall()
    
    c.execute("SELECT confidence FROM predictions WHERE username=?", (session["user"],))
    all_confs = c.fetchall()
    
    ai_readiness = "Pending"
    if all_confs:
        avg_conf = sum([row[0] for row in all_confs if isinstance(row[0], (int, float))]) / len(all_confs)
        if avg_conf >= 92:
            ai_readiness = "High"
        elif avg_conf >= 75:
            ai_readiness = "Moderate"
        else:
            ai_readiness = "Low"

    c.execute("SELECT confidence, role FROM predictions WHERE username=? ORDER BY id ASC", (session["user"],))
    all_data = c.fetchall()
    
    chart_labels = [f"Res {i+1}" for i in range(len(all_data))]
    chart_confidences = [row[0] for row in all_data]
    
    # Role distribution for pie chart
    from collections import Counter
    role_counts = Counter([row[1] for row in all_data])
    pie_labels = list(role_counts.keys())
    pie_values = list(role_counts.values())

    conn.close()

    return render_template("dashboard.html",
                           username=session["user"],
                           predictions=predictions,
                           resumes=resumes,
                           recent_predictions=recent_predictions,
                           ai_readiness=ai_readiness,
                           chart_labels=chart_labels,
                           chart_confidences=chart_confidences,
                           pie_labels=pie_labels,
                           pie_values=pie_values)


# ---------------- UPLOAD PAGE ----------------

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == 'POST':
        file = request.files.get('resume')

        if not file or file.filename == "":
            flash("No file selected", "error")
            return redirect(url_for("upload"))

        if not allowed_file(file.filename):
            flash("Only PDF files allowed", "error")
            return redirect(url_for("upload"))

        # Save file safely
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Save in database
        import datetime
        now = datetime.datetime.now().strftime("%b %d, %Y %I:%M %p")
        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()
            c.execute("INSERT INTO resumes(username, filename, uploaded_at) VALUES(?, ?, ?)",
                      (session["user"], filename, now))
            conn.commit()

        flash("✅ Resume uploaded successfully!", "success")
        return redirect(url_for("upload"))

    # GET → show uploaded resumes
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("SELECT filename, uploaded_at FROM resumes WHERE username=?", (session["user"],))
        resumes = [ {"filename": row[0], "uploaded_at": row[1]} for row in c.fetchall()]

    return render_template("upload.html", resumes=resumes)


# ---------------- DELETE RESUME ----------------
@app.route("/delete_resume", methods=["POST"])
def delete_resume():
    if "user" not in session:
        return redirect(url_for("login"))

    filename = request.form.get("filename")
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if os.path.exists(filepath):
        os.remove(filepath)

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM resumes WHERE username=? AND filename=?", (session["user"], filename))
        c.execute("DELETE FROM predictions WHERE username=? AND filename=?", (session["user"], filename))
        conn.commit()

    flash(f"Resume '{filename}' deleted successfully!", "success")
    return redirect(url_for("upload"))


# ---------------- PREDICT PAGE ----------------

@app.route("/predict_page", methods=['GET', 'POST'])
def predict_page():
    if "user" not in session:
        return redirect(url_for("login"))

    # Fetch resumes
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("SELECT filename, uploaded_at FROM resumes WHERE TRIM(LOWER(username)) = TRIM(LOWER(?))", (session["user"],))
        rows = c.fetchall()
        resumes = [{"filename": row[0], "uploaded_at": row[1]} for row in rows]

    if request.method == 'POST':
        selected_resume = request.form.get('resume')

        if not selected_resume:
            flash("Please select a resume", "error")
            return redirect(url_for("predict_page"))

        filepath = os.path.join(UPLOAD_FOLDER, selected_resume)

        if not os.path.exists(filepath):
            flash("Resume not found!", "error")
            return redirect(url_for("predict_page"))

        resume_text = extract_text_from_pdf(filepath)
        text_lower = resume_text.lower()

        # ML prediction
        text_vector = vectorizer.transform([resume_text])
        probabilities = model.predict_proba(text_vector)[0]
        classes = model.classes_

        top3_indices = probabilities.argsort()[-3:][::-1]
        top_roles = [(classes[i], round(probabilities[i]*100, 2)) for i in top3_indices]

        predicted_role, confidence = top_roles[0]

        # ---------------- KEYWORDS ----------------
        ds_keywords = ["machine learning","python","pandas","numpy","sql"]
        software_keywords = ["java", "python", "c++", "oop", "dsa"]
        web_keywords = ["html","css","javascript","react"]
        android_keywords = ["android","kotlin","java"]
        finance_keywords = ["finance","accounting","excel","tax"]
        banking_keywords = ["bank","loan","credit","transactions"]
        hr_keywords = ["recruitment","hiring","payroll"]
        sales_keywords = ["sales","marketing","client"]
        bpo_keywords = ["bpo","customer support","call center"]

        def count_matches(keywords):
            return sum(1 for k in keywords if k in text_lower)

        scores = {
            "DATA-SCIENCE": count_matches(ds_keywords),
            "SOFTWARE-DEVELOPER": count_matches(software_keywords),
            "WEB-DEVELOPER": count_matches(web_keywords),
            "ANDROID-DEVELOPER": count_matches(android_keywords),
            "FINANCE": count_matches(finance_keywords),
            "BANKING": count_matches(banking_keywords),
            "HR": count_matches(hr_keywords),
            "SALES": count_matches(sales_keywords),
            "BPO": count_matches(bpo_keywords)
        }

        # ---------------- ROLE MAP ----------------
        role_map = {
            "DATA-SCIENCE": ["Data Analyst","ML Engineer","Data Scientist"],
            "SOFTWARE-DEVELOPER": ["Software Developer"],
            "WEB-DEVELOPER": ["Frontend Developer","Backend Developer","Full Stack Developer"],
            "ANDROID-DEVELOPER": ["Android Developer"],
            "FINANCE": ["Financial Analyst","Accountant"],
            "BANKING": ["Bank Clerk","Loan Officer","Relationship Manager"],
            "HR": ["HR Executive","Recruiter"],
            "SALES": ["Sales Executive","Business Development Executive"],
            "BPO": ["Customer Support Executive"]
        }
        def normalize_role(role):
            role = role.lower()

            if role in ["frontend developer", "backend developer", "full stack developer"]:
                return "Web Developer"

            elif role == "data analyst":
                return "Data Analyst"
            
            elif role == "data scientist":
                return "Data Scientist"

            elif role == "ml engineer":
                return "Machine Learning Engineer"
            
            elif role in ["software developer", "java developer", "python developer"]:
                return "Software Developer"
            
            elif role in ["hr executive", "recruiter"]:
                return "HR"
            
            return role.title()

        best_role = max(scores, key=scores.get)

        if scores[best_role] >= 2:
             predicted_role = best_role
             confidence = max(confidence, 85)
             actual_roles = role_map.get(predicted_role, [])
        else:
             actual_roles = role_map.get(predicted_role, [])

        # Step 1: Normalize roles
        normalized_roles = []

        for r in actual_roles:
            nr = normalize_role(r)
            if nr not in normalized_roles:
                normalized_roles.append(nr)

        # Step 2: Ensure always 3 roles
        fallback_map = {
            "Web Developer": ["UI/UX Designer", "Software Developer"],
            "Machine Learning Engineer": ["Data Analyst", "AI Engineer"],
            "Software Developer": ["Backend Developer", "Full Stack Developer"],
            "HR": ["Talent Acquisition", "HR Manager"]
        }

        # Add fallback roles if less than 3
        main_role = normalized_roles[0] if normalized_roles else normalize_role(predicted_role)

        if len(normalized_roles) < 3:
            extras = fallback_map.get(main_role, [])
            for e in extras:
                if e not in normalized_roles:
                    normalized_roles.append(e)
                if len(normalized_roles) == 3:
                    break

        # Final roles
        actual_roles = normalized_roles[:3]

        # Final recommended role
        final_role = actual_roles[0]

        # ---------------- SKILLS ----------------
        skills_list = ["python","java","html","css","javascript","sql","excel","kotlin"]
        skills = [s for s in skills_list if s in text_lower]

        
        
        # ---------------- SCORE ----------------
        score = min(100, scores.get(predicted_role, 0)*15 + len(skills)*5)

        # ---------------- SKILL GAP ----------------
        required_skills_map = {
            "DATA-SCIENCE": ["python","sql","machine learning","statistics"],
            "WEB-DEVELOPER": ["html","css","javascript","react"],
            "ANDROID-DEVELOPER": ["kotlin","java","xml"],
            "FINANCE": ["excel","accounting","financial modeling","tax"],
            "BANKING": ["finance","loan processing","customer service"],
            "HR": ["recruitment","communication","payroll"],
            "SALES": ["communication","negotiation","client handling"],
            "BPO": ["communication","customer support","voice process"],
            "DIGITAL-MEDIA": ["seo","social media","content marketing"],
            "ENGINEERING": ["autocad","design","manufacturing"],
            "HEALTHCARE": ["patient care","medical knowledge","clinical"],
            "EDUCATION": ["teaching","curriculum","lesson planning"],
            "LEGAL": ["law","legal research","compliance"],
            "CONSTRUCTION": ["site management","construction","planning"],
            "RESEARCH": ["research","analysis","data collection"]
            }

        required = required_skills_map.get(predicted_role, [])
        missing_skills = [s for s in required if s not in skills]

        # ---------------- DEMAND ----------------
        demand_map = {
            "DATA-SCIENCE": "🔥 High",
            "WEB-DEVELOPER": "🔥 High",
            "ANDROID-DEVELOPER": "📈 Growing",
            "FINANCE": "📊 Medium",
            "BANKING": "📊 Stable",
            "HR": "📊 Moderate",
            "SALES": "🔥 High",
            "BPO": "📊 Moderate",
            "DIGITAL-MEDIA": "📈 Growing",
            "ENGINEERING": "📊 Stable",
            "HEALTHCARE": "🔥 High",
            "EDUCATION": "📊 Stable",
            "LEGAL": "📊 Moderate",
            "CONSTRUCTION": "📈 Growing",
            "RESEARCH": "📊 Niche"
            }

        demand = demand_map.get(predicted_role, "Normal")

        # ---------------- SALARY ----------------
        salary_map = {
            "DATA-SCIENCE": "₹6L – ₹20L",
            "WEB-DEVELOPER": "₹4L – ₹15L",
            "ANDROID-DEVELOPER": "₹4L – ₹12L",
            "FINANCE": "₹3L – ₹10L",
            "BANKING": "₹3L – ₹8L",
            "HR": "₹3L – ₹7L",
            "SALES": "₹2L – ₹8L",
            "BPO": "₹1.5L – ₹4L",
            "DIGITAL-MEDIA": "₹3L – ₹9L",
            "ENGINEERING": "₹3L – ₹12L",
            "HEALTHCARE": "₹2L – ₹10L",
            "EDUCATION": "₹2L – ₹6L",
            "LEGAL": "₹4L – ₹15L",
            "CONSTRUCTION": "₹3L – ₹10L",
            "RESEARCH": "₹4L – ₹12L"
            }
        
        

        salary = salary_map.get(predicted_role, "Varies")

        # ---------------- DESCRIPTION ----------------
        description_map = {
                "Data Analyst": "Data Analysts analyze complex data to extract meaningful insights. They build models and help organizations make data-driven decisions. Strong skills in Python, statistics, and data handling are essential.",
                "Data Scientist": "Data Scientists analyze complex data to extract meaningful insights. They build machine learning models and help organizations make data-driven decisions. Strong skills in Python, statistics, and data handling are essential.",
                "Machine Learning Engineer": "Machine Learning Engineers design, build and deploy AI models. They help organizations make data-driven decisions. Strong skills in Python, statistics, and algorithm design are essential.",
                "Software Developer": "Software Developers design and build software applications. They focus on building logic, complex structures and algorithms. Strong analytical skills and knowledge of computing are crucial.",
                "Web Developer": "Web Developers design and build websites and web applications. They work on both frontend and backend technologies to create user-friendly experiences. Knowledge of HTML, CSS, JavaScript, and frameworks is important.",
                "Android Developer": "Android Developers create mobile applications for Android devices. They use Kotlin or Java to build efficient and scalable apps. Understanding UI design and app performance optimization is key.",
                "Financial Analyst": "Finance professionals analyze financial data, manage budgets, and support business decisions. They work with reports, investments, and forecasting. Strong analytical skills and Excel knowledge are required.",
                "Accountant": "Finance professionals analyze financial data, manage budgets, and support business decisions. They work with reports, investments, and forecasting. Strong analytical skills and Excel knowledge are required.",
                "Bank Clerk": "Banking professionals handle financial transactions, customer accounts, and loan processing. They ensure smooth banking operations and provide financial services support. Communication and financial knowledge are important.",
                "HR": "HR professionals manage recruitment, employee relations, and organizational development. They ensure smooth hiring processes and maintain a positive work environment. Communication skills are essential.",
                "Sales Executive": "Sales professionals are responsible for generating revenue and managing client relationships. They identify business opportunities and close deals. Strong communication and negotiation skills are crucial.",
                "Customer Support Executive": "BPO roles involve handling customer queries, providing support, and maintaining service quality. Employees interact with customers via calls or chat. Communication and problem-solving skills are key.",
                "UI/UX Designer": "UI/UX Designers study user behavior to design interfaces that are seamless to use. They require deep empathy and design skills to implement frontends.",
                "AI Engineer": "AI Engineers specialize in designing machine learning architectures and generative networks. Strong mathematical background is required.",
                "Backend Developer": "Backend Developers focus on server-side logic, database interaction, and system architecture. They ensure apps are fast and secure.",
                "Full Stack Developer": "Full Stack Developers create end-to-end web architectures, working on both frontend UI and backend server operations seamlessly.",
                "Talent Acquisition": "Talent Acquisition professionals specialize in sourcing, interviewing, and retaining the best talent in the market.",
                "HR Manager": "HR Managers streamline organizational workflow, structure salaries, and manage overall human operations in the company."
                }

        description = description_map.get(final_role, "Role based on your skills. Our intelligence engine detected key overlap between your profile elements and the standard requirements for this field.")

        # ---------------- AI ADVICE ----------------
        if missing_skills:
            advice = f"""To improve your chances in this field, focus on learning {', '.join(missing_skills[:3])}.
            Building hands-on projects and gaining practical experience will strengthen your profile significantly.
            You should also consider internships or certifications to increase your job readiness."""
        else:
            advice = """Your profile is well aligned with this role.
            Focus on gaining real-world experience through projects or internships.
            Start applying confidently to relevant job opportunities."""
            
        # ---------------- SAVE TO HISTORY ----------------
        with sqlite3.connect("database.db") as conn:
            c = conn.cursor()
            c.execute("""
                      INSERT INTO predictions(username, filename, role, confidence, skills)
                      VALUES(?,?,?,?,?)
                      """, (
                          session["user"],
                          selected_resume,
                          predicted_role,
                          confidence,
                          ", ".join(skills)
                          ))
            conn.commit()
            
        session["result_data"] = {
            "filename": selected_resume,
            "role": final_role,
            "actual_roles": actual_roles,
            "confidence": confidence,
            "skills": skills,
            "score": score,
            "missing_skills": missing_skills,
            "demand": demand,
            "salary": salary,
            "description": description,
            "advice": advice
            }
        
        # ---------------- RETURN ----------------
        return render_template("result.html",
                               filename=selected_resume,
                               role=final_role,
                               actual_roles=actual_roles,
                               confidence=confidence,
                               skills=skills,
                               score=score,
                               missing_skills=missing_skills,
                               demand=demand,
                               salary=salary,
                               description=description,
                               advice=advice)

    return render_template("predict_page.html", resumes=resumes)

# ---------------- DOWNLOAD RESULT ----------------
from flask import request, send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

@app.route("/download_result")
def download_result():
    if "user" not in session or "result_data" not in session:
        return redirect(url_for("predict_page"))

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    import io
    from flask import send_file

    data = session["result_data"]

    filename = data.get("filename", "")
    role = data.get("role", "")
    confidence = data.get("confidence", "")
    score = data.get("score", "")
    demand = data.get("demand", "")
    salary = data.get("salary", "")
    description = data.get("description", "")
    advice = data.get("advice", "")
    skills = data.get("skills", [])
    missing_skills = data.get("missing_skills", [])
    actual_roles = data.get("actual_roles", [])

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    width, height = letter
    y = 750

    # ================= HEADER =================
    pdf.setFillColor(colors.HexColor("#0A66C2"))
    pdf.rect(0, 720, width, 80, fill=1)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 760, "AI Job Role Recommendation Report")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 740, f"Generated for: {filename}")

    y = 690
    pdf.setFillColor(colors.black)

    # ================= HELPERS =================
    def section_title(text):
        nonlocal y
        if y < 80:
            pdf.showPage()
            y = 750

        pdf.setFont("Helvetica-Bold", 13)
        pdf.setFillColor(colors.HexColor("#0A66C2"))
        pdf.drawString(50, y, text)
        y -= 20
        pdf.setFillColor(colors.black)

    def write_line(text, spacing=15):
        nonlocal y
        if y < 60:
            pdf.showPage()
            y = 750

        pdf.setFont("Helvetica", 11)
        pdf.drawString(60, y, str(text))
        y -= spacing

    def write_multiline(text, max_chars=90):
        nonlocal y
        if not text:
            return
        text = str(text)
        lines = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]
        for line in lines:
            write_line(line, 14)

    # ================= SUMMARY CARD =================
    box_height = 70

    pdf.setFillColor(colors.HexColor("#EAF3FB"))
    pdf.rect(40, y - box_height, width - 80, box_height, fill=1, stroke=0)

    y_inside = y - 20

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(60, y_inside, f"Recommended Role: {role}")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(60, y_inside - 18, f"Confidence: {confidence}%")
    pdf.drawString(60, y_inside - 36, f"Resume Score: {score}/100")

    y = y - box_height - 25

    # ================= SUGGESTED ROLES =================
    section_title("Suggested Roles")

    line_height = 16
    padding = 12
    num_items = len(actual_roles)

    box_height = (num_items * line_height) + (padding * 2)
    box_top = y

    pdf.setFillColor(colors.HexColor("#F3F6F8"))
    pdf.rect(40, box_top - box_height, width - 80, box_height, fill=1, stroke=0)

    pdf.setFillColor(colors.black)
    y = box_top - padding

    for r in actual_roles:
        write_line(f"• {r}", spacing=line_height)

    y = box_top - box_height - 20

    # ================= SKILLS (TAGS) =================
    section_title("Skills Detected")

    x = 50
    tag_height = 20

    for skill in skills:
        skill = str(skill)
        text_width = pdf.stringWidth(skill, "Helvetica", 10)
        tag_width = text_width + 20

        if x + tag_width > width - 50:
            x = 50
            y -= 30

        pdf.setFillColor(colors.HexColor("#D1E7DD"))
        pdf.roundRect(x, y, tag_width, tag_height, 6, fill=1, stroke=0)

        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x + 10, y + 5, skill)

        x += tag_width + 10

    y -= 40

    # ================= SKILL GAP =================
    section_title("Skill Gap")
    x = 50
    tag_height = 16   # smaller height
    gap = 8           # space between tags

    pdf.setFont("Helvetica", 9)  # smaller font

    for skill in missing_skills:
        skill = str(skill)

        text_width = pdf.stringWidth(skill, "Helvetica", 9)
        tag_width = text_width + 14  # less padding

        # wrap to next line
        if x + tag_width > width - 50:
            x = 50
            y -= 22

        # softer red (more LinkedIn-like)
        pdf.setFillColor(colors.HexColor("#FDE2E4"))
        pdf.roundRect(x, y, tag_width, tag_height, 5, fill=1, stroke=0)

        # text
        pdf.setFillColor(colors.black)
        pdf.drawString(x + 7, y + 4, skill)

        x += tag_width + gap
        
    y -= 30

    # ================= MARKET =================
    section_title("Market Insights")
    write_line(f"📈 Job Demand: {demand}")
    write_line(f"💰 Salary Range: {salary}")

    y -= 10

    # ================= DESCRIPTION =================
    section_title("Role Description")
    write_multiline(description)

    y -= 10

    # ================= ADVICE =================
    section_title("AI Career Advice")
    write_multiline(advice)

    # ================= FOOTER =================
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.setFillColor(colors.grey)
    pdf.drawString(50, 30, "Generated by AI Job Role Recommendation System")

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{filename}_final_report.pdf",
        mimetype="application/pdf"
    )
    
# ---------------- HISTORY ----------------

@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    SELECT filename, role, confidence, skills
    FROM predictions
    WHERE username=?
    ORDER BY id DESC
    """, (session["user"],))

    data = c.fetchall()
    conn.close()

    avg_confidence = 0
    top_domain = "N/A"

    if data:
        # calculate avg confidence
        confs = [row[2] for row in data if isinstance(row[2], (int, float))]
        if confs:
            avg_confidence = round(sum(confs) / len(confs), 1)
            
        # calculate top domain
        from collections import Counter
        roles = [row[1] for row in data if row[1]]
        if roles:
            top_domain = Counter(roles).most_common(1)[0][0]

    return render_template("history.html", data=data, avg_confidence=avg_confidence, top_domain=top_domain)


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- RUN ----------------

if __name__ == "__main__":
    print(app.url_map)
    app.run(debug=True)