from django.db import models
from django.utils import timezone

class DetectedImage(models.Model):
    id = models.AutoField(primary_key=True)
    image_data = models.TextField()
    person_count = models.IntegerField()
    cell_phone_detected = models.BooleanField()
    openai_session_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'detected_images'


class InterviewEvaluation(models.Model):
    id = models.AutoField(primary_key=True)
    session_id = models.CharField(max_length=255)
    evaluation_text = models.TextField(null=True, blank=True)
    performance_score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=255, null=True, blank=True)
    Camera_uploads = models.TextField(null=True, blank=True)
    screen_uploads = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'interview_evaluations'
        constraints = [
            models.CheckConstraint(check=models.Q(performance_score__gte=0, performance_score__lte=100),
                                   name='performance_score_between_0_and_100')
        ]


class InterviewTranscript(models.Model):
    
    itemId = models.CharField( primary_key=True , max_length=255)
    type = models.CharField(max_length=50, null=True, blank=True)
    role = models.CharField(max_length=50, null=True, blank=True)
    title = models.TextField(null=True, blank=True)
    timestamp = models.CharField(max_length=50, null=True, blank=True)
    createdAtMs = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    isHidden = models.BooleanField(null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    Vision_Analysis = models.TextField(null=True, blank=True)
    Agent = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'interview_transcripts'


class LipsyncSession(models.Model):
    id = models.AutoField(primary_key=True)
    openai_session_id = models.CharField(max_length=255, null=True, blank=True)
    batch_id = models.CharField(max_length=255, null=True, blank=True)
    job_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    Status = models.CharField(max_length=50, default='Session Pending')
    class Meta:
        db_table = 'lipsync_openaiid_batchid'
 

class Log(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=255)
    event = models.JSONField()
    suffix = models.CharField(max_length=255, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'logs'


class TabswitchData(models.Model):
    id = models.AutoField(primary_key=True)
    session_id = models.CharField(max_length=255)
    image_data = models.BinaryField(null=True, blank=True)
    tabevent = models.CharField(max_length=255, null=True, blank=True)
    tabswitch_count = models.IntegerField(null=True, blank=True)
    fullscreen_exit_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tabswitch_data'


class UserFeedback(models.Model):
    id = models.AutoField(primary_key=True)
    openai_session_id = models.CharField(max_length=255)
    feedback = models.TextField()
    rating = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_feedback'




from django.db import models
from django.utils import timezone

class JobDetails(models.Model):
    id = models.AutoField(primary_key=True)
    job_id = models.CharField(max_length=100, default=99999999) 
    title = models.TextField(default="Unknown")
    description = models.TextField(default="Unknown")
    technical_skills = models.TextField(default="Unknown")
    behavioural_skills = models.TextField(default="Unknown",  null=True, blank=True)
    focus_skills = models.TextField(default="Unknown")
    industry = models.CharField(max_length=800, default="Unknown")
    min_experience = models.CharField(max_length=100, default="Unknown")
    max_experience = models.CharField(max_length=100, default="Unknown")
    created_at = models.DateTimeField(default=timezone.now)
   

    class Meta:
        db_table = 'job_details'

    def __str__(self):
        return self.job_id
 





class StudentJobData(models.Model):
    id = models.AutoField(primary_key=True)
    batch_id = models.CharField(max_length=100, default="Unknown",unique=False)  
    student_name = models.CharField(max_length=100, default="Unknown")
    education = models.CharField(max_length=100, default="Unknown")
    student_experience = models.CharField(max_length=100, default="Unknown")
    certfication = models.JSONField(default=dict)  
    skills = models.CharField(max_length=1000, default="Unknown")
    projects = models.JSONField(default=dict)  
    selected_language = models.CharField(max_length=50, default="Unknown")
    agent = models.CharField(max_length=1002, default="Unknown")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    job_id = models.CharField(max_length=100, default="Unknown")
    webhook_url = models.CharField(max_length=1000, default="Unknown")
    class Meta:
        db_table = 'student_job_data'

    def __str__(self):
        return str(self.batch_id)
