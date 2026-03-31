# JobEZ — Jobs API Documentation

**Base URL:** `http://localhost:8000/api/v1`

---

## 1. List Jobs (Browse/Search)

**`GET /jobs`**

**Auth:** Bearer token
**Role:** Any authenticated user (job-seeker or employer)

### Query Parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | `1` | Page number (min 1) |
| `limit` | int | `20` | Items per page (1-100) |
| `search` | string | — | Search in title, company, location |
| `locationType` | string | — | Filter: `"Remote"`, `"On-site"`, `"Hybrid"` |
| `type` | string | — | Filter: `"Full-time"`, `"Part-time"`, `"Contract"`, `"Internship"` |
| `experienceLevel` | string | — | Filter: `"Entry"`, `"Mid"`, `"Senior"`, `"Lead"` |
| `employerId` | UUID | — | Filter by employer (for "my posted jobs") |
| `status` | string | `"active"` | `"active"` or `"closed"` |
| `sortBy` | string | `"postedDate"` | `"postedDate"` or `"salary"` |
| `sortOrder` | string | `"desc"` | `"asc"` or `"desc"` |

### Example Request

```typescript
// Job seeker browsing jobs
const response = await fetch("/api/v1/jobs?page=1&limit=20&search=react&locationType=Remote", {
  headers: { Authorization: `Bearer ${token}` },
});

// Employer viewing their own posted jobs
const response = await fetch(`/api/v1/jobs?employerId=${user.id}`, {
  headers: { Authorization: `Bearer ${token}` },
});
```

### Success Response — `200 OK`

```json
{
  "data": [
    {
      "id": "uuid-here",
      "title": "Senior React Developer",
      "company": "Systems Limited",
      "location": "Lahore, Pakistan",
      "locationType": "Hybrid",
      "salary": "200,000 - 350,000 PKR",
      "type": "Full-time",
      "experienceLevel": "Senior",
      "description": "We are looking for a senior React developer...",
      "requirements": ["5+ years React experience", "TypeScript", "Redux"],
      "responsibilities": ["Lead frontend development", "Code reviews"],
      "benefits": ["Health insurance", "Remote flexibility"],
      "postedDate": "2026-03-15T10:00:00+00:00",
      "applicationDeadline": "2026-04-15",
      "employerId": "uuid-here",
      "matchScore": null,
      "applicantsCount": 12,
      "status": "active",
      "createdAt": "2026-03-15T10:00:00+00:00",
      "updatedAt": "2026-03-15T10:00:00+00:00"
    }
  ],
  "total": 45,
  "page": 1,
  "limit": 20,
  "total_pages": 3
}
```

---

## 2. Get Single Job

**`GET /jobs/:id`**

**Auth:** Bearer token
**Role:** Any authenticated user

### Success Response — `200 OK`

```json
{
  "data": {
    "id": "uuid-here",
    "title": "Senior React Developer",
    "company": "Systems Limited",
    "location": "Lahore, Pakistan",
    "locationType": "Hybrid",
    "salary": "200,000 - 350,000 PKR",
    "type": "Full-time",
    "experienceLevel": "Senior",
    "description": "We are looking for a senior React developer...",
    "requirements": ["5+ years React experience", "TypeScript", "Redux"],
    "responsibilities": ["Lead frontend development", "Code reviews"],
    "benefits": ["Health insurance", "Remote flexibility"],
    "postedDate": "2026-03-15T10:00:00+00:00",
    "applicationDeadline": "2026-04-15",
    "employerId": "uuid-here",
    "matchScore": null,
    "applicantsCount": 12,
    "status": "active",
    "createdAt": "2026-03-15T10:00:00+00:00",
    "updatedAt": "2026-03-15T10:00:00+00:00"
  }
}
```

### Errors

| Status | Code | When |
|--------|------|------|
| 404 | `NOT_FOUND` | Job doesn't exist |

---

## 3. Create Job (Post a Job)

**`POST /jobs`**

**Auth:** Bearer token
**Role:** employer only

### Request

```json
{
  "title": "Senior React Developer",
  "company": "Systems Limited",
  "location": "Lahore, Pakistan",
  "locationType": "Hybrid",
  "salary": "200,000 - 350,000 PKR",
  "type": "Full-time",
  "experienceLevel": "Senior",
  "description": "We are looking for a senior React developer to join our team...",
  "requirements": ["5+ years React experience", "TypeScript proficiency", "Redux/state management"],
  "responsibilities": ["Lead frontend development", "Conduct code reviews", "Mentor junior developers"],
  "benefits": ["Health insurance", "Remote flexibility", "Annual bonus"],
  "applicationDeadline": "2026-04-15"
}
```

### Field Value Mappings

**`locationType`** — must be one of:
| Value | Meaning |
|-------|---------|
| `"Remote"` | Fully remote |
| `"On-site"` | On-site only |
| `"Hybrid"` | Hybrid |

**`type`** — must be one of:
| Value | Meaning |
|-------|---------|
| `"Full-time"` | Full-time position |
| `"Part-time"` | Part-time position |
| `"Contract"` | Contract work |
| `"Internship"` | Internship |

**`experienceLevel`** — must be one of:
| Value | Meaning |
|-------|---------|
| `"Entry"` | Entry level |
| `"Mid"` | Mid level |
| `"Senior"` | Senior level |
| `"Lead"` | Lead level |

### Required Fields

