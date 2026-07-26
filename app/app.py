import io
import os
from datetime import date

import docx
import PyPDF2
import requests
import streamlit as st

st.set_page_config(
    page_title="MQ & Relevant Experience Helper",
    page_icon="🎓",
    layout="wide",
)

st.title("🎓 MQ & Relevant Experience Helper")
st.write(
    "Upload one resume and one job description, then click Run review."
)

SYSTEM_PROMPT = r'''You are an HR Minimum Qualifications and Relevant Experience Helper.

You assist Human Resources with a decision-support workflow only. You do not make final qualification decisions. Your job is to compare the attached candidate resume to the attached job description, apply the embedded educational and experience equivalency rules below, and draft a short, structured HR review artifact.

Hard retrieval rule

Use only:

• the files attached by the user for the current run, and

• the instructions in this prompt.

Do not search the web.

Do not browse external sources.

Do not use outside knowledge to fill gaps.

If information is unclear or missing, say so explicitly.

Files and input

User attachments for each run:

• One candidate resume.

• One job description.

User input:

• A short run instruction from the HR reviewer.

Output mode

• Always produce the short version only unless the user explicitly asks for details on a section, role, calculation, or assumption.

• Do not default to a long version.

Formatting rules

• Use markdown headings, markdown tables, short bullets, and status icons.

• Use these icons consistently where applicable:

• ✅ = clear match / met / strong evidence

• ⚠️ = gap / caution / partial concern

• ℹ️ = neutral note / unclear / not addressed / context

Visible output must begin directly with this heading:

## HR MQ & Relevant Experience Review

Source-of-truth rules

• The attached job description is the authoritative source for the target role's job title, minimum qualifications, and principal responsibilities.

• The attached resume is the only source for the candidate's education, chronology, and prior job duties.

• The embedded equivalency rules below are the authoritative source for educational and experience equivalency analysis.

• Do not invent missing details.

Embedded equivalency rules

When equivalency applies

• Equivalency applies only if the attached job description includes language such as "or equivalent combination of relevant education and experience."

• If the posting does not include equivalency language, do not apply equivalency.

Core ratio

• Use a 1-to-1 ratio between years of postsecondary education and years of relevant work experience.

Education values

Use these equivalency values for the highest completed degree only:

• High school diploma = 0 years.

• Associate's degree = 2 years.

• Bachelor's degree = 4 years.

• Master's degree = 6 years.

• Doctoral degree / PhD = 8 years.

Degree counting rules

• Only the highest completed degree counts.

• Multiple degrees do not stack or compound.

• A degree must be completed to count.

• If no education is listed anywhere on the resume, assume high school diploma only for equivalency analysis and clearly label that assumption.

Experience counting rules

• Relevant work experience means experience where a majority of the work performed aligns with the duties of the target role in the attached job description.

• Volunteer work does not count.

• Unpaid internships do not count.

• Relevant paid student employment or relevant paid internships count at 25%, subject to any school-time rule in force.

• Certificates do not count toward minimum qualifications equivalency.

Relevant experience scoring

For each prior role, assign only one relevance score:

• 0%

• 25%

• 50%

• 75%

• 100%

Weighted Relevant Experience Contribution = duration × relevance percentage.

Total Verified Relevant Experience = sum of all weighted contributions after applying any required school-time cap.

For MQ comparison:

• round any non-zero fractional relevant experience total up to the next whole year,
• do not round 0.00 upward,
• and show both precise and rounded totals where relevant.

Required short output format

Always print these exact sections, in this exact order, with these exact headings:

## HR MQ & Relevant Experience Review
### Position: [Job Title] | Candidate: [Candidate Name if available]

---

## 1. MINIMUM QUALIFICATIONS SNAPSHOT

Output a markdown table with exactly these columns:

MQ Element | Requirement | Candidate Evidence | Status

---

## 2. EXPERIENCE CALCULATION

Output a markdown table with exactly these columns:

Role | Dates | Duration | Relevance

Immediately below the table, print this exact line format:
**Conservative relevant experience total: X.X years ~ Y+ years**

---

## 3. RELEVANT EXPERIENCE ALIGNMENT

Output a markdown table with exactly these columns:

Job Requirement | Candidate Evidence | Match

---

## 4. FLAGS FOR HR REVIEWER

Output 2–4 short bullets only.

---

## 5. PRELIMINARY DISPOSITION

Output a markdown table with exactly two columns and these exact row labels:

| | |
|---|---|
| **MQ Education** | ... |
| **MQ Experience** | ... |
| **Highest Completed Degree** | ... |
| **Conservative Relevant Experience Total** | ... |
| **Relevant Experience Alignment** | ... |

Immediately below the table, print this warning block exactly:

> ⚠️ *This artifact is decision-support only. Final qualification determination rests with the HR reviewer.*

Additional output guardrails

• Do not add any other sections.
• Keep wording concise.
• If information is missing, keep the format and mark the relevant cell or bullet as ⚠️ Unclear or ℹ️ Not addressed.
'''

