from django.shortcuts import render, redirect, reverse
from .models import Enquiry, Student, Login
from datetime import date
from django.contrib import messages
from adminapp.models import Program, Branch, Year

def index(request):
    return render(request, "index.html")

def aboutus(request):
    return render(request, "aboutus.html")

def registration(request):
    if request.method == "POST":
        rollno = request.POST['rollno']
        password = request.POST['password']
        
        # 1. Create the Login credentials FIRST so we can link it
        log = Login(userid=rollno, password=password, usertype='student', status='false')
        log.save()
        
        # 2. Fetch the Foreign Key Objects (supports both IDs and names)
        program_val = request.POST.get('program')
        branch_val = request.POST.get('branch')
        year_val = request.POST.get('year')

        program_obj = Program.objects.filter(id=program_val).first() if str(program_val).isdigit() else Program.objects.filter(program=program_val).first()
        branch_obj = Branch.objects.filter(id=branch_val).first() if str(branch_val).isdigit() else Branch.objects.filter(branch=branch_val).first()
        year_obj = Year.objects.filter(id=year_val).first() if str(year_val).isdigit() else Year.objects.filter(year=year_val).first()

        # 3. Create the Student and link everything
        stu = Student(
            login=log, # Linked to Login!
            rollno=rollno,
            name=request.POST['name'],
            fname=request.POST['fname'], 
            mname=request.POST['mname'],
            gender=request.POST['gender'],
            address=request.POST['address'],
            program=program_obj, # Linked to Program!
            branch=branch_obj,   # Linked to Branch!
            year=year_obj,       # Linked to Year!
            contactno=request.POST['contactno'],
            emailaddress=request.POST['emailaddress'],
            regdate=date.today()
        )
        stu.save()
        
        messages.success(request, "Student Registration Is Done")
        
    program = Program.objects.all()
    branch = Branch.objects.all()
    year = Year.objects.all()

    return render(request, "registration.html", locals())

def login(request):
    if request.method == "POST":
        userid = request.POST.get('userid')
        password = request.POST.get('password')
        usertype = request.POST.get('usertype')
        
        try:
            obj = Login.objects.get(userid=userid, password=password, usertype=usertype)
            if obj.usertype == "student":
               request.session['rollno'] = userid
               return redirect(reverse('studentapp:studenthome'))
            elif obj.usertype == "admin":
               request.session['adminid'] = userid
               return redirect(reverse('adminapp:adminhome'))
            else:
               messages.error(request, 'Invalid Userid or Password')
        except Login.DoesNotExist:
            messages.error(request, 'Invalid Userid or Password')
            
    return render(request, "login.html")

def contactus(request):
    if request.method == "POST":
        enq = Enquiry(
            name=request.POST['name'],
            gender=request.POST['gender'],
            address=request.POST['Address'], # Note: your HTML had capital A
            contactno=request.POST['contactno'],
            emailaddress=request.POST['emailaddress'],
            enquirytext=request.POST['enquirytext'],
            enquirydate=date.today()
        )
        enq.save()
        messages.success(request, 'Your enquiry is submitted')
    return render(request, "contactus.html")