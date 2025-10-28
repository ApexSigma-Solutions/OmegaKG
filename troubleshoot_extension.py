#!/usr/bin/env python3
"""
Troubleshoot Omega_KG Chrome Extension capture issues.

Run this to diagnose why conversations aren't being captured.
"""

import sys
from pathlib import Path

try:
    from omega_kg.settings import settings
    from neo4j import GraphDatabase
    import requests
except ImportError as e:
    print(f"❌ Import error: {e} - troubleshoot_extension.py:16")
    print("Run: poetry install - troubleshoot_extension.py:17")
    sys.exit(1)


def check_capture_server():
    """
    Check whether the local capture server's health endpoint is available.
    
    Emits brief status messages to stdout about the check and any errors encountered.
    
    Returns:
        `True` if the health endpoint returned HTTP 200 and a JSON payload, `False` otherwise.
    """
    print("1️⃣  Checking capture server... - troubleshoot_extension.py:23")
    try:
        response = requests.get("http://127.0.0.1:8765/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server running: {data} - troubleshoot_extension.py:28")
            return True
        else:
            print(f"❌ Server returned {response.status_code} - troubleshoot_extension.py:31")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server not running on port 8765 - troubleshoot_extension.py:34")
        print("Start server: poetry run python m omega_kg.capture_server - troubleshoot_extension.py:35")
        return False
    except Exception as e:
        print(f"❌ Error: {e} - troubleshoot_extension.py:38")
        return False


def check_vault_accessible():
    """
    Verify the Obsidian vault is accessible and ensure the AI_Conversations directory and expected platform subfolders exist.
    
    If the AI_Conversations platform subfolders are missing, this function will create them.
    
    Returns:
        bool: `True` if the vault and AI_Conversations directory are accessible (platform folders present or created), `False` otherwise.
    """
    print("\n2️⃣  Checking Obsidian vault... - troubleshoot_extension.py:44")
    vault_path = Path(settings.obsidian_vault_path)
    
    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path} - troubleshoot_extension.py:48")
        return False
    
    ai_conv_path = vault_path / "AI_Conversations"
    if not ai_conv_path.exists():
        print(f"❌ AI_Conversations folder missing: {ai_conv_path} - troubleshoot_extension.py:53")
        return False
    
    # Check for platform folders
    platforms = ["Claude.ai", "ChatGPT", "Gemini", "Perplexity", "GitHub_Copilot", "Qwen"]
    missing = []
    for platform in platforms:
        platform_path = ai_conv_path / platform
        if not platform_path.exists():
            missing.append(platform)
    
    if missing:
        print(f"⚠️  Missing platform folders: {', '.join(missing)} - troubleshoot_extension.py:65")
        print(f"Creating folders... - troubleshoot_extension.py:66")
        for platform in missing:
            (ai_conv_path / platform).mkdir(parents=True, exist_ok=True)
    
    print(f"✅ Vault accessible: {vault_path} - troubleshoot_extension.py:70")
    print(f"✅ AI_Conversations: {ai_conv_path} - troubleshoot_extension.py:71")
    return True


def check_neo4j():
    """
    Check connectivity to the configured Neo4j instance and report basic ChatSession node counts.
    
    Returns:
        bool: `True` if a simple test query succeeds and the ChatSession node count is retrieved, `False` otherwise.
    """
    print("\n3️⃣  Checking Neo4j... - troubleshoot_extension.py:77")
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            if result.single():
                print(f"✅ Neo4j connected: {settings.neo4j_uri} - troubleshoot_extension.py:86")
                
                # Check for recent ChatSession nodes
                result = session.run(
                    "MATCH (s:ChatSession) RETURN count(s) as total"
                )
                count = result.single()["total"]
                print(f"ℹ️  Total ChatSession nodes: {count} - troubleshoot_extension.py:93")
                
                return True
        driver.close()
    except Exception as e:
        print(f"❌ Neo4j error: {e} - troubleshoot_extension.py:98")
        print(f"Check: {settings.neo4j_uri} - troubleshoot_extension.py:99")
        return False


