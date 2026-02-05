# egap-mcp-hub

MCP Hub Service for EGAP - Phase 0: Hello World deployment verification.

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload --port 8080

# Test endpoint
curl http://localhost:8080/
```

### GCP Deployment

**Prerequisites:** Enable required APIs in project `gls-training-486405`:
```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com --project=gls-training-486405
```

**One-time setup:** Create Artifact Registry repository:
```bash
gcloud artifacts repositories create egap-mcp-hub \
  --repository-format=docker \
  --location=us-central1 \
  --project=gls-training-486405
```

**Grant Cloud Build permissions:**
```bash
# Get project number
PROJECT_NUMBER=$(gcloud projects describe gls-training-486405 --format='value(projectNumber)')

# Grant Cloud Run Admin role
gcloud projects add-iam-policy-binding gls-training-486405 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

# Grant Service Account User role
gcloud projects add-iam-policy-binding gls-training-486405 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

**Deploy:**
```bash
gcloud builds submit --config=cloudbuild.yaml --project=gls-training-486405
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Hello World response |
| `GET /health` | Health check for Cloud Run |