from pathlib import Path
import json
import time
from concurrent.futures import ThreadPoolExecutor
from rest_framework.response import Response
from rest_framework import status

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .serializers import JobDataSerializer , StudentDataSerializer
from api_agent_backend.merg_chunks import merge_chunks
from api_agent_backend.Upload_S3 import upload_video_to_s3, store_video_urls_in_db
from rest_framework.views import APIView
from .models import StudentJobData

from decouple import config

BASE_DIR = Path(config('BASE_DIR'))

bucket_name = config('bucket_name')
aws_access_key_id = config('aws_access_key_id')
aws_secret_access_key = config('aws_secret_access_key')

executor = ThreadPoolExecutor(max_workers=10)

def wait_for_folder(path, retries=5, delay=2):
    for i in range(retries):
        if path.exists():
            print(f"Folder found: {path}")
            return True
        print(f"Waiting for folder: {path} (Attempt {i+1}/{retries})")
        time.sleep(delay)
    return False

def process_merge_and_upload(session_id):
    try:
        print("\nInside process_merge_and_upload function")
        print(f"Session ID: {session_id}")
 
        session_id_screen = session_id + "_screen"
 
        paths = {
            "screen": {
                "input": BASE_DIR / "screen_uploads" / session_id_screen,
                "folder_type": "screen_uploads"
            },
            "camera": {
                "input": BASE_DIR / "uploads" / session_id,
                "folder_type": "Camera_uploads"
            }
        }
 
        screen_url = None
        camera_url = None
 
        for key, val in paths.items():
            input_path = val["input"]
            folder_type = val["folder_type"]
 
            output_file = input_path / f"final_{session_id}.mp4"
 
            print(f"Checking for folder: {input_path}")
 
            if wait_for_folder(input_path, retries=5, delay=2):
                success, msg = merge_chunks(input_path, output_file)
                print(f"Merging {folder_type}: Success={success}, Message='{msg}'")
 
                if success:
                    s3_video_file_url = upload_video_to_s3(
                        file_name=str(output_file),
                        bucket_name=bucket_name,
                        session_id=session_id,
                        folder_type=folder_type,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key
                    )
                    if s3_video_file_url:
                        print(f"Video uploaded to S3 ({folder_type}): {s3_video_file_url}")
 
                        if folder_type == "screen_uploads":
                            screen_url = s3_video_file_url
                        elif folder_type == "Camera_uploads":
                            camera_url = s3_video_file_url
                else:
                    print(f"Merging failed for {folder_type}. Skipping upload.")
            else:
                print(f"Folder not found after retries: {input_path}. Skipping {folder_type}.")
 
        if screen_url or camera_url:
            print(f"Storing URLs in database: screen_url={screen_url}, camera_url={camera_url}")
            store_video_urls_in_db(session_id, screen_url=screen_url, camera_url=camera_url)
        else:
            print(f"No videos to store for session_id: {session_id}")
 
    except Exception as e:
        print(f"Exception in process_merge_and_upload for session_id={session_id}: {str(e)}")


