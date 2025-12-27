# Omega_KG

> **Your AI conversations are valuable. Stop losing them.**

## What is Omega_KG?

Ever had a brilliant conversation with ChatGPT, Claude, or Gemini — only to forget what you discussed a week later? Omega_KG solves this by automatically capturing your AI conversations and turning them into a searchable knowledge base.

**Think of it as a "second brain" that:**

- 🎯 **Captures** every AI conversation automatically (no copy-paste needed)
- 🔗 **Connects** ideas across different conversations and projects
- ✅ **Tracks** decisions that turn into tasks
- 📊 **Visualizes** how your ideas and work relate to each other

---

## How It Works (The Simple Version)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  You chat with  │     │   Omega_KG      │     │  Your personal  │
│  ChatGPT/Claude │ ──▶ │   captures it   │ ──▶ │  knowledge base │
│  /Gemini/etc    │     │   automatically │     │  (searchable!)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**That's it.** A Chrome extension watches your AI conversations, saves them to your computer, and organizes them so you can find anything later.

---

## Architecture Overview

### System Components

```mermaid
flowchart TB
    subgraph Browser["🌐 Your Browser"]
        EXT[Chrome Extension]
        AI[AI Platforms<br/>Claude, ChatGPT, Gemini...]
    end

    subgraph LocalServer["💻 Your Computer"]
        CAP[Capture Server<br/>localhost:8765]
        VAULT[Obsidian Vault<br/>Markdown Files]
    end

    subgraph Databases["🗄️ Storage"]
        NEO[Neo4j Graph DB<br/>Relationships]
        PG[PostgreSQL<br/>Events & Sessions]
    end

    subgraph External["☁️ External Services"]
        LINEAR[Linear<br/>Task Management]
        GIT[Git<br/>Code Commits]
    end

    AI -->|You chat| EXT
    EXT -->|Captures conversation| CAP
    CAP -->|Saves markdown| VAULT
    CAP -->|Stores graph| NEO
    CAP -->|Logs events| PG
    CAP <-->|Syncs tasks| LINEAR
    NEO <-->|Links commits| GIT
```

### Data Flow: From Chat to Knowledge

```mermaid
sequenceDiagram
    participant You
    participant AI as AI Platform
    participant Ext as Chrome Extension
    participant Server as Capture Server
    participant Vault as Obsidian Vault
    participant Graph as Neo4j

    You->>AI: Ask a question
    AI->>You: Respond with answer
    Note over Ext: Watches for new messages
    Ext->>Ext: Extract conversation
    Ext->>Server: POST /capture
    Server->>Vault: Save as markdown
    Server->>Graph: Create nodes & links
    Server->>Ext: ✓ Captured!
```

### The Knowledge Graph: How Ideas Connect

```mermaid
graph LR
    subgraph Sessions["💬 Chat Sessions"]
        S1[Session: API Design]
        S2[Session: Bug Fix]
    end

    subgraph Decisions["💡 Decisions"]
        D1[Use REST not GraphQL]
        D2[Add retry logic]
    end

    subgraph Tasks["✅ Tasks"]
        T1[Implement REST API]
        T2[Add error handling]
    end

    subgraph Commits["📝 Git Commits"]
        C1[feat: REST endpoints]
        C2[fix: retry mechanism]
    end

    S1 -->|contains| D1
    S2 -->|contains| D2
    D1 -->|becomes| T1
    D2 -->|becomes| T2
    T1 -->|implemented by| C1
    T2 -->|implemented by| C2

    style S1 fill:#e1f5fe
    style S2 fill:#e1f5fe
    style D1 fill:#fff3e0
    style D2 fill:#fff3e0
    style T1 fill:#e8f5e9
    style T2 fill:#e8f5e9
    style C1 fill:#fce4ec
    style C2 fill:#fce4ec
```

---

## Task Lifecycle: From Idea to Done

Tasks don't just sit there — they move through stages automatically:

```mermaid
stateDiagram-v2
    [*] --> Draft: New task created

    Draft --> Ready: Requirements clear
    Draft --> Archived: Inactive 14 days

    Ready --> Active: Work started
    Ready --> Draft: Needs more info

    Active --> Blocked: Waiting on something
    Active --> Completed: Work finished
    Active --> Blocked: No commits 30 days

    Blocked --> Active: Unblocked
    Blocked --> Archived: Stuck too long

    Completed --> Archived: After 90 days
    Archived --> [*]

    note right of Draft: Auto-archive if<br/>forgotten
    note right of Active: Auto-block if<br/>no progress
    note right of Completed: Auto-archive<br/>after 90 days
```

**What this means:**

- 📝 **Draft** → You captured an idea but haven't fleshed it out
- ✅ **Ready** → Clear enough to start working on
- 🔨 **Active** → You're currently working on it
- 🚧 **Blocked** → Waiting for something (auto-detected if no commits)
- ✓ **Completed** → Done!
- 📦 **Archived** → Out of sight, but searchable

---

## Decision Logic: When Things Happen Automatically

