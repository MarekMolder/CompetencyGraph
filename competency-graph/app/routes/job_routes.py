from flask import Blueprint, request, jsonify, render_template
from logic.job_utils import load_jobs, save_jobs

jobs_bp = Blueprint("jobs", __name__)

@jobs_bp.route("/ametikohad")
def job_list():
    """
    Display a list of all saved job entries.
    """
    return render_template("ametikohad.html", jobs=load_jobs())

@jobs_bp.route("/create_job", methods=["POST"])
def create_job():
    """
    Create a new job entry.

    Request JSON:
        {
            "name": "Job Title",
            "skills": ["skill1", "skill2"]
        }

    Returns:
        JSON: { "success": true }
    """
    jobs = load_jobs()
    jobs.append(request.json)
    save_jobs(jobs)
    return jsonify(success=True)

@jobs_bp.route("/edit_job", methods=["POST"])
def edit_job():
    """
    Edit an existing job entry by index.

    Request JSON:
        {
            "index": 0,
             "job": {
                  "name": "Updated Job Title",
                  "skills": ["newSkill"]
              }
        }

     Returns:
        JSON: { "success": true } on success
               { "success": false, "error": "Invalid index" } on failure
    """
    index = request.json.get("index")
    updated = request.json.get("job")
    jobs = load_jobs()
    if 0 <= index < len(jobs):
        jobs[index] = updated
        save_jobs(jobs)
        return jsonify(success=True)
    return jsonify(success=False, error="Invalid index")

@jobs_bp.route("/delete_job", methods=["POST"])
def delete_job():
    """
    Delete a job entry by index.

    Request JSON:
        {
            "index": 2
        }

    Returns:
        JSON: { "success": true } on success
               { "success": false, "error": "Invalid index" } on failure
    """
    index = request.json.get("index")
    jobs = load_jobs()
    if 0 <= index < len(jobs):
        del jobs[index]
        save_jobs(jobs)
        return jsonify(success=True)
    return jsonify(success=False, error="Invalid index")