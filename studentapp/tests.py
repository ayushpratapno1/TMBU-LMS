from django.test import TestCase, Client
from django.urls import reverse
from adminapp.models import Program, Branch, Year, BookStore, IssueBook
from lmsapp.models import Student, Login
from studentapp.models import StuResponse

class StudentAppMappingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Master data
        self.program = Program.objects.create(program="B.Tech")
        self.branch = Branch.objects.create(branch="Information Technology")
        self.year = Year.objects.create(year="Second Year")

        # Student & Login
        self.login = Login.objects.create(userid="2002", password="password123", usertype="student", status="active")
        self.student = Student.objects.create(
            login=self.login,
            rollno="2002",
            name="Alice Smith",
            fname="Bob Smith",
            mname="Carol Smith",
            gender="female",
            address="Campus Hostel",
            program=self.program,
            branch=self.branch,
            year=self.year,
            contactno="9123456780",
            emailaddress="alice@test.com",
            regdate="2026-11-01"
        )

        # Login student into session
        session = self.client.session
        session['rollno'] = '2002'
        session.save()

        # Book
        self.book = BookStore.objects.create(
            bookid="TMBU-202",
            isbnno="ISBN-202",
            program=self.program,
            branch=self.branch,
            year=self.year,
            subject="Algorithms",
            bookname="Introduction to Algorithms",
            authorname="CLRS",
            qty=3
        )

        # Issue book to student
        self.issue = IssueBook.objects.create(
            book=self.book,
            student=self.student,
            issuedate="2026-11-05",
            duedate="2026-11-20",
            status="pending"
        )

    def test_viewstudentbook_renders_book_details(self):
        response = self.client.get(reverse('studentapp:viewstudentbook'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Verify book details are visible to student
        self.assertIn("TMBU-202", content)
        self.assertIn("Introduction to Algorithms", content)
        self.assertIn("Algorithms", content)
        self.assertIn("CLRS", content)
        self.assertIn("2026-11-05", content)
        self.assertIn("2026-11-20", content)
        self.assertIn("pending", content)

    def test_studenthome_renders_profile(self):
        response = self.client.get(reverse('studentapp:studenthome'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("2002", content)
        self.assertIn("Alice Smith", content)
        self.assertIn("Information Technology", content)
        self.assertIn("Second Year", content)
