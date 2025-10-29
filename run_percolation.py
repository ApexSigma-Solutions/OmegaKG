#!/usr/bin/env python
"""
Percolation Engine Runner
Extracts tasks, commits, and links from Obsidian vault into Neo4j
"""

from pathlib import Path
from omega_kg.settings import settings
from omega_kg.percolation import create_percolation_engine


def main():
    print("📊 Omega_KG Percolation Engine")
    print("=" * 70)
    print(f"🔗 Neo4j URI:        {settings.neo4j_uri}")
    print(f"👤 Neo4j User:       {settings.neo4j_user}")
    print(f"📁 Vault Path:       {settings.obsidian_vault_path}")
    print("=" * 70)
    
    try:
        # Create engine
        engine = create_percolation_engine(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password
        )
        print("✅ Connected to Neo4j\n")
        
        # Verify vault exists
        vault_path = Path(settings.obsidian_vault_path)
        if not vault_path.exists():
            print(f"❌ Vault path not found: {vault_path}")
            return 1
        
        print("🔄 Scanning vault for markdown files...")
        md_files = list(vault_path.rglob("*.md"))
        print(f"   Found {len(md_files)} markdown files\n")
        
        # Run percolation
        print("🔄 Running percolation engine...")
        stats = engine.percolate_from_vault(vault_path)
        
        # Print results
        print("\n" + "=" * 70)
        print("✅ Percolation complete!")
        print("=" * 70)
        print("📈 Results:")
        print(f"   • Tasks processed:    {stats.get('tasks', 0):>6}")
        print(f"   • Commits processed:  {stats.get('commits', 0):>6}")
        print(f"   • Links created:      {stats.get('links', 0):>6}")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during percolation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
