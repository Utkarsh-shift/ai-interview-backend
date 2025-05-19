
import os
import mysql.connector
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from datetime import datetime
from decouple import config
host = config('host')
user = config('user')
password = config('password')
database = config('database')

DB_CONFIG = {
    "host": host,
    "user": user,
    "password": password,
    "database": database
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def upload_video_to_s3(file_name, bucket_name, session_id, folder_type, aws_access_key_id=None, aws_secret_access_key=None):
    if folder_type not in ['screen_uploads', 'Camera_uploads']:
        print(f"Invalid folder_type: {folder_type}")
        return None

    object_name = f"{session_id}/{folder_type}/{os.path.basename(file_name)}"

    s3_client = boto3.client('s3', 
                            aws_access_key_id=aws_access_key_id,
                            aws_secret_access_key=aws_secret_access_key)

    try:
        s3_client.upload_file(file_name, bucket_name, object_name)

        print(f"File {file_name} uploaded successfully to {bucket_name}/{object_name}")
        file_url = f"https://{bucket_name}.s3.amazonaws.com/{object_name}"
        print(f"File URL: {file_url}")

        os.remove(file_name)
        print(f"File {file_name} deleted from local system.")

        return file_url
    except FileNotFoundError:
        print(f"File {file_name} not found.")
        return None
    except NoCredentialsError:
        print("Credentials not available.")
        return None
    except PartialCredentialsError:
        print("Incomplete credentials.")
        return None
    except Exception as e:
        print(f"Error uploading file: {e}")
        return None

def store_video_urls_in_db(session_id, screen_url=None, camera_url=None):
    conn = get_db_connection()
    if not conn:
        print("Database connection failed. Cannot insert data.")
        return False

    try:
        print("******************************************************")
        cursor = conn.cursor()
        update_query = """
            UPDATE interview_evaluations
            SET screen_uploads = %s,
                Camera_uploads = %s
            WHERE session_id = %s
        """
        cursor.execute(update_query, (screen_url, camera_url, session_id))
        print(f"Updated existing record for session_id: {session_id}")
    

        conn.commit()
        return True
    except Exception as e:
        print(f"Error inserting/updating database: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
