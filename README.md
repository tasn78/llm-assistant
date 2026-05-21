**llm-assistant**

A Flask-based document summarization and workflow automation service using a locally-hosted HuggingFace transformer (distilbart-cnn-12-6) integrated with Google Calendar and Gmail via OAuth2.

**Features**
- PDF and text document ingestion (PyMuPDF)
- Token-aware chunking for long documents (1,000-token windows via AutoTokenizer)
- NLP-based action item extraction with dateparser
- Automatic Google Calendar event creation from extracted dates
- Gmail send integration
- SQLite audit logging with admin dashboard (HTTP Basic Auth)
- Optional TLS support

**Deployment History**

*Version 1 — GCP Cloud Run:* Initially deployed as a containerized service on Google Cloud Run, provisioned with Terraform (VPC, Cloud Storage, Artifact Registry, service account), with a GitHub Actions CI/CD pipeline running on push to main.

*Version 2 — Self-Hosted Server (Course Deployment):* Migrated to a university-managed Linux server as part of CS coursework in cloud computing, managing Docker deployment, environment configuration, volume persistence, and service monitoring directly on the host.

**Running with Docker**
```
docker build -t llm-assistant .
docker run -p 443:443 -v $(pwd)/data:/data llm-assistant
```
