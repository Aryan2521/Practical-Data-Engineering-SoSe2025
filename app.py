import streamlit as st
from neo4j import GraphDatabase
from ollama import chat
import pandas as pd

# Neo4j setup
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "12345678")
driver = GraphDatabase.driver(URI, auth=AUTH)

def run_query(cypher, parameters=None):
    with driver.session() as session:
        result = session.run(cypher, parameters or {})
        return [record.data() for record in result]

# Cypher queries
query_fuzzy_jobs = """
MATCH (j:Job)
WHERE toLower(trim(j.name)) CONTAINS toLower($partial)
RETURN DISTINCT trim(j.name) AS job_title
"""

query_all_jobs = """
MATCH (j:Job)
RETURN DISTINCT trim(j.name) AS job_title
ORDER BY job_title
"""

query_recommend_courses = """
MATCH (j:Job {name: $job_title})-[:REQUIRES]->(s:Skill)
WITH COLLECT(s.name) AS required_skills
MATCH (c:Course)-[:TEACHES]->(s:Skill)
WHERE s.name IN required_skills
WITH c.name AS course, COUNT(DISTINCT s) AS coverage
RETURN course, coverage
ORDER BY coverage DESC
"""

query_course_skills = """
MATCH (c:Course {name: $course_name})-[:TEACHES]->(s:Skill)
RETURN DISTINCT s.name AS skill
"""

query_missing_skills = """
MATCH (j:Job {name: $job_title})-[:REQUIRES]->(s:Skill)
WHERE NOT EXISTS {
  MATCH (:Course)-[:TEACHES]->(s)
}
RETURN DISTINCT s.name AS skill
"""

# UI Layout
st.set_page_config(page_title="Curriculum Mapper", layout="centered")
st.title("🎓 Career Path & Course Recommender")
st.caption("Powered by Neo4j + LLaMA3")

# Optional: Show all available job titles
with st.expander("📋 Click to view all available job titles"):
    all_jobs = run_query(query_all_jobs)
    for j in all_jobs:
        st.markdown("- " + j["job_title"])

# Search for job title
keyword = st.text_input("Enter job keyword (e.g. developer, analyst, cloud):", "").strip()
if keyword:
    matches = run_query(query_fuzzy_jobs, {"partial": keyword})
    job_titles = [row["job_title"] for row in matches]

    if job_titles:
        job_choice = st.selectbox("🎯 Select a job title to explore:", job_titles)
        if job_choice:
            st.success(f"Target job selected: {job_choice}")

            # Recommended courses
            recommended = run_query(query_recommend_courses, {"job_title": job_choice})
            if recommended:
                st.subheader("📘 Recommended Courses (ranked by skill coverage):")
                df = pd.DataFrame(recommended)
                st.dataframe(df)

                st.bar_chart(df.set_index("course"))

                # Missing skills
                missing = run_query(query_missing_skills, {"job_title": job_choice})
                if missing:
                    st.warning("⚠️ Skills required but not taught:")
                    st.markdown(", ".join([m["skill"] for m in missing]))

                # Select a course to get summary
                course_names = [r["course"] for r in recommended]
                selected_course = st.selectbox("🧾 Select a course to get a LLaMA3 summary:", course_names)

                if st.button("🔍 Generate Summary"):
                    skills = run_query(query_course_skills, {"course_name": selected_course})
                    prompt = f"Summarize the course '{selected_course}' for someone aiming to become a {job_choice}. It teaches the following skills: "
                    prompt += ", ".join([s["skill"] for s in skills])

                    with st.spinner("Generating summary via LLaMA3..."):
                        stream = chat(model="llama3", messages=[{"role": "user", "content": prompt}], stream=True)
                        response = ""
                        for chunk in stream:
                            response += chunk["message"]["content"]
                        st.success("💬 Course Summary:")
                        st.write(response)
            else:
                st.error("No courses found for this job.")
    else:
        st.warning("❌ No matching jobs found. Try a broader keyword or check the full list above.")
