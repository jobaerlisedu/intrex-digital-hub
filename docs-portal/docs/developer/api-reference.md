# API Reference

This document outlines the API endpoints exposed by the Intrex ERP platform, including the public JSON interfaces used by the external website and guidelines for internal database queries.

---

## 1. Public JSON API Endpoints

These endpoints handle public submissions from the main website (e.g. course registrations and contact inquiries). They are implemented using Django views that store data in MySQL via Django ORM.

### A. Course Registration API
Submits a student registration application directly to the training admissions pipeline.

*   **Endpoint URL**: `/courses/register/`
*   **HTTP Method**: `POST`
*   **Content-Type**: `application/x-www-form-urlencoded` or `multipart/form-data`
*   **Authentication**: None (Public Endpoint)

#### Request Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `fullName` | String | **Yes** | Candidate's legal name. |
| `email` | String | **Yes** | Contact email address. |
| `phone` | String | **Yes** | Contact phone number. |
| `course` | String | **Yes** | Course identifier/title. |
| `education` | String | No | Level of education (e.g. B.Sc. in CSE). |
| `schedule` | String | No | Preferred batch schedule (e.g. Friday/Saturday). |
| `isJobHolder`| String | No | Boolean string (`"true"` or `"false"`). |
| `companyName`| String | No | Employer company name (if employed). |
| `designation`| String | No | Current job designation (if employed). |
| `message` | String | No | Additional comments or notes. |

#### JSON Responses

##### Success (200 OK)
```json
{
  "status": "success",
  "key": "REG-874213"
}
```

##### Validation Error (400 Bad Request)
```json
{
  "status": "error",
  "message": "Missing required fields."
}
```

##### Method Not Allowed (405 Method Not Allowed)
```json
{
  "status": "error",
  "message": "Invalid request method."
}
```

##### Database Write Failure (500 Internal Server Error)
```json
{
  "status": "error",
  "message": "Database insertion failed."
}
```

---

### B. Course & General Inquiry API
Submits user questions and general training inquiries. Depending on the `source` parameter, the system route will categorise the record.

*   **Endpoint URL**: `/courses/inquire/`
*   **HTTP Method**: `POST`
*   **Content-Type**: `application/x-www-form-urlencoded`
*   **Authentication**: None (Public Endpoint)

#### Request Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `name` | String | **Yes** | Sender's name. |
| `email` | String | **Yes** | Contact email address. |
| `phone` | String | No | Contact phone number. |
| `subject` | String | No | Inquiry subject line or course code. |
| `message` | String | **Yes** | Message body. |
| `source` | String | No | Origin tracker (defaults to `"training-page"`). |

#### Routing Rules
*   **`source = 'training-page'`**: Saves directly into the `learn_online_registrations` MySQL table, returning a key prefixed with `REG-`. This links the inquiry to the admissions pipeline.
*   **`source = 'contact-page'` (or other)**: Saves into the `learn_online_inquiries` MySQL table, returning a key prefixed with `INQ-`. This links the inquiry to the general marketing sales queue.

#### JSON Responses

##### Success (200 OK - Contact Page)
```json
{
  "status": "success",
  "key": "INQ-420958"
}
```

##### Success (200 OK - Training Page)
```json
{
  "status": "success",
  "key": "REG-591042"
}
```

---

### C. Certificate Verification API
Retrieves metadata of student certificates issued by the academy to confirm validation.

*   **Endpoint URL**: `/verify-certificate/`
*   **HTTP Method**: `GET`
*   **Query Parameters**:
    *   `id` (String - Required): The certificate ID (e.g. `INTREX-CERT-CCNA-2026`).
*   **Response**: Renders the verification HTML page containing the certificate status, student metadata, issue date, and validation hash.

---

## 2. Internal Django ORM Queries

Within the backend Python views, database access is performed through Django ORM models defined in each module.

### Query Snippets

#### 1. Fetching Active Documents
```python
from training.models import Course

# Retrieve all active courses sorted by title
active_courses = Course.objects.filter(status='Active').order_by('title')
```

#### 2. Creating a Record
```python
from training.models import OnlineRegistration

registration = OnlineRegistration.objects.create(
    full_name='Jane Doe',
    email='jane@example.com'
)
```