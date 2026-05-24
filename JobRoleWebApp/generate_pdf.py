from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Dataset Viva Questions & Answers', 0, 1, 'C')
        self.ln(5)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        # Using multi_cell for text wrapping
        self.multi_cell(0, 8, body)
        self.ln()

pdf = PDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)

content = [
    {
        'title': '1. Basic Dataset Understanding',
        'body': 'Q: Can you describe the dataset you used for your project?\n'
                'A: We used a resume dataset consisting of 2,484 records. Each record corresponds to a resume. The dataset includes 4 columns: ID (unique identifier), Resume_str (the plain text of the resume), Resume_html (the HTML format of the resume), and Category (the target label indicating the job role).\n\n'
                'Q: Where did this dataset come from?\n'
                'A: It is a well-known open-source resume dataset, typically sourced from Kaggle.'
    },
    {
        'title': '2. Features and Target Variable',
        'body': 'Q: Which specific features (columns) did you use to train your model?\n'
                'A: Out of the 4 columns, we only used two: Resume_str as our input feature (X) and Category as our target/output variable (y).\n\n'
                'Q: How many job roles (classes) is your model predicting?\n'
                'A: There are 24 unique job roles/categories, such as Information-Technology, Business-Development, HR, Finance, Engineering, etc.'
    },
    {
        'title': '3. Data Distribution & Imbalances',
        'body': 'Q: Is your dataset balanced or imbalanced?\n'
                'A: It is slightly imbalanced but mostly consistent. Most of the 24 categories have between 100 to 120 resumes. However, there are a few minority classes with significantly less data, such as Agriculture (63), Automobile (36), and BPO (22).\n\n'
                'Q: How did you handle that imbalance?\n'
                'A: In our Random Forest model, we passed the parameter class_weight="balanced". This automatically adjusts the weights inversely proportional to class frequencies.'
    },
    {
        'title': '4. Data Preprocessing & Cleaning',
        'body': 'Q: Did your dataset have any missing values? If so, how did you handle them?\n'
                'A: No, during our EDA we found that there were 0 missing values across all columns, so we did not require imputation.\n\n'
                'Q: Resumes have lots of junk characters. How did you clean the text data?\n'
                'A: I implemented a clean_text function in my script. It converts all text to lowercase and uses Regular Expressions to remove all non-alphabetical characters so the model only learns from pure alphabetic words.\n\n'
                'Q: How do you convert text data into a format that a Machine Learning model can understand?\n'
                'A: We used NLP techniques. Specifically, we used TF-IDF (Term Frequency-Inverse Document Frequency) Vectorizer. We set it to ignore common English stop words, look at combinations of 1 and 2 words, and limited it to the top 10,000 most frequent feature words.'
    },
    {
        'title': '5. Training and Testing',
        'body': 'Q: How did you split this dataset for evaluating your model?\n'
                'A: We used train_test_split from sklearn, splitting the data into 80% for training and 20% for testing. We also used random_state=42 to make sure the split is reproducible.\n\n'
                'Pro-Tip for the Viva:\n'
                'If they ask you "What is the weakest point of your dataset?", a great answer is to mention that since categories like BPO and Automobile have significantly fewer rows compared to IT and Finance, the model naturally might struggle slightly more to have high confidence when predicting those specific niche roles.'
    }
]

for item in content:
    pdf.chapter_title(item['title'])
    pdf.chapter_body(item['body'].encode('latin-1', 'replace').decode('latin-1'))

pdf.output('Dataset_Viva_Questions.pdf')
print("Successfully generated Dataset_Viva_Questions.pdf")