def check_recent_captures():
    """
    Summarizes recent captured conversations found under the vault's AI_Conversations folder.
    
    Prints warnings if the vault or AI_Conversations directory is missing, reports the total number of Markdown capture files, and lists up to the five most recent captures with their platform (parent folder), filename, and modification timestamp.
    """
    print("\n4️⃣  Checking recent captures... - troubleshoot_extension.py:105")
    vault_path = Path(settings.obsidian_vault_path)
    ai_conv_path = vault_path / "AI_Conversations"
    
    if not ai_conv_path.exists():
        print("⚠️  No captures found (AI_Conversations missing) - troubleshoot_extension.py:110")
        return
    
    # Find all markdown files
    md_files = list(ai_conv_path.rglob("*.md"))
    if not md_files:
        print("⚠️  No conversation files found - troubleshoot_extension.py:116")
        return
    
    # Sort by modification time
    md_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    print(f"ℹ️  Total captures: {len(md_files)} - troubleshoot_extension.py:122")
    print(f"📄 Most recent (top 5): - troubleshoot_extension.py:123")
    for i, file in enumerate(md_files[:5], 1):
        platform = file.parent.name
        mod_time = file.stat().st_mtime
        from datetime import datetime
        mod_datetime = datetime.fromtimestamp(mod_time)
        print(f"{i}. {platform}: {file.name} ({mod_datetime.strftime('%Y%m%d %H:%M')}) - troubleshoot_extension.py:129")


def print_extension_instructions():
    """
    Prints a concise troubleshooting checklist for the Omega_KG Chrome extension.
    
    Provides steps to verify the extension is installed and in developer mode, that the extension is listed as "Omega_KG Chat Capture", that it appears on supported AI platforms, that the floating Ω button is visible, and where to inspect browser and service worker console logs. Ends with a tip to force a manual capture to exercise logging.
    """
    print("\n5️⃣  Chrome Extension Checklist: - troubleshoot_extension.py:134")
    print("□ Extension loaded in chrome://extensions/ - troubleshoot_extension.py:135")
    print("□ Developer mode enabled - troubleshoot_extension.py:136")
    print("□ Extension shows 'Omega_KG Chat Capture' - troubleshoot_extension.py:137")
    print("□ Visit supported AI platform (Claude.ai, ChatGPT, etc.) - troubleshoot_extension.py:138")
    print("□ Look for floating Ω button (bottomright) - troubleshoot_extension.py:139")
    print("□ Open browser console (F12) and check for [Omega_KG] logs - troubleshoot_extension.py:140")
    print("□ Click service worker link in chrome://extensions/ - troubleshoot_extension.py:141")
    print("□ Service worker console should show message handling - troubleshoot_extension.py:142")
    print("\n   💡 TIP: Click the Ω button to force manual capture and check logs - troubleshoot_extension.py:143")


def main():
    """
    Run a suite of diagnostic checks for the Omega_KG Chrome Extension capture workflow and report results to the console.
    
    This function executes health checks for the local capture server, Obsidian vault accessibility (including required AI_Conversations subfolders), and Neo4j connectivity, then lists recent captured conversation files and prints a checklist of extension troubleshooting steps. All results and guidance are written to standard output.
    """
    print("= - troubleshoot_extension.py:148" * 60)
    print("Omega_KG Chrome Extension Diagnostics - troubleshoot_extension.py:149")
    print("= - troubleshoot_extension.py:150" * 60)
    
    checks = [
        check_capture_server(),
        check_vault_accessible(),
        check_neo4j()
    ]
    
    check_recent_captures()
    print_extension_instructions()
    
    print("\n - troubleshoot_extension.py:161" + "=" * 60)
    if all(checks):
        print("✅ All systems operational! - troubleshoot_extension.py:163")
        print("\nIf extension still not capturing: - troubleshoot_extension.py:164")
        print("1. Reload extension in chrome://extensions/ - troubleshoot_extension.py:165")
        print("2. Refresh AI chat page - troubleshoot_extension.py:166")
        print("3. Click Ω button to test manual capture - troubleshoot_extension.py:167")
        print("4. Check browser console (F12) for [Omega_KG] logs - troubleshoot_extension.py:168")
    else:
        print("❌ Some issues detected  fix above errors first - troubleshoot_extension.py:170")
    print("= - troubleshoot_extension.py:171" * 60)


if __name__ == "__main__":
    main()
