# LinkedIn Content Scheduler

A Dockerized service for scheduling and publishing posts to LinkedIn using the official LinkedIn API.

## Features

- Schedule posts for future publication
- Recurring posts (daily/weekly)
- REST API for management
- SQLite database for persistence
- Automatic retry on failure (3 attempts)
- Health check endpoint

## API Endpoints

### Health Check
```bash
GET /health
```

### Schedule a Post
```bash
POST /api/v1/schedule
Content-Type: application/json

{
  "content": "Your post content here",
  "schedule_time": "2026-02-26T10:00:00",
  "visibility": "PUBLIC",
  "recurring": false,
  "recurrence_pattern": null
}
```

### List Scheduled Posts
```bash
GET /api/v1/scheduled
```

### Cancel a Scheduled Post
```bash
DELETE /api/v1/scheduled/{id}
```

## Configuration

Set these environment variables in a `.env` file:

```
LI_CLIENT_ID=your_linkedin_client_id
LI_CLIENT_SECRET=your_linkedin_client_secret
LI_ACCESS_TOKEN=your_linkedin_access_token
LI_PERSON_URN=your_linkedin_person_urn
```

## Quick Start

1. Clone the repository
2. Create `.env` file with your LinkedIn credentials
3. Run: `docker-compose up -d`
4. Access API at `http://localhost:8000`

## Docker Commands

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild
docker-compose up -d --build --force-recreate
```

## License

MIT