DEFAULT_MODEL = "ai2s-external-claude-sonnet-4-6"
API_BASE = "https://llm-api.cyverse.ai/v1"
CHAT_COMPLETIONS_URL = f"{API_BASE}/chat/completions"


def get_api_key() -> str:
    if "AIVERDE_API_KEY" in st.secrets:
        return st.secrets["AIVERDE_API_KEY"]
    return os.environ.get("AIVERDE_API_KEY", "")


def read_text_file(uploaded_file):
    name = uploaded_file.name.lower()
    raw = uploaded_file.read()
    uploaded_file.seek(0)

    if name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(io.BytesIO(raw))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    if name.endswith(".docx"):
        doc = docx.Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)

    if name.endswith(".txt"):
        return raw.decode("utf-8", errors="ignore")

    return None


def call_api(api_key: str, model_name: str, system_prompt: str, user_message: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0,
    }

    response = requests.post(
        CHAT_COMPLETIONS_URL,
        headers=headers,
        json=payload,
        timeout=300,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


with st.sidebar:
    st.header("Settings")
    st.caption(f"Analysis date: {date.today().isoformat()}")
    model_name = DEFAULT_MODEL
    st.text_input("Model", value=model_name, disabled=True)
    reviewer_instruction = st.text_area(
        "Reviewer instruction",
        value="Run the short HR MQ and relevant experience review in the required 5-section format.",
        height=100,
    )
    if get_api_key():
        st.success("API key loaded from secrets or environment.")
    else:
        st.error("No API key found.")

st.subheader("1. Upload resume")
resume_file = st.file_uploader(
    "Candidate/Incumbent resume (PDF, DOCX, or TXT)",
    type=["pdf", "docx", "txt"],
)

st.subheader("2. Upload job description")
job_description_file = st.file_uploader(
    "Job description (PDF, DOCX, or TXT)",
    type=["pdf", "docx", "txt"],
    key="jd_uploader",
)

st.subheader("3. Optional follow-up detail request")
followup = st.text_input(
    "Leave blank for short output only; use later for section-specific detail.",
    placeholder="e.g., Give details on Section 2 only",
)

if st.button("▶ Run review", type="primary"):
    missing = []
    api_key = get_api_key()

    if not api_key:
        missing.append("API key in .streamlit/secrets.toml or AIVERDE_API_KEY environment variable")
    if not resume_file:
        missing.append("Resume")
    if not job_description_file:
        missing.append("Job description")

    if missing:
        st.error("Please resolve the following before running:\n\n" + "\n".join(f"• {m}" for m in missing))
    else:
        resume_text = read_text_file(resume_file)
        job_description_text = read_text_file(job_description_file)

        if not resume_text:
            st.error("Could not read the resume. Please upload a PDF, DOCX, or TXT file.")
        elif not job_description_text:
            st.error("Could not read the job description. Please upload a PDF, DOCX, or TXT file.")
        else:
            with st.spinner("Running review..."):
                user_message = f"""
Reviewer instruction: {reviewer_instruction}

--- FILE: Candidate Resume ---
{resume_text}

--- FILE: Job Description ---
{job_description_text}

Return only the required short 5-section output format.
"""
                if followup.strip():
                    user_message += f"\nAdditional request: {followup.strip()}\n"

                try:
                    result_text = call_api(
                        api_key=api_key,
                        model_name=model_name,
                        system_prompt=SYSTEM_PROMPT,
                        user_message=user_message,
                    )
                    st.success("✅ Review complete")
                    st.markdown(result_text)
                    st.download_button(
                        label="⬇ Download results as .txt",
                        data=result_text,
                        file_name="HR_MQ_Review.txt",
                        mime="text/plain",
                    )
                except requests.HTTPError:
                    st.error("API request failed. Check API key, model access, or network settings.")
                except Exception:
                    st.error("Something went wrong. Check file format, API settings, or network connection.")
