# 🧪 TestAnix – AI-Powered QA Testing Agent
##Live: testanix.streamlit.app/

**Generate professional software test cases using AI from PDF requirements or simple text prompts.**

TestAnix is an AI-powered QA testing application built with Python, LangChain, Groq LLM, HuggingFace Embeddings, ChromaDB, Pydantic, and Streamlit.

It helps QA Engineers reduce the manual effort involved in writing test cases by automatically analyzing software requirements and generating structured test scenarios.

Users can either upload an SRS (Software Requirements Specification) PDF or directly enter a feature description to generate test cases.

---

## 🚀 Key Features

### 1. Dual Test Case Generation Modes

**PDF-Based Generation**
- Upload software requirement documents in PDF format.
- Extract requirement text using PyPDFLoader.
- Split large documents into smaller text chunks.
- Generate embeddings and store them in ChromaDB.
- Retrieve relevant requirement chunks using similarity search.
- Generate test cases based on the retrieved requirements.

**Prompt-Based Generation**
- Generate test cases without uploading a PDF.
- Enter a feature description directly into the application.
- Generate test cases using the Groq LLM.
- Identify unclear or missing requirements.

### 2. AI-Powered Test Case Generation

Generate test cases covering different testing scenarios:

- Positive Testing
- Negative Testing
- Boundary Value Testing
- Security Testing
- Functional Testing
- Validation Testing
- Error Handling
- Usability Testing

The application targets 10–15 test cases per feature where sufficient requirement information is available.

### 3. Structured Test Case Output

Each generated test case contains:

| Field | Description |
|---|---|
| Test ID | Unique test case identifier |
| Scenario | Test scenario name |
| Objective | Purpose of the test case |
| Test Type | Positive, Negative, Boundary or Security |
| Preconditions | Conditions required before testing |
| Test Steps | Step-by-step execution instructions |
| Test Data | Input data required for execution |
| Expected Result | Expected application behavior |
| Priority | High, Medium or Low |

Pydantic validates the generated output against the defined test case schema.

### 4. Test Cases Dashboard

- View generated test cases in a structured table.
- Search test cases by ID, scenario or objective.
- Filter test cases by testing type.
- Filter test cases by priority.
- View individual test case details.

### 5. Coverage Summary

Visualize generated test case distribution through charts:

- Test cases by testing type.
- Test cases by priority.

These charts help QA Engineers review the distribution of generated scenarios.

### 6. Requirement Ambiguities

Identify unclear or incomplete software requirements.

The application highlights missing business rules and unclear requirements that may need clarification from the Business Analyst, Product Owner or development team.

### 7. Export Test Cases

Export generated test cases into:

- **CSV:** For spreadsheet applications and data processing.
- **Excel (.xlsx):** Includes separate Test Cases and Ambiguities worksheets.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Streamlit | Interactive web application |
| LangChain | LLM integration and prompt management |
| Groq LLM | AI-powered test case generation |
| HuggingFace Embeddings | Text embedding generation |
| ChromaDB | Vector database |
| Pydantic | Structured output validation |
| PyPDFLoader | PDF requirement extraction |
| RecursiveCharacterTextSplitter | Text chunking |
| Pandas | Data manipulation and tabular display |
| OpenPyXL | Excel generation and formatting |
| Python-dotenv | Environment variable management |

---

## 🧠 Project Architecture

TestAnix uses Retrieval-Augmented Generation (RAG) for PDF-based test case generation.

### PDF-Based Workflow

1. User uploads an SRS PDF.
2. PyPDFLoader extracts the document content.
3. RecursiveCharacterTextSplitter divides the content into smaller chunks.
4. HuggingFace Embeddings converts chunks into numerical vectors.
5. ChromaDB stores the text chunks and embeddings.
6. The retriever searches for relevant requirement chunks.
7. LangChain prepares the prompt with retrieved context.
8. Groq LLM generates structured test cases.
9. Pydantic validates the generated output.
10. Streamlit displays the results and provides export options.

### Prompt-Based Workflow

1. User enters a feature description.
2. The application uses the prompt as the requirement source.
3. LangChain sends the prompt and context to Groq.
4. Groq generates structured test cases.
5. Pydantic validates the response.
6. Streamlit displays and exports the generated results.

Both workflows use the same test case generation chain.

---

## 📂 Project Structure

