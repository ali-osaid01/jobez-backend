# JobEZ — Auth API Documentation

**Base URL:** `http://localhost:8000/api/v1`

All requests/responses use `Content-Type: application/json`.

---

## 1. Sign Up

**`POST /auth/signup`** — Creates a new user account.

**Auth:** None (public)

### Request Body

```json
{
  "email": "ahmed@example.com",
  "password": "securepass123",
  "phone": "03001234567",
  "role": "job-seeker",
  "name": "Ahmed Hassan"
}
```

| Field      | Type   | Required | Rules                                |
|------------|--------|----------|--------------------------------------|
| `email`    | string | Yes      | Valid email format, must be unique    |
| `password` | string | Yes      | Minimum 6 characters                 |
| `phone`    | string | Yes      | Minimum 10 characters                |
| `role`     | string | Yes      | `"job-seeker"` or `"employer"`       |
| `name`     | string | Yes      | Cannot be empty                      |

### Success Response — `201 Created`

```json
{
  "data": {
    "user": {
      "id": "4d948bb1-5041-4ff4-a7f5-c5a0985075b1",
      "email": "ahmed@example.com",
      "name": "Ahmed Hassan",
      "phone": "03001234567",
      "role": "job-seeker",
      "onboardingComplete": false
    },
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "refreshToken": "eyJhbGciOiJIUzI1NiIs..."
  },
  "message": "Success"
}
```

### Error Responses

| Status | Code               | When                          |
|--------|--------------------|-------------------------------|
| 409    | `CONFLICT`         | Email already registered      |
| 422    | `VALIDATION_ERROR` | Missing/invalid fields        |

```json
{
  "error": {
    "code": "CONFLICT",
    "message": "A user with this email already exists",
    "details": null
  }
}
```

---

## 2. Login

**`POST /auth/login`** — Authenticates user and returns tokens.

**Auth:** None (public)

### Request Body

```json
{
  "email": "ahmed@example.com",
  "password": "securepass123"
}
```

| Field      | Type   | Required |
|------------|--------|----------|
| `email`    | string | Yes      |
| `password` | string | Yes      |

### Success Response — `200 OK`

```json
{
  "data": {
    "user": {
      "id": "4d948bb1-5041-4ff4-a7f5-c5a0985075b1",
      "email": "ahmed@example.com",
      "name": "Ahmed Hassan",
      "phone": "03001234567",
      "role": "job-seeker",
      "onboardingComplete": false
    },
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "refreshToken": "eyJhbGciOiJIUzI1NiIs..."
  },
  "message": "Success"
}
```

### Frontend Redirect Logic

Use `onboardingComplete` and `role` to decide where to redirect:

```typescript
if (!user.onboardingComplete) {
  router.push("/onboarding");
} else if (user.role === "job-seeker") {
  router.push("/job-seeker/dashboard");
} else {
  router.push("/employer/dashboard");
}
```

### Error Responses

| Status | Code           | When                          |
|--------|----------------|-------------------------------|
| 401    | `UNAUTHORIZED` | Wrong password                |
| 404    | `NOT_FOUND`    | Email not registered          |

---

## 3. Refresh Token

**`POST /auth/refresh`** — Gets a new access token using a refresh token.

**Auth:** None (uses refresh token in body)

### Request Body

```json
{
  "refreshToken": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Success Response — `200 OK`

```json
{
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": "4d948bb1-5041-4ff4-a7f5-c5a0985075b1",
      "email": "ahmed@example.com",
      "name": "Ahmed Hassan",
      "phone": "03001234567",
      "role": "job-seeker",
      "onboardingComplete": false
    }
  },
  "message": "Success"
}
```

### Frontend Usage (RTK Query `baseQueryWithReauth`)

```typescript
// When any API call returns 401:
// 1. Call POST /auth/refresh with the stored refreshToken
// 2. Store the new token
// 3. Retry the original request with the new token
```

### Error Responses

| Status | Code           | When                             |
|--------|----------------|----------------------------------|
| 401    | `UNAUTHORIZED` | Invalid or expired refresh token |

---

## 4. Logout

**`POST /auth/logout`** — Invalidates the refresh token server-side.

**Auth:** Bearer token required

### Headers

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Request Body

None

### Success Response — `200 OK`

```json
{
  "message": "Logged out"
}
```

### Error Responses

| Status | Code           | When                              |
|--------|----------------|-----------------------------------|
| 401    | `UNAUTHORIZED` | Missing or invalid access token   |

---

## Token Details

| Token          | Lifetime   | Sent As                    | Storage Recommendation         |
|----------------|------------|----------------------------|--------------------------------|
| Access Token   | 30 minutes | `Authorization: Bearer <token>` | Memory (Redux/Context)    |
| Refresh Token  | 7 days     | Request body to `/auth/refresh` | `httpOnly` cookie or localStorage |

### JWT Payload (Access Token)

```json
{
  "sub": "4d948bb1-5041-4ff4-a7f5-c5a0985075b1",
  "role": "job-seeker",
  "exp": 1773466550,
  "type": "access"
}
```

---

## Common Error Format

All errors follow this structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": null
  }
}
```

| HTTP | Code               | When                             |
|------|--------------------|----------------------------------|
| 401  | `UNAUTHORIZED`     | Missing/invalid/expired token    |
| 409  | `CONFLICT`         | Duplicate resource (e.g. email)  |
| 422  | `VALIDATION_ERROR` | Invalid input (field-level)      |
| 429  | `RATE_LIMITED`      | Too many requests (60/min)       |
| 500  | `INTERNAL_ERROR`   | Server error                     |

### Validation Error Example (422)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "email": "Value is not a valid email address",
      "password": "String should have at least 6 characters"
    }
  }
}
```
