import frontmatter
from pathlib import Path

vault_path = Path(r"C:\Users\steyn\OneDrive\Apps\remotely-save\Omega.as Vault")
task_files = list(vault_path.glob("Tasks/*.md"))

print(f"Found {len(task_files)} task files")

for task_file in task_files[:2]:
    print(f"\n--- {task_file.name} ---")
    post = frontmatter.load(task_file)
    print(f"Metadata: {post.metadata}")
    print(f"UID: {post.metadata.get('uid')}")
    print(f"Title: {post.metadata.get('title', task_file.stem)}")
    print(f"Status: {post.metadata.get('status', 'draft')}")