```text
TestAnix/
│
├── Agents/
│   ├── __init__.py
│   └── test_case_agent.py
│
├── RequirementLoader/
│   ├── __init__.py
│   ├── pdf.py
│   └── text_splitter.py
│
├── VectorStore/
│   ├── __init__.py
│   └── chroma_db.py
│
├── schemas/
│   ├── __init__.py
│   └── test_case_schema.py
│
├── chroma_db/
│
├── .env
├── .env.example
├── .gitignore
├── Main.py
└── requirements.txt
```

### Folder Responsibilities

| Folder/File | Responsibility |
|---|---|
| `Agents/` | AI agent and test case generation logic |
| `RequirementLoader/` | PDF extraction and text splitting |
| `VectorStore/` | Embeddings, ChromaDB and retrieval |
| `schemas/` | Pydantic test case data models |
| `chroma_db/` | Persistent vector database storage |
| `Main.py` | Main Streamlit application |
| `.env` | API keys and model configuration |
| `requirements.txt` | Project dependencies |

---

## ⚙️ Installation and Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/anish-prajapati03/TestAnix.git
```

Navigate to the project directory:

```bash
cd TestAnix
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Activate it on macOS/Linux:

```bash
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the root directory.

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

Get your API key from:

https://console.groq.com/keys

**Important:** Never commit your actual API key or `.env` file to GitHub.

### Step 5: Run the Application

```bash
streamlit run Main.py
```

The application will open in your browser.

---

## 🖥️ How to Use TestAnix

### Mode 1: Generate Test Cases Using a PDF

1. Open TestAnix.
2. Upload an SRS PDF document.
3. Select the required testing types.
4. Enter your test generation prompt.
5. Click **Generate Test Cases**.
6. Review the generated test cases.
7. Explore the Coverage Summary and Requirement Ambiguities.
8. Download the results in CSV or Excel format.

### Mode 2: Generate Test Cases Without a PDF

1. Open TestAnix.
2. Skip the PDF upload.
3. Select the required testing types.
4. Enter a feature description in the prompt field.
5. Click **Generate Test Cases**.
6. Review and export the generated test cases.

### Example Prompt

```text
Generate 10-15 test cases for login functionality.

Include:
- Positive scenarios
- Negative scenarios
- Boundary scenarios
- Empty field validation
- Invalid email validation
- Password validation

Provide clear test steps, test data,
expected results and priorities.
```

---

## 🔍 Example Test Case

| Field | Example |
|---|---|
| Test ID | TC001 |
| Scenario | Login with valid credentials |
| Objective | Verify successful user authentication |
| Test Type | Positive |
| Preconditions | Registered user account exists |
| Test Steps | Enter valid email, enter password and click Login |
| Test Data | Valid registered email and password |
| Expected Result | User is successfully logged in and redirected to the dashboard |
| Priority | High |

---

## 🔐 Security and Configuration

- Store API credentials in environment variables.
- Keep `.env` excluded from Git.
- Use `.env.example` to document required configuration.
- Do not upload confidential requirement documents or sensitive test data without authorization.

---

## ⚠️ Current Limitations

- Generated test cases require review by a QA Engineer.
- Results depend on the quality and completeness of the supplied requirements.
- PDF retrieval may miss requirements if they are not present in the retrieved chunks.
- Large documents may require feature-wise processing to avoid output truncation.
- The application generates test cases but does not currently execute them against a live application.

---

## 🔮 Future Enhancements

Potential improvements planned for future versions:

- [ ] Feature-wise requirement extraction and batch generation.
- [ ] Automated bug report generation.
- [ ] Playwright automation script generation.
- [ ] Jira integration for test case management.
- [ ] Requirement-to-test-case traceability.
- [ ] Test case duplicate detection.
- [ ] Test execution and reporting.
- [ ] PDF and additional document format support.
- [ ] Advanced test coverage analytics.

---

## 🎯 Project Objective

The objective of TestAnix is to simplify the test case design process by combining Artificial Intelligence, Retrieval-Augmented Generation, and software testing principles.

It demonstrates how modern LLM technologies can support QA Engineers in analyzing requirements, generating test scenarios, identifying requirement ambiguities, and preparing structured testing documentation.

---

## 👨‍💻 Author

**Anish Prajapati**

B.Tech – Computer Science and Engineering

**Areas of Interest:**
- Software Quality Assurance
- Manual Testing
- Automation Testing
- Python
- Generative AI
- LangChain and RAG

---

⭐ If you find TestAnix useful, consider giving the repository a star!

**Built with ❤️ using Python, LangChain, Groq and Streamlit.**