from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class CheckBatchId(APIView):
    def post(self, request, *args, **kwargs):
        """
        Checks if the batch_id exists in the StudentJobData model.
        """
        batch_id = request.data.get('batch_id')

        if not batch_id:
            return Response({
                "status": "failure",
                "message": "batch_id is required",
                "status_code": 400
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            student_instance = StudentJobData.objects.filter(batch_id=batch_id).first()

            if student_instance:
                return Response({
                    "status": "success",
                    "message": f"Student data with batch_id {batch_id} exists",
                    "status_code": 200
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "failure",
                    "message": f"No student data found with batch_id {batch_id}",
                    "status_code": 404
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                "status": "failure",
                "message": f"Error: {str(e)}",
                "status_code": 500
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@method_decorator(csrf_exempt, name='dispatch')
class merge_videos(APIView):
    def post(self, request, *args, **kwargs):
        """Handle video merging request."""
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                session_id = data.get("session_id")
    
                if not session_id:
                    return JsonResponse({"error": "Missing session_id"}, status=400)
    
                executor.submit(process_merge_and_upload, session_id)
                return JsonResponse({"success": True, "message": f"Merging started for {session_id}"}, status=200)
            
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON data"}, status=400)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
    
        return JsonResponse({"error": "Invalid request method"}, status=405)
    
    

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import StudentJobData

@method_decorator(csrf_exempt, name='dispatch')
class DeleteStudentData(APIView):
    def delete(self, request, *args, **kwargs):
        batch_array = request.data.get('array')

        if not batch_array or not isinstance(batch_array, list):
            return Response({
                "status": "failure",
                "message": "A valid 'array' of batch_ids is required",
                "status_code": 400
            }, status=status.HTTP_400_BAD_REQUEST)

        deleted = []
        not_found = []

        try:
            for item in batch_array:
                batch_id = item.get('batch_id')
                if batch_id:
                    deleted_count, _ = StudentJobData.objects.filter(batch_id=batch_id).delete()
                    if deleted_count:
                        deleted.append(batch_id)
                    else:
                        not_found.append(batch_id)
                else:
                    not_found.append(None)

            return Response({
                "status": "success",
                "deleted_batch_ids": deleted,
                "not_found_batch_ids": not_found,
                "status_code": 200
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "failure",
                "message": f"Error: {str(e)}",
                "status_code": 500
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from api_agent_backend.models import StudentJobData
from api_agent_backend.serializers import   StudentDataSerializer 
from django.conf import settings
import json

class post_student_data(APIView):
    def post(self, request, *args, **kwargs):
       
        if isinstance(request.data, str):
            data = json.loads(request.data)
        else:
            data = request.data

        
        batch_id = data.get('batch_id')
        
        if not batch_id:
            return Response({
                "status": "failure",
                "message": "batch_id is required",
                "status_code": 400
            }, status=400)

        
        student_instance = StudentJobData.objects.filter(batch_id=batch_id).first()
        
        if student_instance:
            
            serializer = StudentDataSerializer(student_instance, data=data)
            if serializer.is_valid():
                serializer.save()  
                redirect_url = f"{settings.CUSTOM_BASE_URL}/?batch_id={student_instance.batch_id}&job_id={student_instance.job_id}"
                return Response({
                    "status": "success",
                    "message": "Student data updated successfully",
                    "redirect_url": redirect_url,
                    "status_code": 200
                }, status=200)
            else:
                return Response({
                    "status": "failure",
                    "errors": serializer.errors,
                    "status_code": 400
                }, status=400)
        else:
            serializer = StudentDataSerializer(data=data)
            if serializer.is_valid():
                instance = serializer.save()  # Create and save the new instance
                redirect_url = f"{settings.CUSTOM_BASE_URL}/?batch_id={instance.batch_id}&job_id={instance.job_id}"
                return Response({
                    "status": "success",
                    "message": "Student data created successfully",
                    "redirect_url": redirect_url,
                    "status_code": 200
                }, status=200)
            else:
                return Response({
                    "status": "failure",
                    "errors": serializer.errors,
                    "status_code": 400
                }, status=400)

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import JobDetails as JobData
from .serializers import JobDataSerializer

class post_job_data(APIView):
    def post(self, request, *args, **kwargs):

        many = isinstance(request.data, list)
        serializer = JobDataSerializer(data=request.data, many=many)

        if serializer.is_valid():
            for data in serializer.validated_data:

                if isinstance(request.data, str):
                    import json
                    data = json.loads(request.data)
                else:
                    data = request.data
                job_id = data.get('job_id') 
                
                
                existing_job = JobData.objects.filter(job_id=job_id).first()  
                if existing_job:
                    for field, value in data.items():
                        setattr(existing_job, field, value)  
                    existing_job.save()  
                else:
                    JobData.objects.create(**data)  

            return Response({
                "status": "success",
                "message": "Student data successfully posted or updated!",
                "status_code": status.HTTP_200_OK
            }, status=status.HTTP_200_OK)
        
        return Response({
            "status": "failure",
            "errors": serializer.errors,
            "status_code": status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)

 
 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import StudentJobData
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class GetStudentData(APIView):
    def post(self, request):
     
        batch_id = request.data.get('batch_id') 


        if not batch_id:
            return Response({"error": "Missing batch_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student_data = StudentJobData.objects.get(batch_id=batch_id)
            response_data = {
                "batch_id": student_data.batch_id,
                "student_name": student_data.student_name,
                "education": student_data.education,
                "student_experience": student_data.student_experience,
                "certfication": student_data.certfication,
                "skills": student_data.skills,
                "projects": student_data.projects,
                "selected_language": student_data.selected_language,
                "agent": student_data.agent,
                "job_id": student_data.job_id,
                "created_at": student_data.created_at,
                "updated_at": student_data.updated_at,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except StudentJobData.DoesNotExist:
            return Response({"error": "Student data not found or invalid"}, status=status.HTTP_404_NOT_FOUND)