All fields except `requirements`, `responsibilities`, `benefits`, and `applicationDeadline` are **required**.

### Success Response — `201 Created`

```json
{
  "data": {
    "id": "uuid-here",
    "title": "Senior React Developer",
    "company": "Systems Limited",
    "location": "Lahore, Pakistan",
    "locationType": "Hybrid",
    "salary": "200,000 - 350,000 PKR",
    "type": "Full-time",
    "experienceLevel": "Senior",
    "description": "We are looking for a senior React developer...",
    "requirements": ["5+ years React experience", "TypeScript proficiency"],
    "responsibilities": ["Lead frontend development", "Conduct code reviews"],
    "benefits": ["Health insurance", "Remote flexibility"],
    "postedDate": "2026-03-15T10:00:00+00:00",
    "applicationDeadline": "2026-04-15",
    "employerId": "uuid-here",
    "matchScore": null,
    "applicantsCount": 0,
    "status": "active",
    "createdAt": "2026-03-15T10:00:00+00:00",
    "updatedAt": "2026-03-15T10:00:00+00:00"
  }
}
```

### Errors

| Status | Code | When |
|--------|------|------|
| 401 | `UNAUTHORIZED` | Missing/invalid token |
| 403 | `FORBIDDEN` | Not an employer |
| 422 | `VALIDATION_ERROR` | Missing required fields or invalid enum values |

---

## 4. Update Job

**`PATCH /jobs/:id`**

**Auth:** Bearer token
**Role:** employer (must own the job)

### Request

All fields are optional — only send what changed.

```json
{
  "title": "Updated Job Title",
  "salary": "250,000 - 400,000 PKR",
  "status": "closed"
}
```

### Success Response — `200 OK`

Same shape as Create response.

### Errors

| Status | Code | When |
|--------|------|------|
| 403 | `FORBIDDEN` | Not the job owner |
| 404 | `NOT_FOUND` | Job doesn't exist |

---

## 5. Delete (Close) Job

**`DELETE /jobs/:id`**

**Auth:** Bearer token
**Role:** employer (must own the job)

This doesn't actually delete the job — it sets `status` to `"closed"`.

### Success Response — `200 OK`

```json
{
  "message": "Job closed"
}
```

### Errors

| Status | Code | When |
|--------|------|------|
| 403 | `FORBIDDEN` | Not the job owner |
| 404 | `NOT_FOUND` | Job doesn't exist |

---

## 6. Get Recommended Jobs

**`GET /jobs/recommended`**

**Auth:** Bearer token
**Role:** job-seeker only

Returns up to 10 recommended jobs (currently returns newest active jobs; AI scoring coming soon).

### Success Response — `200 OK`

```json
{
  "data": [
    {
      "id": "uuid-here",
      "title": "Senior React Developer",
      "company": "Systems Limited",
      ...
    }
  ]
}
```

---

## 7. Toggle Bookmark

**`POST /jobs/:id/bookmark`**

**Auth:** Bearer token
**Role:** job-seeker only

Toggles a bookmark on/off. If already bookmarked, removes it. If not bookmarked, adds it.

### Success Response — `200 OK`

```json
{
  "data": {
    "bookmarked": true
  }
}
```

`bookmarked: true` = just bookmarked, `bookmarked: false` = just removed.

### Errors

| Status | Code | When |
|--------|------|------|
| 404 | `NOT_FOUND` | Job doesn't exist |

---

## Endpoints Summary

| Method | Endpoint | Role | Purpose |
|--------|----------|------|---------|
| `GET` | `/jobs` | Any | Browse/search jobs with filters & pagination |
| `GET` | `/jobs/recommended` | job-seeker | Get AI-recommended jobs |
| `GET` | `/jobs/:id` | Any | Get single job details |
| `POST` | `/jobs` | employer | Post a new job |
| `PATCH` | `/jobs/:id` | employer (owner) | Update job details |
| `DELETE` | `/jobs/:id` | employer (owner) | Close a job |
| `POST` | `/jobs/:id/bookmark` | job-seeker | Toggle bookmark on/off |

---

## Frontend Usage Examples

### Employer — Post a Job

```typescript
const response = await fetch("/api/v1/jobs", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    title: "Senior React Developer",
    company: "Systems Limited",
    location: "Lahore, Pakistan",
    locationType: "Hybrid",
    salary: "200,000 - 350,000 PKR",
    type: "Full-time",
    experienceLevel: "Senior",
    description: "We are looking for...",
    requirements: ["React", "TypeScript"],
    responsibilities: ["Lead frontend"],
    benefits: ["Health insurance"],
    applicationDeadline: "2026-04-15",
  }),
});
```

### Employer — Get My Posted Jobs

```typescript
const response = await fetch(`/api/v1/jobs?employerId=${currentUser.id}`, {
  headers: { Authorization: `Bearer ${token}` },
});
```

### Job Seeker — Browse & Filter Jobs

```typescript
const response = await fetch(
  "/api/v1/jobs?page=1&limit=20&search=react&locationType=Remote&type=Full-time&experienceLevel=Senior",
  { headers: { Authorization: `Bearer ${token}` } }
);
```

### Job Seeker — Bookmark a Job

```typescript
const response = await fetch(`/api/v1/jobs/${jobId}/bookmark`, {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
});
const { data } = await response.json();
// data.bookmarked === true means bookmarked, false means removed
```
