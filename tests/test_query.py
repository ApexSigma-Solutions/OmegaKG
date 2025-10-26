from neo4j import GraphDatabase
from omega_kg.settings import Settings

settings = Settings()
driver = GraphDatabase.driver(
    settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
)
session = driver.session()

# Check all tasks
result = session.run("MATCH (t:Task) RETURN count(t) as count")
count_result = result.single()
print(f"Total tasks: {count_result['count']}")

# Check one task with all properties
result = session.run("MATCH (t:Task) RETURN t LIMIT 1")
task = result.single()
if task:
    print(f"Task: {task['t']}")
    print(f"Properties: {dict(task['t'])}")

driver.close()
