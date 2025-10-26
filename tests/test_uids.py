from pathlib import Path
import frontmatter
from src.settings import Settings

settings = Settings()
vault_path = Path(settings.obsidian_vault_path)
task_files = list(vault_path.glob("Tasks/*.md"))

print(f"Total: {len(task_files)}\n")

for f in task_files[:15]:
    post = frontmatter.load(str(f))
    uid = post.metadata.get("uid", "NONE")
    print(f"{f.name[:50]:50} | uid={uid}")
