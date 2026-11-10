from django.test import TestCase, Client
from django.urls import reverse
from adminapp.models import Program, Branch, Year
from lmsapp.models import Student, Login, Enquiry

class LMSAppMappingTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.program = Program.objects.create(program="B.Tech")
        self.branch = Branch.objects.create(branch="Computer Science")
        self.year = Year.objects.create(year="First Year")

    def test_student_registration_and_login(self):
        reg_data = {
            'rollno': '3003',
            'name': 'Bob Tester',
            'fname': 'Father Bob',
            'mname': 'Mother Bob',
            'gender': 'male',
            'contactno': '9876543210',
            'address': 'Campus',
            'emailaddress': 'bob@test.com',
            'program': self.program.id,
            'branch': self.branch.id,
            'year': self.year.id,
            'password': 'password123',
            'confirmpassword': 'password123',
        }
        response = self.client.post(reverse('lmsapp:registration'), reg_data)
        self.assertEqual(response.status_code, 200)

        # Check DB
        student = Student.objects.filter(rollno='3003').first()
        self.assertIsNotNone(student)
        self.assertEqual(student.name, 'Bob Tester')
        self.assertEqual(student.program, self.program)
        self.assertEqual(student.branch, self.branch)
        self.assertEqual(student.year, self.year)

        login_record = Login.objects.filter(userid='3003').first()
        self.assertIsNotNone(login_record)
        self.assertEqual(login_record.password, 'password123')

        # Test login
        login_res = self.client.post(reverse('lmsapp:login'), {
            'userid': '3003',
            'password': 'password123',
            'usertype': 'student'
        })
        self.assertEqual(login_res.status_code, 302)
        self.assertIn(reverse('studentapp:studenthome'), login_res.url)

    def test_contact_us_enquiry(self):
        response = self.client.post(reverse('lmsapp:contactus'), {
            'name': 'Visitor',
            'gender': 'male',
            'Address': 'City',
            'contactno': '9998887776',
            'emailaddress': 'vis@test.com',
            'enquirytext': 'How to enroll?'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Enquiry.objects.filter(name='Visitor').exists())
