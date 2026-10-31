from django.db import models

class Program(models.Model):
    program = models.CharField(max_length=100)
    def __str__(self):
        return self.program

class Branch(models.Model):
    branch = models.CharField(max_length=100)
    def __str__(self):
        return self.branch

class Year(models.Model):
    year = models.CharField(max_length=100)
    def __str__(self):
        return self.year

class BookStore(models.Model):
    bookid = models.CharField(max_length=15, primary_key=True)
    isbnno = models.CharField(max_length=15)
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True)
    year = models.ForeignKey(Year, on_delete=models.SET_NULL, null=True)
    subject = models.CharField(max_length=100)
    bookname = models.CharField(max_length=100)
    authorname = models.CharField(max_length=100)
    qty = models.IntegerField()

    def __str__(self):
        return self.bookname

class IssueBook(models.Model):
    # Links directly to the Book and Student tables
    book = models.ForeignKey(BookStore, on_delete=models.CASCADE)
    student = models.ForeignKey('lmsapp.Student', on_delete=models.CASCADE)
    
    issuedate = models.CharField(max_length=30)
    duedate = models.CharField(max_length=30)
    status = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.book.bookname} issued to {self.student.name}"