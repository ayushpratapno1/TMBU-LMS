from django.test import TestCase, Client
from django.urls import reverse
from adminapp.models import Program, Branch, Year, BookStore, IssueBook
from lmsapp.models import Student, Login
from studentapp.models import StuResponse

class AdminAppMappingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Create test session for admin
        session = self.client.session
        session['adminid'] = 'admin'
        session.save()

        # Create master data
        self.program = Program.objects.create(program="B.Tech")
        self.branch = Branch.objects.create(branch="Computer Science")
        self.year = Year.objects.create(year="Third Year")

        # Create student login & student
        self.login = Login.objects.create(userid="1001", password="password123", usertype="student", status="active")
        self.student = Student.objects.create(
            login=self.login,
            rollno="1001",
            name="Test Student",
            fname="Father Name",
            mname="Mother Name",
            gender="male",
            address="Test Address",
            program=self.program,
            branch=self.branch,
            year=self.year,
            contactno="9876543210",
            emailaddress="student@test.com",
            regdate="2026-11-01"
        )

        # Create Book
        self.book = BookStore.objects.create(
            bookid="TMBU-101",
            isbnno="ISBN-101",
            program=self.program,
            branch=self.branch,
            year=self.year,
            subject="Operating Systems",
            bookname="Modern Operating Systems",
            authorname="Tanenbaum",
            qty=5
        )

        # Issue book to student
        self.issued_pending = IssueBook.objects.create(
            book=self.book,
            student=self.student,
            issuedate="2026-11-01",
            duedate="2026-11-15",
            status="pending"
        )

        # Returned book
        self.issued_returned = IssueBook.objects.create(
            book=self.book,
            student=self.student,
            issuedate="2026-10-01",
            duedate="2026-10-15",
            status="return"
        )

        # Feedback & Complain
        self.feedback = StuResponse.objects.create(
            student=self.student,
            responsetype="feedback",
            subject="Great Library",
            responsetext="Excellent collection of books",
            responsedate="2026-11-02"
        )
        self.complain = StuResponse.objects.create(
            student=self.student,
            responsetype="complain",
            subject="Book Damaged",
            responsetext="Page 20 is torn",
            responsedate="2026-11-03"
        )

    def test_viewissuedbook_renders_data(self):
        response = self.client.get(reverse('adminapp:viewissuedbook'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # Verify book details are rendered
        self.assertIn("TMBU-101", content)
        self.assertIn("Modern Operating Systems", content)
        self.assertIn("Tanenbaum", content)
        self.assertIn("Operating Systems", content)
        # Verify student details are rendered
        self.assertIn("1001", content)
        self.assertIn("Test Student", content)
        self.assertIn("Computer Science", content)
        self.assertIn("Third Year", content)

    def test_returnbook_renders_data(self):
        response = self.client.get(reverse('adminapp:returnbook'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("TMBU-101", content)
        self.assertIn("Modern Operating Systems", content)
        self.assertIn("Test Student", content)
        self.assertIn("1001", content)

    def test_viewfeedback_renders_data(self):
        response = self.client.get(reverse('adminapp:viewfeedback'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("1001", content)
        self.assertIn("Test Student", content)
        self.assertIn("Computer Science", content)
        self.assertIn("Great Library", content)

    def test_viewcomplain_renders_data(self):
        response = self.client.get(reverse('adminapp:viewcomplain'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("1001", content)
        self.assertIn("Test Student", content)
        self.assertIn("Computer Science", content)
        self.assertIn("Book Damaged", content)

    def test_issue_book_and_return_cycle(self):
        initial_qty = self.book.qty
        issue_res = self.client.post(reverse('adminapp:issue'), {
            'bookid': self.book.bookid,
            'rollno': self.student.rollno,
            'issuedate': '2026-11-10',
            'duedate': '2026-11-25',
        })
        self.assertEqual(issue_res.status_code, 302)
        self.book.refresh_from_db()
        self.assertEqual(self.book.qty, initial_qty - 1)

        new_issue = IssueBook.objects.filter(
            book=self.book, student=self.student, status='pending'
        ).last()
        self.assertIsNotNone(new_issue)

        # Return the newly issued book
        ret_res = self.client.get(reverse('adminapp:ret', kwargs={'id': new_issue.id}))
        self.assertEqual(ret_res.status_code, 302)
        new_issue.refresh_from_db()
        self.assertEqual(new_issue.status, 'return')
        self.book.refresh_from_db()
        self.assertEqual(self.book.qty, initial_qty)

    def test_add_book(self):
        post_data = {
            'bookid': '999',
            'isbnno': 'ISBN-999',
            'program': self.program.id,
            'branch': self.branch.id,
            'year': self.year.id,
            'subject': 'Compiler Design',
            'bookname': 'Principles of Compiler Design',
            'authorname': 'Aho Ullman',
            'qty': '2'
        }
        res = self.client.post(reverse('adminapp:addbook'), post_data)
        self.assertEqual(res.status_code, 200)
        created_book = BookStore.objects.filter(bookid='TMBU-999').first()
        self.assertIsNotNone(created_book)
        self.assertEqual(created_book.program, self.program)
        self.assertEqual(created_book.branch, self.branch)
        self.assertEqual(created_book.year, self.year)
