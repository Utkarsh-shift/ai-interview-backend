from django.urls import path
from .views import post_student_data , merge_videos, post_job_data, DeleteStudentData,CheckBatchId
from .libcode import TokenObtainPairView,TokenRefreshView
from django.conf.urls.static import static
from django.conf import settings
from .views import  GetStudentData,getLinkvalidation
 
urlpatterns = [
    path('api/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/access_token',TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path("api/merge_videos/", merge_videos.as_view(), name="merge_videos"),
    path('api/get-student-data/', GetStudentData.as_view(), name='get_student_data'),
    path("api/post-job-details/", post_job_data.as_view(), name = "post_job_data"),
    path("api/post-student-details/", post_student_data.as_view(), name = "post_student_job_data"),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/delete-student-data/', DeleteStudentData.as_view(), name='delete_student_data'),
    path('api/check-batch-id/', CheckBatchId.as_view(), name='check-batch-id'),
    path('api/validate-link/', getLinkvalidation.as_view(), name='validate-link'),
]
