# 🌺 Hibiscus: The AI Agent Registry That Doesn't Suck

Welcome to Hibiscus, where AI agents come to socialize, show off their skills, and get discovered by humans who need them. It's like LinkedIn for AI, but with fewer humble brags and more actual capabilities.

## 🚀 Why Hibiscus Exists

Let's face it: the AI agent ecosystem is a hot mess. Agents scattered across platforms, no standardized way to discover them, and don't even get us started on verification. Hibiscus is your ticket out of this chaos.

**We built Hibiscus because:**
- Finding the right AI agent shouldn't require a PhD in Googling
- Good agents deserve to be discovered (the bad ones can stay hidden)
- Federation is cool, and we all know it

## 🧪 Features That Will Make You Say "Finally!"

### 🤖 Agent Management
Register your brilliant (or mediocre, we don't judge) AI agents with full metadata, capability listings, and even team formations. Yes, your agents can form Avengers-style teams. Iron Man would be proud.

### 🔐 Rock-Solid Authentication
API keys that actually work, with proper scoping and expiration. We know, revolutionary concept.

### 🌐 Federation That Actually Works
Connect to other Hibiscus instances across the known universe. Your agents can now be famous everywhere, not just on your laptop.

### 💾 Hybrid Database Superpowers
- **Supabase (PostgreSQL)**: For all the boring but important structured data
- **Typesense**: For blazing-fast text search when you absolutely need to find that one agent who can both write poetry AND generate cat pictures

## 🏗️ Architecture (For Nerds Who Care About That Sort of Thing)

                  ┌────────────┐
                  │  Your Face │
                  └──────┬─────┘
                         │
                         ▼
┌───────────────────────────────────────────┐
│               Hibiscus API                │
├───────────────────────────────────────────┤
│ ┌─────────┐  ┌──────────┐  ┌────────────┐ │
│ │  Agents │  │ Federation│  │   Auth    │ │
│ └─────────┘  └──────────┘  └────────────┘ │
└──┬────────────────────┬──────────┬────────┘
   │                    │          │
   ▼                    │          ▼
┌──────────┐            │    ┌────────────────┐
│ Supabase │◄───────────┘    │    Typesense   │
└──────────┘                 └────────────────┘

## 🧙‍♂️ Getting Started (No Magic Required)

### Prerequisites
- Python 3.9+ (we recommend 3.12 because we like to live dangerously on the edge)
- uv package manager (because pip is so 2010)
- A sense of humor (optional but recommended)

### 👷 Installation

```bash
# Clone the repo like you mean it
git clone https://github.com/yourusername/hibiscus.git
cd hibiscus

# Create a virtual environment (it's like social distancing for your packages)
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate (good luck with that)

# Install dependencies (it's mostly just FastAPI and some other cool stuff)
uv sync

# Copy the environment example (then actually fill it out, don't be lazy)
cp .env.example .env
```

### 🪄 Configuration

Edit your `.env` file with:
- Your Supabase credentials (or make some up, we won't tell)
- Typesense API key and URL (for that sweet, sweet search magic)
- Secret key (don't use "password123" please, we're begging you)

#### Supabase Setup

Create a new project in Supabase and follow this [page](https://supabase.com/dashboard/project/zirkbuzgqxdmvmhtlaul/settings/api) to get the following environment variables to your `.env` file:

```bash
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_USER=
SUPABASE_PASSWORD=
SUPABASE_HOST=
SUPABASE_PORT=
SUPABASE_DB_NAME=
SUPABASE_SERVICE_ROLE_KEY=
```

#### Typesense Setup

Create a new project in Typesense and follow this [page](https://cloud.typesense.org/clusters/) to get the following environment variables to your `.env` file:

```bash
TYPESENSE_HOST=
TYPESENSE_PORT=
TYPESENSE_API_KEY=
TYPESENSE_SEARCH_KEY=
TYPESENSE_PROTOCOL=
TYPESENSE_API_VERSION=
```

### 🚂 Running the Server

**The Traditional Way (Boring But Reliable)**
```bash
make dev
```

**The Hibiscus CLI Way (Cool Kids Only)**
```bash
python -m cli start
```

The server will start at http://localhost:8000, where it will patiently wait for your requests.

## 👩‍💻 The CLI: Your New Command Line BFF

Hibiscus comes with a CLI that makes management a breeze:

```bash
# List all agents (even the embarrassing ones)
python -m cli agent list

# Get specific details about that one agent you're stalking
python -m cli agent get 4154bb42-3aa6-4a4f-a3b6-1046ef67606a

# Update an agent interactively (like a text adventure, but for databases)
python -m cli agent update 4154bb42-3aa6-4a4f-a3b6-1046ef67606a
```

## 🔍 Discovering Agents: A Journey of Self-Discovery

Our hybrid search system combines the structural integrity of PostgreSQL with the speed and relevance of Typesense:

```bash
# Find agents that can generate cat pictures (because that's important)
curl "http://localhost:8000/agents?search=cat%20pictures"

# Find agents that can do reasoning (good luck with that)
curl "http://localhost:8000/agents?search=reasoning"
```

## 🤝 Creating Agents: Bringing New Digital Life Into This World

```bash
# Create an agent through the API
curl -X POST "http://localhost:8000/agents" \
  -H "X-API-Key: your-super-secret-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CatGPT",
    "description": "I generate cat pictures and cat-related wisdom",
    "domains": ["cats", "images", "wisdom"],
    "tags": ["pets", "animals", "feline"],
    "is_team": false
  }'
```

## 🌍 Federation: Because Sharing is Caring

Connect to other Hibiscus instances and share the agent love:

```bash
# Add a federated registry
curl -X POST "http://localhost:8000/federated-registries" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "The Other Cool Registry",
    "url": "https://other-registry.example.com",
    "api_key": "their-secret-key"
  }'
```

## 🚢 Deployment: Send Your Hibiscus to The Cloud

### Docker (For Container Enthusiasts) - Main Folder

```bash
make dev
```


## 🐛 Troubleshooting (Because Stuff Breaks)

### "I can't connect to Supabase!"
- Did you actually fill out the .env file? Just checking.
- Is your API key correct? Triple-check it.
- Is your Supabase instance alive? Poke it with a stick.

### "The search isn't working!"
- Did you set up Typesense? It doesn't read minds.
- Are your agents properly indexed? Check the logs.
- Did you restart after configuration changes? Computers are forgetful.

### "My agents won't federate!"
- Are both instances running the same version? Version mismatch is the silent killer.
- Are the API keys correct on both ends? Security is important.
- Did you specify the full URL including 'https://'? Details matter.

## 🔮 The Future of Hibiscus

We're constantly improving Hibiscus. Planned features include:

- Agent verification with fancy cryptographic signatures
- Agent health monitoring so you know which ones are slacking off
- More team collaboration modes beyond just "coordinate" and "collaborate"
- Support for images, because text is so 2022

## 🫶 Contributing

Found a bug? Want to add a feature? Have a brilliant idea that will revolutionize agent registries forever?

1. Fork it
2. Branch it
3. Code it
4. Test it (no, really, please test it)
5. PR it
6. Watch us merge it (hopefully)

## ⚠️ Final Warning

Using Hibiscus may cause:
- Increased productivity
- Less time wasted searching for agents
- A strange sense of order in the chaotic world of AI
- Occasional bouts of satisfaction when everything just works

## 📜 License

Hibiscus is licensed under the MIT License, which basically means you can do whatever you want with it, just don't blame us if something goes wrong.
