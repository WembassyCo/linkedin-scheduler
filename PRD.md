# Product Requirements Document (PRD)
## LinkedIn Content Scheduler

### Goal
Build a Dockerized service that automatically schedules and publishes text posts to LinkedIn using the official LinkedIn API, avoiding browser automation which violates LinkedIn's terms of service.

### Inputs
| Input | Type | Description |
|-------|------|-------------|
| `content` | string | The text content to post (max 3000 chars) |
| `schedule_time` | ISO8601 datetime | When to publish the post |
| `visibility` | enum | "PUBLIC" or "CONNECTIONS" |
| `recurring` | boolean | Whether this is a recurring post |
| `recurrence_pattern` | string | "daily" or "weekly" (if recurring=true) |
| `LI_CLIENT_ID` | env var | LinkedIn OAuth Client ID |
| `LI_CLIENT_SECRET` | env var | LinkedIn OAuth Client Secret |
| `LI_ACCESS_TOKEN` | env var | LinkedIn OAuth Access Token |

### Outputs
| Output | Type | Description |
|--------|------|-------------|
| `post_id` | string | LinkedIn post URN upon successful publish |
| `status` | string | "scheduled", "published", "failed" |
| `error_message` | string | Error details if posting failed |
| `scheduled_posts` | JSON array | List of all scheduled posts |

### API Endpoints
1. `POST /api/v1/schedule` - Schedule a new post
2. `GET /api/v1/scheduled` - List all scheduled posts
3. `DELETE /api/v1/scheduled/{id}` - Cancel a scheduled post
4. `GET /health` - Health check endpoint

### Acceptance Criteria
- [ ] Docker image builds successfully
- [ ] Service starts and passes health check
- [ ] Can schedule a post via POST /api/v1/schedule
- [ ] Can list scheduled posts via GET /api/v1/scheduled
- [ ] Can cancel a scheduled post via DELETE
- [ ] Posts are published at the scheduled time
- [ ] Recurring posts work (daily/weekly)
- [ ] Logs are output to stdout with timestamps
- [ ] Failed posts are retried 3 times before marking failed
- [ ] README documents all endpoints and configuration
- [ ] docker-compose.yml works with single `docker-compose up`
