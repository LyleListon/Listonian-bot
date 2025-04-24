# MCP Servers Setup Guide

This guide provides comprehensive setup instructions for 13 powerful MCP servers that can be used with the Augment extension or any other MCP-compatible client.

## Table of Contents

1. [GitHub MCP Server](#1-github-mcp-server)
2. [Context7 MCP Server](#2-context7-mcp-server)
3. [MCP Compass](#3-mcp-compass)
4. [Setup Helper](#4-setup-helper)
5. [Brave Search](#5-brave-search)
6. [Memory](#6-memory)
7. [Filesystem](#7-filesystem)
8. [Serena](#8-serena)
9. [Bankless Onchain](#9-bankless-onchain)
10. [Last9](#10-last9)
11. [thirdweb](#11-thirdweb)
12. [Vibe Check](#12-vibe-check)
13. [GemSuite](#13-gemsuite)

## 1. GitHub MCP Server

### Installation

```bash
npm install -g @modelcontextprotocol/server-github
```

### Configuration

```json
"github": {
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-github"
  ],
  "env": {
    "GITHUB_TOKEN": "YOUR_GITHUB_TOKEN_HERE"
  },
  "disabled": false,
  "alwaysAllow": []
}
```

### Required API Keys

- **GITHUB_TOKEN**: Generate from [GitHub Developer Settings](https://github.com/settings/tokens)

## 2. Context7 MCP Server

### Installation

```bash
npm install -g @upstash/context7-mcp
```

### Configuration

```json
"context7": {
  "command": "npx",
  "args": [
    "-y",
    "@upstash/context7-mcp@latest"
  ],
  "env": {},
  "disabled": false,
  "alwaysAllow": []
}
```

## 3. MCP Compass

### Installation

```bash
npm install -g @liuyoshio/mcp-compass
```

### Configuration

```json
"mcp-compass": {
  "command": "npx",
  "args": [
    "-y",
    "@liuyoshio/mcp-compass"
  ],
  "env": {},
  "disabled": false,
  "alwaysAllow": []
}
```

## 4. Setup Helper

### Installation

No installation required - this is a built-in server.

### Configuration

```json
"setup-helper": {
  "command": "undefined",
  "args": [],
  "env": {},
  "disabled": false,
  "alwaysAllow": []
}
```

## 5. Brave Search

### Installation

```bash
npm install -g @modelcontextprotocol/server-brave-search
```

### Configuration

```json
"brave-search": {
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-brave-search"
  ],
  "env": {},
  "disabled": false,
  "alwaysAllow": []
}
```

## 6. Memory

### Installation

```bash
npm install -g @modelcontextprotocol/server-memory
```

### Configuration

```json
"memory": {
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-memory"
  ],
  "env": {},
  "disabled": false,
  "alwaysAllow": []
}
```

## 7. Filesystem

### Installation

No installation required - this is a built-in server.

### Configuration

```json
"filesystem": {
  "command": "undefined",
  "args": [],
  "env": {},
  "disabled": false,
  "alwaysAllow": []
}
```

## 8. Serena

### Installation

```bash
npm install -g @serena-ai/mcp
```

### Configuration

```json
"serena": {
  "command": "npx",
  "args": [
    "@serena-ai/mcp"
  ],
  "env": {},
  "disabled": false,
  "alwaysAllow": []
}
```

## 9. Bankless Onchain

### Installation

```bash
npm install -g @bankless/onchain-mcp
```

### Configuration

```json
"bankless-onchain": {
  "command": "npx",
  "args": [
    "@bankless/onchain-mcp"
  ],
  "env": {
    "BANKLESS_API_TOKEN": "YOUR_BANKLESS_API_TOKEN_HERE"
  },
  "disabled": false,
  "alwaysAllow": []
}
```

### Required API Keys

- **BANKLESS_API_TOKEN**: Get from Bankless dashboard

## 10. Last9

### Installation

```bash
npm install -g @last9/mcp-server
```

### Configuration

```json
"last9": {
  "command": "npx",
  "args": [
    "@last9/mcp-server"
  ],
  "env": {
    "LAST9_AUTH_TOKEN": "YOUR_LAST9_AUTH_TOKEN_HERE"
  },
  "disabled": false,
  "alwaysAllow": []
}
```

### Required API Keys

- **LAST9_AUTH_TOKEN**: Get from [Last9 API Access](https://app.last9.io/v2/organizations/gmail-lylepaul78/settings/api-access)

## 11. thirdweb

### Installation

```bash
pipx install thirdweb-mcp
```

### Configuration

```json
"thirdweb-mcp": {
  "command": "thirdweb-mcp",
  "args": [],
  "env": {
    "THIRDWEB_SECRET_KEY": "YOUR_THIRDWEB_SECRET_KEY_HERE"
  },
  "disabled": true,
  "alwaysAllow": []
}
```

### Required API Keys

- **THIRDWEB_SECRET_KEY**: Get from [thirdweb dashboard](https://thirdweb.com/dashboard)

## 12. Vibe Check

### Installation

Method 1 (Recommended):
```bash
npx -y @smithery/cli install @PV-Bhat/vibe-check-mcp-server --client claude
```

Method 2 (Manual):
```bash
git clone https://github.com/PV-Bhat/vibe-check-mcp-server.git
cd vibe-check-mcp-server
npm install
npm run build
```

### Configuration

```json
"vibe-check": {
  "command": "node",
  "args": [
    "/path/to/vibe-check-mcp-server/build/index.js"
  ],
  "env": {
    "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY_HERE"
  },
  "disabled": false,
  "alwaysAllow": []
}
```

### Required API Keys

- **GEMINI_API_KEY**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

## 13. GemSuite

### Installation

Method 1 (Recommended):
```bash
npx -y @smithery/cli@latest install @PV-Bhat/gemsuite-mcp --client claude
```

Method 2 (Manual):
```bash
git clone https://github.com/PV-Bhat/gemsuite-mcp.git
cd gemsuite-mcp
npm install
npm run build
```

### Configuration

```json
"gemsuite-mcp": {
  "command": "node",
  "args": [
    "/path/to/gemsuite-mcp/index.js"
  ],
  "env": {
    "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY_HERE"
  },
  "disabled": false,
  "alwaysAllow": []
}
```

### Required API Keys

- **GEMINI_API_KEY**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Complete Configuration Example

Here's a complete configuration example with all 13 MCP servers:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_TOKEN": "YOUR_GITHUB_TOKEN_HERE"
      },
      "disabled": false,
      "alwaysAllow": []
    },
    "context7": {
      "command": "npx",
      "args": [
        "-y",
        "@upstash/context7-mcp@latest"
      ],
      "env": {},
      "disabled": false,
      "alwaysAllow": []
    },
    "mcp-compass": {
      "command": "npx",
      "args": [
        "-y",
        "@liuyoshio/mcp-compass"
      ],
      "env": {},
      "disabled": false,
      "alwaysAllow": []
    },
    "setup-helper": {
      "command": "undefined",
      "args": [],
      "env": {},
      "disabled": false,
      "alwaysAllow": []
    },
    "brave-search": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-brave-search"
      ],
      "env": {},
      "disabled": false,
      "alwaysAllow": []
    },
    "memory": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-memory"
      ],
      "env": {},
      "disabled": false,
      "alwaysAllow": []
    },
    "filesystem": {
      "command": "undefined",
      "args": [],
      "env": {},
      "disabled": false,
      "alwaysAllow": []
    },
    "serena": {
      "command": "npx",
      "args": [
        "@serena-ai/mcp"
      ],
      "env": {},
      "disabled": false,
      "alwaysAllow": []
    },
    "bankless-onchain": {
      "command": "npx",
      "args": [
        "@bankless/onchain-mcp"
      ],
      "env": {
        "BANKLESS_API_TOKEN": "YOUR_BANKLESS_API_TOKEN_HERE"
      },
      "disabled": false,
      "alwaysAllow": []
    },
    "last9": {
      "command": "npx",
      "args": [
        "@last9/mcp-server"
      ],
      "env": {
        "LAST9_AUTH_TOKEN": "YOUR_LAST9_AUTH_TOKEN_HERE"
      },
      "disabled": false,
      "alwaysAllow": []
    },
    "thirdweb-mcp": {
      "command": "thirdweb-mcp",
      "args": [],
      "env": {
        "THIRDWEB_SECRET_KEY": "YOUR_THIRDWEB_SECRET_KEY_HERE"
      },
      "disabled": true,
      "alwaysAllow": []
    },
    "vibe-check": {
      "command": "node",
      "args": [
        "/path/to/vibe-check-mcp-server/build/index.js"
      ],
      "env": {
        "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY_HERE"
      },
      "disabled": false,
      "alwaysAllow": []
    },
    "gemsuite-mcp": {
      "command": "node",
      "args": [
        "/path/to/gemsuite-mcp/index.js"
      ],
      "env": {
        "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY_HERE"
      },
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

## API Keys

Here are the API keys you'll need to collect:

1. **GITHUB_TOKEN**: For GitHub MCP Server -- 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

2. **BANKLESS_API_TOKEN**: For Bankless Onchain -- Username: lylepaul78 -- Password: PJones9999!! -- MCP API Key:bankless_secret_a0f899608db493c5a910d9cfad2a6c7558dba7ba8ede6b284c8293473e5a4e61

3. **LAST9_AUTH_TOKEN**: For Last9
     --Cluster Name: gmail-lylepaul78  us-east-1
     --Token Name: gmail-lylepaul78-token
     --Levitate Remote-Write Username: 861982fa-d177-4bac-932e-0c6a6cbe3856content_copy
     --Levitate Remote-Write Password: b93d11d32bd48d55e05d8ec448b2043dcontent_copy
     --Levitate Remote-Write URL: https://app-tsdb-use1.last9.io/v1/metrics/8c84b5ff51d5dc11cb42e0cbeb17009e/sender/gmail-lylepaul78/write

4. **THIRDWEB_SECRET_KEY**: For thirdweb  --  ClientID: accd6efca144e38697d1959d64a7fecb  -- Secret Key: Zy7MdHwPRbeXg5KeK2x8H8G4nOid7b14_67LrnrKKxyf0eCo7YJQq_2QIMuH83QU3uC--QKASXTiRpxXaTymgA

5. **GEMINI_API_KEY**: For Vibe Check and GemSuite -- AIzaSyBEOiFW34jKVrvfHx8J4JEBAcB4_KPzEGA

## Server Capabilities

### GitHub MCP Server
- Create or update files in GitHub repositories
- Search repositories
- Create repositories
- Get file contents
- Push multiple files
- Create issues and pull requests
- Fork repositories
- Create branches
- List commits, issues, and pull requests

### Context7 MCP Server
- Get up-to-date documentation for libraries
- Resolve library IDs
- Fetch library documentation

### MCP Compass
- Discover and recommend other MCP servers

### Setup Helper
- Set up AI assistant environments with a Memory Bank system
- Generate templates for project documentation
- Analyze project summaries

### Brave Search
- Perform web searches
- Find information from across the internet
- Research topics and gather data

### Memory
- Store and retrieve knowledge in a graph structure
- Create entities and relationships
- Add observations to entities
- Delete entities, observations, and relations
- Search for nodes in the knowledge graph

### Filesystem
- Access files on your system
- List directories and read files
- Manage your local filesystem

### Serena
- Powerful coding agent toolkit with semantic code understanding
- Navigate and edit code at the symbol level
- Execute shell commands and manage project memories

### Bankless Onchain
- Read smart contract state
- Get proxy addresses
- Get contract ABIs and source code
- Get transaction history and information
- Get token balances
- Get block information

### Last9
- Get server-side exceptions
- Get service dependency graphs
- Get logs filtered by service name and severity level
- Manage drop rules for logs

### thirdweb
- Autonomous onchain execution
- Blockchain data analysis
- Contract deployments and interactions
- Decentralized storage capabilities

### Vibe Check
- Pattern interrupt mechanism that breaks tunnel vision
- Meta-thinking anchor point that recalibrates complex workflows
- Self-improving feedback loop that builds pattern recognition

### GemSuite
- Information retrieval with search integration
- Complex reasoning with step-by-step analysis
- Fast, efficient content processing
- Intelligent file analysis with auto-model selection