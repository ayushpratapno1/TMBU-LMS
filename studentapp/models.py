from django.db import models

class StuResponse(models.Model):
    # If the student is deleted, delete all their responses automatically
    student = models.ForeignKey('lmsapp.Student', on_delete=models.CASCADE)
    
    responsetype = models.CharField(max_length=50)
    subject = models.CharField(max_length=500)
    responsetext = models.CharField(max_length=1000)
    responsedate = models.CharField(max_length=30)

    def __str__(self):
        return f"{self.responsetype} from {self.student.name}"