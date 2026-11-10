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
    student = Student.objects.all().select_related('program', 'branch', 'year')
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
    feed = StuResponse.objects.filter(responsetype='feedback').select_related(
        'student', 'student__program', 'student__branch', 'student__year'
    )
    return render(request, "viewfeedback.html", {'adminid': adminid, 'feed': feed})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def viewcomplain(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    comp = StuResponse.objects.filter(responsetype='complain').select_related(
        'student', 'student__program', 'student__branch', 'student__year'
    )
    return render(request, "viewcomplain.html", {'adminid': adminid, 'comp': comp})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def addbook(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    
    if request.method == "POST":
        program_val = request.POST.get('program')
        branch_val = request.POST.get('branch')
        year_val = request.POST.get('year')

        program_obj = Program.objects.filter(id=program_val).first() if str(program_val).isdigit() else Program.objects.filter(program=program_val).first()
        branch_obj = Branch.objects.filter(id=branch_val).first() if str(branch_val).isdigit() else Branch.objects.filter(branch=branch_val).first()
        year_obj = Year.objects.filter(id=year_val).first() if str(year_val).isdigit() else Year.objects.filter(year=year_val).first()

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
    book = BookStore.objects.all().select_related('program', 'branch', 'year')
    return render(request, "viewbook.html", locals())

def deletebook(request, bookid):
    BookStore.objects.filter(bookid=bookid).delete()
    return redirect('adminapp:viewbook')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def issuebook(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    book = BookStore.objects.all().select_related('program', 'branch', 'year')
    return render(request, "issuebook.html", locals())

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def issuebookui(request, bookid):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    book = BookStore.objects.select_related('program', 'branch', 'year').get(bookid=bookid)
    return render(request, "issuebookui.html", locals())

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def issue(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    
    if request.method == "POST":
        bookid = request.POST.get('bookid')
        rollno = request.POST.get('rollno')
        issuedate = request.POST.get('issuedate')
        duedate = request.POST.get('duedate')

        try:
            book_obj = BookStore.objects.get(bookid=bookid)
        except BookStore.DoesNotExist:
            messages.error(request, 'Book does not exist.')
            return redirect('adminapp:issuebook')

        if book_obj.qty <= 0:
            messages.error(request, 'This book is out of stock.')
            return redirect('adminapp:issuebook')

        try:
            stu_obj = Student.objects.get(rollno=rollno)
        except Student.DoesNotExist:
            messages.error(request, f'Student with Roll No {rollno} does not exist.')
            return redirect('adminapp:issuebookui', bookid=bookid)

        ib = IssueBook(
            book=book_obj,
            student=stu_obj,
            issuedate=issuedate,
            duedate=duedate,
            status='pending'
        )
        ib.save()
        
        # Deduct stock
        book_obj.qty -= 1
        book_obj.save()
        messages.success(request, f'Book "{book_obj.bookname}" successfully issued to {stu_obj.name} ({stu_obj.rollno}).')
        return redirect('adminapp:issuebook')
    return redirect('adminapp:issuebook')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def viewissuedbook(request):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    book = IssueBook.objects.filter(status='pending').select_related(
        'book', 'student', 'book__program', 'book__branch', 'book__year',
        'student__program', 'student__branch', 'student__year'
    )
    return render(request, "viewissuedbook.html", locals())

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def ret(request, id):
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    
    try:
        issued = IssueBook.objects.select_related('book').get(id=id)
        issued.status = 'return'
        issued.save()
        
        # Add back to stock using the relation
        issued.book.qty += 1
        issued.book.save()
        messages.success(request, f'Book "{issued.book.bookname}" returned successfully.')
    except IssueBook.DoesNotExist:
        messages.error(request, 'Issued book record not found.')
        
    return redirect('adminapp:viewissuedbook')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def returnbook(request): 
    if not request.session.get('adminid'):
        return redirect('lmsapp:login')
    adminid = request.session['adminid']
    book = IssueBook.objects.filter(status='return').select_related(
        'book', 'student', 'book__program', 'book__branch', 'book__year',
        'student__program', 'student__branch', 'student__year'
    )
    return render(request, "returnbook.html", locals())