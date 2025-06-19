# 📘 API Documentation – Skills Graph Application

This document outlines the API endpoints provided by the **Skills Graph Flask application**.  
These endpoints allow users to search for skills, retrieve graph data, and manage job entries.

---

## 🔗 `/graph`

**Method**: `GET`  
**Description**: Returns the graph structure (nodes and edges) for a given skill or for all skills.

**Query Parameters**:
- `skill` (string, optional): The name of the skill to search for (case-insensitive).
- `limit_recursion` (boolean, optional): Whether to limit the recursion depth. Default: `false`.
- `max_depth` (integer, optional): Maximum recursion depth. Default: `2`.

**Responses**:
- `200 OK`
  ```json
  {
    "nodes": [...],
    "edges": [...]
  }
  ```
- `404 Not Found`: If the skill is not found.  
- `500 Internal Server Error`: If an error occurs during processing.

---

## 🔗 `/ametikohad`

**Method**: `GET`  
**Description**: Displays a list of all saved job entries.

**Response**:  
Renders the `ametikohad.html` template with the job list.

---

## 🔗 `/create_job`

**Method**: `POST`  
**Description**: Adds a new job entry to the system.

**Request Body**:
```json
{
  "name": "Job Title",
  "skills": ["skill1", "skill2"]
}
```

**Responses**:
- `200 OK`
  ```json
  { "success": true }
  ```
- On failure (e.g. invalid input):
  ```json
  { "success": false }
  ```

---

## 🔗 `/edit_job`

**Method**: `POST`  
**Description**: Updates an existing job based on its index.

**Request Body**:
```json
{
  "index": 0,
  "job": {
    "name": "Updated Job Title",
    "skills": ["newSkill"]
  }
}
```

**Responses**:
- `200 OK`
  ```json
  { "success": true }
  ```
- `400 Bad Request`
  ```json
  { "success": false, "error": "Invalid index" }
  ```

---

## 🔗 `/delete_job`

**Method**: `POST`  
**Description**: Deletes a job entry by its index.

**Request Body**:
```json
{
  "index": 2
}
```

**Responses**:
- `200 OK`
  ```json
  { "success": true }
  ```
- `400 Bad Request`
  ```json
  { "success": false, "error": "Invalid index" }
  ```

---

## 🔗 `/`

**Method**: `GET`  
**Description**: Loads the homepage interface for searching and visualizing skills.

**Response**:  
Renders `index.html` – the main skill search and graph interface.

---

## 📝 Notes

- All endpoints that modify job data (`/create_job`, `/edit_job`, `/delete_job`) interact with a JSON file located at the root of the project: `ametikohad.json`.
- The skill graph data is parsed dynamically from RDF sources on [oppekava.edu.ee](https://oppekava.edu.ee).

---

## 👤 Author

**Marek Mölder**
