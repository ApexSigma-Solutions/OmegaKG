from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687", auth=("neo4j", "please-change-this-password")
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
