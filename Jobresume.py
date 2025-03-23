import os
import streamlit as st
import requests
from openai import OpenAI
import PyPDF2

# --------------------------
# SESSION STATE INITIALIZATION
# --------------------------
if "jobs" not in st.session_state:
    st.session_state.jobs = None  # Holds the list of job results
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "salary_range" not in st.session_state:
    st.session_state.salary_range = (50000, 100000)
if "uploaded_resumes" not in st.session_state:
    st.session_state.uploaded_resumes = {}  # job index -> resume text
if "tailored_recs" not in st.session_state:
    st.session_state.tailored_recs = {}  # job index -> tailored recommendations
if "current_page" not in st.session_state:
    st.session_state.current_page = "search"

# --------------------------
# SETUP OPENAI CLIENT
# --------------------------
RAPIDAPI_KEY = os.getenv("RapidAPI") if os.getenv("RapidAPI") else st.secrets["RapidAPI"]["key"]
OPENAI_API_KEY = os.getenv("General") if os.getenv("General") else st.secrets["General"]["key"]

client = OpenAI(api_key=OPENAI_API_KEY)

# --------------------------
# FUNCTION DEFINITIONS
# --------------------------
def get_ai_job_recommendations(query):
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert career assistant."},
            {"role": "user", "content": f"Given the job search '{query}', suggest three similar job titles."}
        ]
    )
    return completion.choices[0].message.content

def tailor_resume(resume_text, job_details):
    prompt = (
        f"Given my resume below and the job posting details '{job_details}', "
        "provide specific recommendations on how to tailor my resume for this job. "
        "List actionable improvements and suggest rewordings where necessary.\n\n"
        f"Resume:\n{resume_text}"
    )
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert career advisor and resume reviewer."},
            {"role": "user", "content": prompt}
        ]
    )
    return completion.choices[0].message.content

def render_search_page():
    st.title("Job Search with Resume & Cover Letter Generation")
    st.subheader("Job Search")
    job_query = st.text_input(
        "Enter job search query (e.g., 'Developer jobs in Chicago')",
        value=st.session_state.search_query or "Developer jobs in Chicago"
    )
    employment_type = st.radio("Select Employment Type", options=[
        "All", "Full-time", "Part-time", "Contractor", "Entry Level"
    ])
    remote_filter = st.radio("Remote Jobs Only?", options=["All", "Yes", "No"])
    st.session_state.salary_range = st.slider(
        "Select Salary Range ($)",
        0, 300000, st.session_state.salary_range, step=10000
    )
    
    if st.button("Search"):
        st.session_state.search_query = job_query
        query = job_query
        if employment_type != "All":
            query += f" {employment_type}"
        if remote_filter == "Yes":
            query += " remote"
        elif remote_filter == "No":
            query += " onsite"
        
        url = "https://jsearch.p.rapidapi.com/search"
        querystring = {
            "query": query,
            "page": "1",
            "num_pages": "1",
            "country": "us",
            "date_posted": "all"
        }
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": "jsearch.p.rapidapi.com"
        }
        with st.spinner("Searching for jobs..."):
            response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200:
            data = response.json()
            jobs = data.get("data", [])
            if jobs:
                st.session_state.jobs = jobs
                st.session_state.current_page = "results"
                st.rerun()
            else:
                st.error("No jobs found for your search.")
        else:
            st.error("Error fetching jobs. Please try again later.")

def render_results_page():
    st.title("Job Search with Resume & Cover Letter Generation")
    st.subheader("Job Listings")
    jobs = st.session_state.jobs
    for i, job in enumerate(jobs):
        st.markdown(f"### {job.get('job_title', 'No Title')}")
        st.write(f"**Employer:** {job.get('employer_name', 'N/A')}")
        st.write(f"**Location:** {job.get('job_location', 'N/A')}")
        st.write(f"**Employment Type:** {job.get('job_employment_type', 'N/A')}")
        st.write(f"**Posted:** {job.get('job_posted_at', 'N/A')}")
        st.markdown(f"[Apply Here]({job.get('job_apply_link', '#')})")
        with st.expander("View Job Description"):
            st.write(job.get("job_description", "No description available."))
        
        with st.expander("Upload Your Resume for Tailoring"):
            uploaded_file = st.file_uploader("Upload your resume (PDF or TXT)", type=["pdf", "txt"], key=f"resume_{i}")
            if uploaded_file:
                file_extension = uploaded_file.name.split('.')[-1].lower()
                if file_extension == "txt":
                    resume_text = uploaded_file.read().decode("utf-8")
                else:  # PDF handling
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    resume_text = "".join(page.extract_text() or "" for page in pdf_reader.pages)
                st.session_state.uploaded_resumes[i] = resume_text
                # Generate tailored recommendations immediately upon upload
                recs = tailor_resume(resume_text, job.get("job_description", ""))
                st.info("Tailored Resume Recommendations:")
                st.write(recs)
        
        with st.expander("Generate Cover Letter"):
            # Instead of auto-generating the cover letter, prompt the user to message you on LinkedIn
            if st.button("Request Cover Letter via LinkedIn", key=f"cover_{i}"):
                # Display a clickable link to open a new LinkedIn message window.
                st.info(
                    "Please [click here](https://www.linkedin.com/in/josh-poresky956/ 'Message Josh on LinkedIn') "
                    "to send me a direct message on LinkedIn and request a personalized cover letter."
                )
                # If you prefer email, replace the above link with:
                # st.info("Please [click here](mailto:josh.poresky@gmail.com?subject=Request%20Cover%20Letter) to email me for a personalized cover letter.")
        
        st.markdown("---")
    
    if st.button("New Search"):
        st.session_state.jobs = None
        st.session_state.current_page = "search"
        st.experimental_rerun()

# --------------------------
# PAGE RENDERING
# --------------------------
if st.session_state.current_page == "search":
    render_search_page()
elif st.session_state.current_page == "results":
    render_results_page()
