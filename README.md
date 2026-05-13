# VectorMind Backend

VectorMind is an advanced backend application integrating RAG (Retrieval-Augmented Generation) capabilities, hybrid search, and local LLM inference.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/OpenSearch-2.19-orange.svg" alt="OpenSearch">
  <img src="https://img.shields.io/badge/Docker-Compose-blue.svg" alt="Docker">
</p>

## 🚀 Quick Start

### **📋 Prerequisites**
- **Docker Desktop** (with Docker Compose)  
- **Python 3.12+**
- **UV Package Manager** ([Install Guide](https://docs.astral.sh/uv/getting-started/installation/))
- **8GB+ RAM** and **20GB+ free disk space**

### **⚡ Get Started**

```bash
# 1. Setup Environment
# Copy .env.example to .env and configure variables
cp .env.example .env

# 2. Install dependencies
uv sync

# 3. Start all services
docker compose up --build -d

# 4. Verify everything works
curl http://localhost:8000/health
```

### **📊 Access Your Services**

| Service | URL | Purpose |
|---------|-----|---------|
| **API Documentation** | http://localhost:8000/docs | Interactive API testing |
| **Airflow Dashboard** | http://localhost:8080 | Workflow management |
| **OpenSearch Dashboards** | http://localhost:5601 | Hybrid search engine UI |

#### **NOTE**: Default Airflow credentials are **username**: `admin`, **password**: Check container logs or simple_auth file.

---

## 🛠️ Technology Stack

| Service | Purpose | Status |
|---------|---------|--------|
| **FastAPI** | REST API with automatic docs | ✅ Ready |
| **PostgreSQL 16** | Core metadata storage | ✅ Ready |
| **OpenSearch 2.19** | Hybrid search engine | ✅ Ready |
| **Apache Airflow 2.10** | Workflow automation | ✅ Ready |
| **Ollama 0.11** | Local LLM serving | ✅ Ready |

**Development Tools:** UV, Ruff, MyPy, Pytest, Docker Compose

---

## 🔧 Essential Commands

### **Using the Makefile** (Recommended)
```bash
# View all available commands
make help

# Quick workflow
make start         # Start all services
make health        # Check all services health
make test          # Run tests
make stop          # Stop services
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.
