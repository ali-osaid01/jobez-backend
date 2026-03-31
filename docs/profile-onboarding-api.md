# JobEZ — Profile & Onboarding API Documentation

**Base URL:** `http://localhost:8000/api/v1`

---

## 1. Resume Extract (Upload + AI Parse)

**`POST /profile/resume/extract`**

Uploads the resume to Cloudinary, then sends it to Gemini OCR to extract structured fields for auto-filling the onboarding form.

**Auth:** Bearer token
**Role:** job-seeker
**Content-Type:** `multipart/form-data`

### Request

FormData with `file` field (PDF, DOC, DOCX — max 5MB)

```typescript
const formData = new FormData();
formData.append("file", selectedFile);

const response = await fetch("/api/v1/profile/resume/extract", {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: formData,
});
```

### Success Response — `200 OK`

```json
{
  "data": {
    "title": "Senior Software Engineer",
    "experience": "5-10",
    "preferredRole": "software-engineering",
    "location": "Lahore, Pakistan",
    "expectedSalary": "150,000 - 250,000 PKR",
    "skills": ["React", "TypeScript", "Node.js", "Python", "AWS"],
    "bio": "Experienced software engineer with 7 years of full-stack development...",
    "education": [
      {
        "degree": "BS Computer Science",
        "institution": "LUMS",
        "year": "2017"
      }
    ],
    "workExperience": [
      {
        "title": "Senior Software Engineer",
        "company": "Systems Limited",
        "duration": "2020 - Present"
      },
      {
        "title": "Software Engineer",
        "company": "Netsol Technologies",
        "duration": "2017 - 2020"
      }
    ],
    "certifications": ["AWS Certified Solutions Architect"],
    "resumeUrl": "https://res.cloudinary.com/.../resumes/abc123.pdf"
  },
  "message": "Resume parsed successfully"
}
```

### Field Value Mappings

**`experience`** — must be one of:
| Value | Meaning |
|-------|---------|
| `"0-1"` | 0-1 years |
| `"1-3"` | 1-3 years |
| `"3-5"` | 3-5 years |
| `"5-10"` | 5-10 years |
| `"10+"` | 10+ years |

**`preferredRole`** — must be one of:
`"software-engineering"`, `"data-science"`, `"product-management"`, `"design"`, `"marketing"`, `"sales"`, `"operations"`, `"finance"`, `"hr"`, `"other"`

### Notes

- All fields are optional in the response — returns `null` for fields that couldn't be extracted
- The frontend should pre-fill the form with returned data; user can edit before submitting
- The original resume file is also uploaded and stored — `resumeUrl` is returned
- If `GEMINI_API_KEY` is not configured, returns empty/null fields with `resumeUrl` still populated

### Errors

| Status | Code | When |
|--------|------|------|
| 400 | `VALIDATION_ERROR` | Unsupported file type |
| 400 | `VALIDATION_ERROR` | File too large (>5MB) |
| 401 | `UNAUTHORIZED` | Missing/invalid token |
| 403 | `FORBIDDEN` | Not a job-seeker |

---

## 2. Resume Upload (No Parsing)

**`POST /profile/resume`**

Just uploads and stores the resume, no AI extraction.

**Auth:** Bearer token
**Role:** job-seeker
**Content-Type:** `multipart/form-data`

### Request

FormData with `file` field (PDF, DOC, DOCX — max 5MB)

### Success Response — `200 OK`

```json
{
  "data": {
    "resumeUrl": "https://res.cloudinary.com/.../resumes/abc123.pdf"
  },
  "message": "Resume uploaded successfully"
}
```

### Errors

Same as resume extract above.

---

## 3. Complete Onboarding — Job Seeker

**`PATCH /profile/me`**

**Auth:** Bearer token
**Role:** job-seeker

### Request

```json
{
  "title": "Senior Software Engineer",
  "experience": "5-10",
  "preferredRole": "software-engineering",
  "location": "Lahore, Pakistan",
  "expectedSalary": "150,000 - 250,000 PKR",
  "skills": ["React", "TypeScript", "Node.js"],
  "bio": "Experienced engineer focused on...",
  "education": [
    {
      "degree": "BS Computer Science",
      "institution": "LUMS",
      "year": "2017"
    }
  ],
  "workExperience": [
    {
      "title": "Senior Software Engineer",
      "company": "Systems Limited",
      "duration": "2020 - Present"
    }
  ],
  "certifications": ["AWS Certified Solutions Architect"],
  "resumeUrl": "https://res.cloudinary.com/.../resumes/abc123.pdf",
  "onboardingComplete": true
}
```

