from django.db import models

class Login(models.Model):
    userid = models.CharField(max_length=50, primary_key=True)
    password = models.CharField(max_length=30)
    usertype = models.CharField(max_length=50)
    status = models.CharField(max_length=10, default='active')

    def __str__(self):
        return f"{self.userid} ({self.usertype})"

class Student(models.Model):
    # This links the student directly to their login. If Login is deleted, Student is deleted.
    login = models.OneToOneField(Login, on_delete=models.CASCADE, null=True)
    
    rollno = models.CharField(max_length=20, primary_key=True) # Fixed IntegerField bug
    name = models.CharField(max_length=50)
    fname = models.CharField(max_length=50)
    mname = models.CharField(max_length=50)
    gender = models.CharField(max_length=6)
    address = models.TextField()
    
    # Linked to AdminApp models instead of just typing strings
    program = models.ForeignKey('adminapp.Program', on_delete=models.SET_NULL, null=True)
    branch = models.ForeignKey('adminapp.Branch', on_delete=models.SET_NULL, null=True)
    year = models.ForeignKey('adminapp.Year', on_delete=models.SET_NULL, null=True)
    
    contactno = models.CharField(max_length=10)
    emailaddress = models.CharField(max_length=50)
    regdate = models.CharField(max_length=30) # Consider DateField in the future

    def __str__(self):
        return f"{self.name} ({self.rollno})"

class Enquiry(models.Model):
    name = models.CharField(max_length=50)
    gender = models.CharField(max_length=6)
    address = models.TextField()
    contactno = models.CharField(max_length=10)
    emailaddress = models.CharField(max_length=50)
    enquirytext = models.TextField()
    enquirydate = models.CharField(max_length=30)

    def __str__(self):
        return f"Enquiry from {self.name}"