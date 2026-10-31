from django.shortcuts import render, redirect
from django.views.decorators.cache import cache_control
from lmsapp.models import Student, Login, Enquiry
from studentapp.models import StuResponse
from .models import Program, Branch, Year, BookStore, IssueBook
from django.contrib import messages

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def adminhome(request):
    try:
        if request.session.get('adminid'):
            adminid = request.session['adminid']
            return render(request, "adminhome.html", {'adminid': adminid})
        return redirect('lmsapp:login')
    except KeyError:
        return redirect('lmsapp:login')

def adminlogout(request):
    if 'adminid' in request.session:
        del request.session['adminid']
    return redirect('lmsapp:login')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def viewstudents(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    student = Student.objects.all()
    return render(request, "viewstudents.html", {'adminid': adminid, 'student': student})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def viewenquiry(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    enq = Enquiry.objects.all()
    return render(request, "viewenquiry.html", {'adminid': adminid, 'enq': enq})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def viewfeedback(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    feed = StuResponse.objects.filter(responsetype='feedback')
    return render(request, "viewfeedback.html", {'adminid': adminid, 'feed': feed})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def viewcomplain(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    comp = StuResponse.objects.filter(responsetype='complain')
    return render(request, "viewcomplain.html", {'adminid': adminid, 'comp': comp})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def addbook(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    
    if request.method == "POST":
        try:
            program_obj = Program.objects.get(id=request.POST['program'])
            branch_obj = Branch.objects.get(id=request.POST['branch'])
            year_obj = Year.objects.get(id=request.POST['year'])
        except (ValueError, Program.DoesNotExist):
            program_obj = Program.objects.filter(program=request.POST['program']).first()
            branch_obj = Branch.objects.filter(branch=request.POST['branch']).first()
            year_obj = Year.objects.filter(year=request.POST['year']).first()

        book = BookStore(
            bookid="TMBU-" + request.POST['bookid'],
            isbnno=request.POST['isbnno'],
            program=program_obj,
            branch=branch_obj,
            year=year_obj,
            subject=request.POST['subject'],
            bookname=request.POST['bookname'],
            authorname=request.POST['authorname'],
            qty=request.POST['qty']
        )
        book.save()
        messages.success(request, 'Book detail is added')
        
    adminid = request.session['adminid']
    program = Program.objects.all()
    branch = Branch.objects.all()
    year = Year.objects.all()
    return render(request, "addbook.html", locals())

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def viewbook(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    book = BookStore.objects.all()
    return render(request, "viewbook.html", locals())

def deletebook(request, bookid):
    BookStore.objects.filter(bookid=bookid).delete()
    return redirect('adminapp:viewbook')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def issuebook(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    book = BookStore.objects.all()
    return render(request, "issuebook.html", locals())

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def issuebookui(request, bookid):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    book = BookStore.objects.get(bookid=bookid)
    return render(request, "issuebookui.html", locals())

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def issue(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    
    if request.method == "POST":
        # Simply get the Book object and Student object
        book_obj = BookStore.objects.get(bookid=request.POST['bookid'])
        stu_obj = Student.objects.get(rollno=request.POST['rollno'])
        
        # Link them directly! No need to copy-paste the branch, year, name, etc.
        ib = IssueBook(
            book=book_obj,
            student=stu_obj,
            issuedate=request.POST['issuedate'],
            duedate=request.POST['duedate'],
            status='pending'
        )
        ib.save()
        
        # Deduct stock
        book_obj.qty -= 1
        book_obj.save()
        
        return redirect('adminapp:issuebook')
    return redirect('adminapp:issuebook')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def viewissuedbook(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    book = IssueBook.objects.filter(status='pending')
    return render(request, "viewissuedbook.html", locals())

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def ret(request, id):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    
    issued = IssueBook.objects.get(id=id)
    issued.status = 'return'
    issued.save()
    
    # Add back to stock using the relation
    issued.book.qty += 1
    issued.book.save()
    
    return redirect('adminapp:viewissuedbook')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def returnbook(request): 
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    book = IssueBook.objects.filter(status='return')
    return render(request, "returnbook.html", locals())