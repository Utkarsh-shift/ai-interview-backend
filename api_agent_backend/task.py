import uuid
import logging
import mysql.connector
import requests
import json
from time import sleep
import random
from backend.celery import app
from decouple import config


DB_CONFIG = {
    'host': config('host'),
    'database': config('database'),
    'user': config('user'),
    'password': config('password'),
    'port': config('port')
}

API_POST_URL = config('API_POST_URL')   

@app.task(name="api_agent_backend.task.check_pending_evaluations")
def check_pending_evaluations():
    cursor = None
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True, buffered=True)
        logging.info("Checking for pending evaluations...")
        print("Checking for pending evaluations...")

        query = """
        SELECT session_id
        FROM interview_evaluations
        WHERE status = 'PENDING'
        ORDER BY id ASC
        LIMIT 1
        """
        cursor.execute(query)
        pending_session = cursor.fetchone()
        if not pending_session:
            logging.info("No pending sessions found.")
            return

        session_id = pending_session["session_id"]
        logging.info(f"Triggering evaluation for session: {session_id}")
        print(f"Triggering evaluation for session: {session_id}")

      
        status_query = "SELECT status FROM interview_evaluations WHERE session_id = %s"
        cursor.execute(status_query, (session_id,))
        session_status = cursor.fetchone()

        if session_status and session_status["status"] == "PROCESSED":
            print(f"Session {session_id} has already been processed. Skipping.")
            return

        fetch_batch_query = "SELECT batch_id FROM lipsync_openaiid_batchid WHERE openai_session_id = %s"
        cursor.execute(fetch_batch_query, (session_id,))
        batch_result = cursor.fetchone()

        if batch_result is None:
            print(f"Error: No batch_id found for session ID {session_id}.")
            return

        batch_id = batch_result["batch_id"]
        print("Batch ID: ", batch_id)

        upload_link, skills_raw, focus_skills_raw, tabswitch_count, fullscreen_exit_count, multi_person_count, cell_phone_count, server_url = get_data(session_id, batch_id)
        get_uuid = uuid.uuid4()

        if upload_link is None:
            print("Error: Unable to retrieve data for the given session ID.")
        else:
            payload = build_payload(session_id, upload_link, skills_raw, focus_skills_raw, tabswitch_count, fullscreen_exit_count, multi_person_count, cell_phone_count, get_uuid, batch_id, server_url)
            send_post_request(payload, session_id, cursor, conn)

        cooldown_time = random.randint(300, 600)
        print(f"Waiting for {cooldown_time} seconds before the next task...")
        sleep(cooldown_time)

        check_pending_evaluations.apply_async(countdown=cooldown_time)

    except mysql.connector.Error as e:
        logging.error(f"Database Error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_data(session_id, batch_id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(buffered=True)
    print(session_id, batch_id, "=======================")
    try:
        cursor.execute("""
            SELECT job_id
            FROM student_job_data
            WHERE batch_id = %s
        """, (batch_id,))
        result = cursor.fetchone()
        job_id = result[0] if result else None
        print("Job ID: ", job_id)

        if not job_id:
            print("No job_id found for batch_id:", batch_id)
            return (None,) * 8

        print("Fetching webhook URL...")
        cursor.execute("""
            SELECT webhook_url
            FROM job_details
            WHERE job_id = %s
        """, (job_id,))
        result = cursor.fetchone()
        server_url = result[0] if result else None
        print("Server URL:", server_url)

        cursor.execute("""
            SELECT Camera_uploads
            FROM interview_evaluations
            WHERE session_id = %s
        """, (session_id,))
        result = cursor.fetchone()
        upload_link = result[0] if result else None
        print("Upload Link: ", upload_link)

        cursor.execute("""
            SELECT technical_skills, focus_skills
            FROM job_details
            WHERE job_id = %s
        """, (job_id,))
        result = cursor.fetchone()
        skills_raw, focus_skills_raw = result if result else (None, None)

        cursor.execute("""
            SELECT tabswitch_count, fullscreen_exit_count
            FROM tabswitch_data
            WHERE session_id = %s
            ORDER BY id DESC
            LIMIT 1
        """, (session_id,))
        result = cursor.fetchone()
        tabswitch_count = result[0] if result else 0
        fullscreen_exit_count = result[1] if result else 0

        cursor.execute("""
            SELECT
                COUNT(CASE WHEN person_count > 1 THEN 1 END),
                COUNT(CASE WHEN cell_phone_detected = 1 THEN 1 END)
            FROM detected_images
            WHERE openai_session_id = %s
        """, (session_id,))
        result = cursor.fetchone()
        multi_person_count = result[0] if result else 0
        cell_phone_count = result[1] if result else 0

        return (upload_link, skills_raw, focus_skills_raw,
                tabswitch_count, fullscreen_exit_count,
                multi_person_count, cell_phone_count,
                server_url)

    finally:
        cursor.close()
        conn.close()

def build_payload(session_id, upload_link, skills_raw, focus_skills_raw,
                  tabswitch_count, fullscreen_exit_count, multi_person_count, cell_phone_count, get_uuid, batch_id, server_url):
    def to_skill_list(skill_str):
        if not skill_str:
            return []
        return [{"skill_title": s.strip()} for s in skill_str.split(",") if s.strip()]

    return {
        "server_url": server_url,
        "batch_id": batch_id,
        'openai_id': session_id,
        "is_agent": "1",
        "links": [
            {
                "id": str(get_uuid),
                "link": upload_link
            }
        ],
        "skill": to_skill_list(skills_raw),
        "focus_skill": to_skill_list(focus_skills_raw),
        "proctoring_data": [
            {"proctering_title": "Tab Switch", "proctering_count": tabswitch_count},
            {"proctering_title": "Exited Full Screen", "proctering_count": fullscreen_exit_count},
            {"proctering_title": "Multiple Face Detection", "proctering_count": multi_person_count},
            {"proctering_title": "cellphone", "proctering_count": cell_phone_count},
            {"proctering_title": "Dual monitor", "proctering_count": 0},
            {"proctering_title": "no face detected", "proctering_count": 0}
        ]
    }

def send_post_request(payload, session_id, cursor, conn):
    token=get_access_token()
    headers = {"Authorization":f"Bearer {token}",'Content-Type': 'application/json'}

    response = requests.post(API_POST_URL, headers=headers, data=json.dumps(payload))
    print("Header:", headers, response.text)
    if response.status_code == 201:
        print("Inside First Block")
        print("Request was successful. Updating status to 'PROCESSING'.", response.json())
        update_query = "UPDATE interview_evaluations SET status = 'PROCESSING' WHERE session_id = %s"
        cursor.execute(update_query, (session_id,))
        conn.commit()
    elif response.status_code not in (200, 201):
        print("Inside Second Block")
        print("Request failed. Marking status as 'ONETIMESEND'.", response.json())
        update_query = "UPDATE interview_evaluations SET status = 'ONETIMESEND' WHERE session_id = %s"
        cursor.execute(update_query, (session_id,))
        conn.commit()
    else:
        print("Inside Else Block")
        print(f"Request failed with status code: {response.status_code}. Marking as 'FAILED'.")
        update_query = "UPDATE interview_evaluations SET status = 'FAILED' WHERE session_id = %s"
        cursor.execute(update_query, (session_id,))
        conn.commit()

def get_access_token():
    username=config('REPORT_USER_NAME')
    password=config('REPORT_PASSWORD')
    api_url=config('REPORT_ACCESS_TOKEN_API')
    payload = {
        'username': username,
        'password': password
    }
    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        data = response.json()
        access_token = data.get('access')
        if access_token:
            print("Access token received:", access_token)
            return access_token
        else:
            print("Access token not found in response.")
            return None
 
    except requests.exceptions.RequestException as e:
        print("HTTP Request failed:", e)
        return None
