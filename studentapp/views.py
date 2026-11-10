from django.shortcuts import render, redirect
from lmsapp.models import Student, Login
from django.views.decorators.cache import cache_control
from .models import StuResponse
from datetime import date
from django.contrib import messages
from adminapp.models import IssueBook

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def studenthome(request):
    if not request.session.get('rollno'):
        return redirect('lmsapp:login')
        
    rollno = request.session['rollno']
    stu = Student.objects.get(rollno=rollno)
    return render(request, 'studenthome.html', {'stu': stu})

def studentlogout(request):
    if 'rollno' in request.session:
        del request.session['rollno']
    return redirect('lmsapp:login')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def response(request):
    if not request.session.get('rollno'):
        return redirect('lmsapp:login')
        
    rollno = request.session['rollno']
    stu = Student.objects.get(rollno=rollno)
    
    if request.method == "POST":
        # Link the response directly to the student object
        sr = StuResponse(
            student=stu, 
            responsetype=request.POST['responsetype'],
            subject=request.POST['subject'],
            responsetext=request.POST['responsetext'],
            responsedate=date.today()
        )
        sr.save()
        messages.success(request, 'Response Is Submitted')
        
    return render(request, "response.html", {'stu': stu})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def changepassword(request):
    if not request.session.get('rollno'):
        return redirect('lmsapp:login')
        
    rollno = request.session['rollno']
    stu = Student.objects.get(rollno=rollno)
    
    if request.method == "POST":
        oldpassword = request.POST['oldpassword']
        newpassword = request.POST['newpassword']
        confirmpassword = request.POST['confirmpassword']
        
        if newpassword != confirmpassword:
            messages.error(request, 'New password and Confirm password do not match')
            return render(request, "changepassword.html", {'stu': stu})
            
        try:
            log = Login.objects.get(userid=rollno, password=oldpassword)
            log.password = newpassword
            log.save()
            return redirect('studentapp:studentlogout')
        except Login.DoesNotExist:
            messages.error(request, 'Old password is not matched')
            
    return render(request, 'changepassword.html', {'stu': stu})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def viewstudentbook(request):
    if not request.session.get('rollno'):
        return redirect('lmsapp:login')
        
    rollno = request.session['rollno']
    try:
        stu = Student.objects.get(rollno=rollno)
    except Student.DoesNotExist:
        return redirect('lmsapp:login')
    
    # Filter by the relation!
    book = IssueBook.objects.filter(student=stu).select_related('book', 'book__program', 'book__branch', 'book__year')
    return render(request, 'viewstudentbook.html', locals())