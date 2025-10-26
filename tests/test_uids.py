from pathlib import Path
import frontmatter

vault_path = Path(r"C:\Users\steyn\OneDrive\Apps\remotely-save\Omega.as Vault")
task_files = list(vault_path.glob("Tasks/*.md"))

print(f"Total: {len(task_files)}\n")

for f in task_files[:15]:
    post = frontmatter.load(str(f))
    uid = post.metadata.get("uid", "NONE")
    print(f"{f.name[:50]:50} | uid={uid}")