```mermaid
flowchart TD
    START([Every 5 minutes]) --> CHECK{Check all tasks}

    CHECK --> DRAFT{Is Draft?}
    DRAFT -->|Yes| DRAFT_AGE{Age > 14 days?}
    DRAFT_AGE -->|Yes| WARN_DRAFT[Send warning email]
    WARN_DRAFT --> ARCHIVE_DRAFT[Archive task]
    DRAFT_AGE -->|No| NEXT1[Check next task]

    CHECK --> ACTIVE{Is Active?}
    ACTIVE -->|Yes| COMMIT_CHECK{Last commit<br/>> 30 days?}
    COMMIT_CHECK -->|Yes| BLOCK[Mark as Blocked]
    COMMIT_CHECK -->|No| NEXT2[Check next task]

    CHECK --> COMPLETED{Is Completed?}
    COMPLETED -->|Yes| COMP_AGE{Age > 90 days?}
    COMP_AGE -->|Yes| ARCHIVE_COMP[Archive task]
    COMP_AGE -->|No| NEXT3[Check next task]

    ARCHIVE_DRAFT --> DONE([Done])
    BLOCK --> DONE
    ARCHIVE_COMP --> DONE
    NEXT1 --> DONE
    NEXT2 --> DONE
    NEXT3 --> DONE
```

---

## Supported AI Platforms

| Platform | Status | Auto-Capture |
|----------|--------|--------------|
| ChatGPT | ✅ Supported | Yes |
| Claude | ✅ Supported | Yes |
| Gemini | ✅ Supported | Yes |
| Perplexity | ✅ Supported | Yes |
| DeepSeek | ✅ Supported | Yes |
| Mistral | ✅ Supported | Yes |
| AI Studio | ✅ Supported | Yes |
| Qwen | ✅ Supported | Yes |

---

## Quick Start

### What You Need

- **Python 3.12+** — The programming language
- **Poetry** — Manages Python packages
- **Neo4j** — Graph database (free desktop version works)
- **Chrome/Edge** — For the browser extension

### 5-Minute Setup

```bash
# 1. Get the code
git clone https://github.com/ApexSigma-Solutions/omega_kg.git
cd omega_kg

# 2. Install dependencies
poetry install --with dev

# 3. Create your config file
cp .env.example .env
# Edit .env with your passwords and paths

# 4. Start the server
poetry run capture-server
# Server runs at http://localhost:8765
```

### Install the Chrome Extension

1. Open `chrome://extensions` in Chrome
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `chrome-extension/` folder
5. Click the extension icon → Enter your API key

**Done!** Start chatting with any AI platform and watch conversations appear in your vault.

---

## Port Reference

| Service | Port | Purpose |
|---------|------|---------|
| Capture Server | 8765 | Receives conversations from extension |
| Neo4j Browser | 7474 | Graph visualization UI |
| Neo4j Bolt | 7687 | Database connections |
| PostgreSQL | 5433 | Event storage |
| Ollama | 11434 | Local AI embeddings |

See [docs/PORT_MAPPING.md](./docs/PORT_MAPPING.md) for detailed configuration.

---

## Project Structure

```
omega_kg/
├── capture_server.py   # Receives conversations from browser
├── lifecycle.py        # Manages task states automatically
├── linear_sync.py      # Syncs with Linear task manager
├── percolation.py      # Extracts insights into graph
├── settings.py         # Configuration management
│
├── chrome-extension/   # Browser extension files
│   ├── background.js   # Handles communication
│   ├── content.js      # Extracts conversations
│   └── config.js       # Extension settings
│
└── docs/               # Documentation
    └── PORT_MAPPING.md # Network configuration
```

---

## Common Commands

```bash
# Start the capture server
poetry run capture-server

# Run lifecycle checks (preview mode)
poetry run python -m omega_kg.lifecycle --dry-run

# Run tests
poetry run pytest

# Check code quality
poetry run ruff check .
```

---

## Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Key settings to configure:

```env
# Where to save conversations
OBSIDIAN_VAULT_PATH=D:\your\vault\path

# Neo4j database
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your-password

# Server port (default 8765)
APP_PORT=8765
```

---

## Troubleshooting

### "Package not installed" Error

If you encounter "Package not installed" errors, see the [Installation Troubleshooting Guide](docs/INSTALLATION_TROUBLESHOOTING.md) for detailed resolution steps.

### Extension says "Failed to fetch"

→ Is the capture server running? Check `http://localhost:8765/health`

### Conversations not appearing

→ Reload the extension in `chrome://extensions`

### Neo4j connection failed

→ Make sure Neo4j Desktop is running

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and test: `poetry run pytest`
4. Submit a pull request

See [SECURITY.md](./SECURITY.md) for security best practices and vulnerability reporting.

---

## Security

We take security seriously. Please review our [Security Policy](./SECURITY.md) for:

- Reporting security vulnerabilities
- Security best practices
- Secret management guidelines
- Pre-commit security hooks

**Never commit private keys, API keys, or credentials to the repository.**

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

---

## Links

- 📖 [Full Documentation](./docs/index.md)
- 🐛 [Report Issues](https://github.com/ApexSigma-Solutions/omega_kg/issues)
- 🔒 [Security Policy](./SECURITY.md)
- 📋 [API Reference](./docs/reference.md)
- 🌐 [Port Configuration](./docs/PORT_MAPPING.md)
