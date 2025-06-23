from neo4j import GraphDatabase
from ollama import chat

# Update with your actual connection info
URI = "neo4j://127.0.0.1:7687"
AUTH = ("neo4j", "12345678")

driver = GraphDatabase.driver(URI, auth=AUTH)

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.verify_connectivity()
    print("Connection established.")

def run_query(cypher_query, parameters=None):
    with driver.session() as session:
        result = session.run(cypher_query, parameters or {})
        return [record.data() for record in result]

query1= """
MATCH (c:Courses)-[:Teaches]->(s:Skills)<-[:Requires]-(j:Jobs {job_title: $job_title})
RETURN DISTINCT c.course_name as course
"""
query2= """ MATCH (j:Jobs {job_title: $job_title})-[:Requires]->(s:Skills)
WHERE NOT ( (:Courses)-[:Teaches]->(s) )
RETURN DISTINCT s.name AS skill """

query3= """ MATCH (j:Jobs)
RETURN DISTINCT j.job_title AS job_title """
results3 = run_query(query3)
print("Suppoerted jobs:")
for i, row in enumerate(results3, start=1):
    print(f"{i}. {row['job_title']}")
print( )
print()


job = input("Please enter the job you want to enquire about: ")
job1= str(job)
results = run_query(query1, {"job_title": job1})
print("Required Courses for this Job are:")
for i, row in enumerate(results, start=1):
    print(f"{i}. {row['course']}")
print()
print()
results1 = run_query(query2, {"job_title": job1})
if len(results1)>0:
    print("Unfortunately these skills are not taught:")
    for i, row in enumerate(results1, start=1):
        print(f"{i}. {row['skill']}")


choice = input("Would you like a sumary of one the suggested courses(y/n):")
while choice=="y":

  course_name = input("Please enter the name of the course: ")
  if course_name in [row['course'] for row in results]:
      query4 = """MATCH (c:Courses {course_name: $course_name})-[:Teaches]->(s:Skills)
         RETURN DISTINCT s.name AS skill"""
      results4 = run_query(query4, {"course_name": str(course_name)})
      ask = 'give me a summary for the course ' + str(course_name) + 'with skills: '
      for row in results4:
          ask += row['skill'] + ', '
      stream = chat(
          model='llama3.2',
          messages=[{'role': 'user', 'content': ask}],
          stream=True,
      )
      for chunk in stream:
          print(chunk['message']['content'], end='', flush=True)

  else:
      print("Sorry this course is not part of the recommendation")


  print()

  choice = input("Would you like a sumary of one the suggested courses(y/n):")



print("Thnak you")





