from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(
    settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
)
session = driver.session()

# Check all Task nodes
result = session.run("MATCH (t:Task) RETURN count(t) as count, collect(t) as tasks")
record = result.single()
if record:
    print(f"Total Task nodes: {record['count']}")
    if record["count"] > 0:
        tasks = record["tasks"]
        for task in tasks[:5]:
            print(f"Task: {dict(task)}")

# Check ALL nodes
result = session.run("MATCH (n) RETURN count(n) as count, labels(n) as labels LIMIT 10")
for record in result:
    print(f"Nodes with labels {record['labels']}: {record['count']}")

driver.close()