All fields are optional — only send what changed. The key field is `onboardingComplete: true` which marks onboarding as done.

### Success Response — `200 OK`

```json
{
  "data": {
    "id": "uuid-here",
    "userId": "uuid-here",
    "email": "ahmed@example.com",
    "name": "Ahmed Hassan",
    "phone": "03001234567",
    "role": "job-seeker",
    "onboardingComplete": true,
    "title": "Senior Software Engineer",
    "experience": "5-10",
    "preferredRole": "software-engineering",
    "location": "Lahore, Pakistan",
    "expectedSalary": "150,000 - 250,000 PKR",
    "skills": ["React", "TypeScript", "Node.js"],
    "bio": "Experienced engineer focused on...",
    "education": [
      { "degree": "BS Computer Science", "institution": "LUMS", "year": "2017" }
    ],
    "workExperience": [
      { "title": "Senior Software Engineer", "company": "Systems Limited", "duration": "2020 - Present" }
    ],
    "certifications": ["AWS Certified Solutions Architect"],
    "resumeUrl": "https://res.cloudinary.com/.../resumes/abc123.pdf",
    "company": null,
    "companySize": null,
    "industry": null,
    "website": null,
    "description": null,
    "founded": null,
    "createdAt": "2026-03-14T10:00:00+00:00",
    "updatedAt": "2026-03-14T10:05:00+00:00"
  },
  "message": "Profile updated successfully"
}
```

---

## 4. Complete Onboarding — Employer

**`PATCH /profile/me`** (same endpoint, different fields)

**Auth:** Bearer token
**Role:** employer

### Request

```json
{
  "company": "Systems Limited",
  "industry": "technology",
  "companySize": "501-1000",
  "location": "Lahore, Pakistan",
  "website": "https://systemsltd.com",
  "description": "Leading technology company...",
  "onboardingComplete": true
}
```

**`industry`** — must be one of:
`"technology"`, `"finance"`, `"healthcare"`, `"education"`, `"retail"`, `"manufacturing"`, `"other"`

**`companySize`** — must be one of:
`"1-10"`, `"11-50"`, `"51-200"`, `"201-500"`, `"501-1000"`, `"1000+"`

### Success Response — `200 OK`

```json
{
  "data": {
    "id": "uuid-here",
    "userId": "uuid-here",
    "email": "hr@systemsltd.com",
    "name": "Ali Khan",
    "phone": "03009876543",
    "role": "employer",
    "onboardingComplete": true,
    "title": null,
    "location": "Lahore, Pakistan",
    "experience": null,
    "preferredRole": null,
    "expectedSalary": null,
    "skills": null,
    "education": null,
    "workExperience": null,
    "certifications": null,
    "resumeUrl": null,
    "bio": null,
    "company": "Systems Limited",
    "companySize": "501-1000",
    "industry": "technology",
    "website": "https://systemsltd.com",
    "description": "Leading technology company...",
    "founded": null,
    "createdAt": "2026-03-14T10:00:00+00:00",
    "updatedAt": "2026-03-14T10:05:00+00:00"
  },
  "message": "Profile updated successfully"
}
```

---

## 5. Get My Profile

**`GET /profile/me`**

**Auth:** Bearer token
**Role:** Any authenticated user

Returns the same response shape as `PATCH /profile/me` above.

---

## Onboarding Flow

```
User signs up (POST /auth/signup)
  └── onboardingComplete = false → Redirect to /onboarding

Job Seeker Onboarding:
  Step 1: Upload resume
    ├── Option A: POST /profile/resume/extract → auto-fill form
    └── Option B: Skip, fill manually

  Steps 2-4: User edits/fills form fields

  Step 5: Review & submit
    └── PATCH /profile/me (all fields + onboardingComplete: true)
        └── Response has onboardingComplete: true
            └── Update Redux auth state → Redirect to /job-seeker/dashboard

Employer Onboarding:
  Step 1: Fill company info
  Step 2: Submit
    └── PATCH /profile/me (company fields + onboardingComplete: true)
        └── Redirect to /employer/dashboard
```

---

## Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/profile/resume/extract` | Upload resume + Gemini AI parse → structured JSON |
| `POST` | `/profile/resume` | Upload resume only (no parsing) |
| `PATCH` | `/profile/me` | Save onboarding data + set `onboardingComplete: true` |
| `GET` | `/profile/me` | Get current user's profile |
