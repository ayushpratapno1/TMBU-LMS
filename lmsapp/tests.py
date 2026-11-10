from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from adminapp.models import Program, Branch, Year
from lmsapp.models import Student, Login, Enquiry
from unittest.mock import patch
import time

class LMSAppMappingTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.program = Program.objects.create(program="B.Tech")
        self.branch = Branch.objects.create(branch="Computer Science")
        self.year = Year.objects.create(year="First Year")

        # Create admin user & login
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@testlibrary.com',
            password='AdminPassword123'
        )
        self.admin_login = Login.objects.create(
            userid='admin_test',
            password='AdminPassword123',
            usertype='admin',
            status='active'
        )

    def tearDown(self):
        cache.clear()

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

        # Test student login bypasses 2FA directly to studenthome
        login_res = self.client.post(reverse('lmsapp:login'), {
            'userid': '3003',
            'password': 'password123',
            'usertype': 'student'
        })
        self.assertEqual(login_res.status_code, 302)
        self.assertIn(reverse('studentapp:studenthome'), login_res.url)
        self.assertEqual(self.client.session.get('rollno'), '3003')
        self.assertIsNone(self.client.session.get('adminid'))

    def test_registration_validation_invalid_contactno(self):
        reg_data = {
            'rollno': '3004',
            'name': 'Charlie',
            'fname': 'Father',
            'mname': 'Mother',
            'gender': 'male',
            'contactno': '123',  # Invalid phone
            'address': 'Campus',
            'emailaddress': 'charlie@test.com',
            'program': self.program.id,
            'branch': self.branch.id,
            'year': self.year.id,
            'password': 'password123',
            'confirmpassword': 'password123',
        }
        response = self.client.post(reverse('lmsapp:registration'), reg_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Contact number must be exactly 10 digits", response.content.decode())
        self.assertFalse(Student.objects.filter(rollno='3004').exists())

    def test_registration_validation_password_mismatch(self):
        reg_data = {
            'rollno': '3005',
            'name': 'David',
            'fname': 'Father',
            'mname': 'Mother',
            'gender': 'male',
            'contactno': '9876543211',
            'address': 'Campus',
            'emailaddress': 'david@test.com',
            'program': self.program.id,
            'branch': self.branch.id,
            'year': self.year.id,
            'password': 'password123',
            'confirmpassword': 'wrongpassword',
        }
        response = self.client.post(reverse('lmsapp:registration'), reg_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Password and Confirm Password do not match", response.content.decode())
        self.assertFalse(Student.objects.filter(rollno='3005').exists())

    def test_registration_duplicate_rollno(self):
        # Create an existing student
        Login.objects.create(userid='3006', password='password123', usertype='student')
        reg_data = {
            'rollno': '3006',
            'name': 'Duplicate',
            'fname': 'Father',
            'mname': 'Mother',
            'gender': 'male',
            'contactno': '9876543212',
            'address': 'Campus',
            'emailaddress': 'dup@test.com',
            'program': self.program.id,
            'branch': self.branch.id,
            'year': self.year.id,
            'password': 'password123',
            'confirmpassword': 'password123',
        }
        response = self.client.post(reverse('lmsapp:registration'), reg_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("already exists", response.content.decode())

    def test_registration_rate_limiting(self):
        # Max 30 registrations allowed per 5 min per IP
        reg_data = {
            'name': 'Test Student',
            'fname': 'Father',
            'mname': 'Mother',
            'gender': 'male',
            'contactno': '9876543213',
            'address': 'Campus',
            'emailaddress': 'test@test.com',
            'program': self.program.id,
            'branch': self.branch.id,
            'year': self.year.id,
            'password': 'password123',
            'confirmpassword': 'password123',
        }
        for i in range(30):
            d = dict(reg_data)
            d['rollno'] = f"301{i}"
            res = self.client.post(reverse('lmsapp:registration'), d)
            self.assertEqual(res.status_code, 200)

        # 31st attempt should be blocked by rate limit
        d = dict(reg_data)
        d['rollno'] = "3099"
        res = self.client.post(reverse('lmsapp:registration'), d)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Too many registration requests", res.content.decode())
        self.assertFalse(Student.objects.filter(rollno='3099').exists())

    def test_login_failed_attempts_lockout(self):
        # 10 consecutive failed logins trigger a 1-minute lockout
        for i in range(9):
            res = self.client.post(reverse('lmsapp:login'), {
                'userid': 'admin_test',
                'password': 'WrongPassword',
                'usertype': 'admin'
            })
            self.assertEqual(res.status_code, 200)
            self.assertIn("remaining", res.content.decode())

        # 10th failed attempt locks out the account
        res = self.client.post(reverse('lmsapp:login'), {
            'userid': 'admin_test',
            'password': 'WrongPassword',
            'usertype': 'admin'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("Please wait 1 minute before trying again", res.content.decode())

        # 11th attempt with CORRECT password must still be locked out!
        locked_res = self.client.post(reverse('lmsapp:login'), {
            'userid': 'admin_test',
            'password': 'AdminPassword123',
            'usertype': 'admin'
        })
        self.assertEqual(locked_res.status_code, 200)
        self.assertIn("temporarily locked", locked_res.content.decode())

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

    @patch('lmsapp.views.send_otp_email')
    def test_admin_login_triggers_2fa(self, mock_send_email):
        mock_send_email.return_value = (True, None)

        res = self.client.post(reverse('lmsapp:login'), {
            'userid': 'admin_test',
            'password': 'AdminPassword123',
            'usertype': 'admin'
        })

        # Should redirect to 2FA verification page, NOT admin home yet!
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('lmsapp:verify_otp'), res.url)

        # adminid must NOT be set yet
        self.assertIsNone(self.client.session.get('adminid'))
        # 2fa session keys must be set
        self.assertEqual(self.client.session.get('2fa_admin_userid'), 'admin_test')
        otp = self.client.session.get('2fa_otp')
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

        # Email send called with registered email
        mock_send_email.assert_called_once_with('admin@testlibrary.com', otp)

        # GET verify_otp page renders successfully
        page = self.client.get(reverse('lmsapp:verify_otp'))
        self.assertEqual(page.status_code, 200)
        self.assertIn("Two-Factor Authentication", page.content.decode())
        self.assertIn("ad***n@testlibrary.com", page.content.decode())

    @patch('lmsapp.views.send_otp_email')
    def test_admin_otp_verification_success(self, mock_send_email):
        mock_send_email.return_value = (True, None)

        # Initiate login
        self.client.post(reverse('lmsapp:login'), {
            'userid': 'admin_test',
            'password': 'AdminPassword123',
            'usertype': 'admin'
        })
        otp = self.client.session.get('2fa_otp')

        # Submit correct OTP
        verify_res = self.client.post(reverse('lmsapp:verify_otp'), {'otp': otp})
        self.assertEqual(verify_res.status_code, 302)
        self.assertIn(reverse('adminapp:adminhome'), verify_res.url)

        # Now adminid must be set in session!
        self.assertEqual(self.client.session.get('adminid'), 'admin_test')
        # 2FA session keys should be cleaned up
        self.assertIsNone(self.client.session.get('2fa_admin_userid'))
        self.assertIsNone(self.client.session.get('2fa_otp'))

    def test_admin_otp_verification_failure(self):
        session = self.client.session
        session['2fa_admin_userid'] = 'admin_test'
        session['2fa_otp'] = '123456'
        session['2fa_otp_time'] = int(time.time())
        session['2fa_email'] = 'admin@testlibrary.com'
        session.save()

        # Submit incorrect OTP
        res = self.client.post(reverse('lmsapp:verify_otp'), {'otp': '999999'})
        self.assertEqual(res.status_code, 200)
        self.assertIn("Invalid OTP code", res.content.decode())
        self.assertIn("9 attempts remaining", res.content.decode())
        self.assertIsNone(self.client.session.get('adminid'))

    def test_admin_2fa_attempts_limit_and_lockout(self):
        # 10 failed attempts locks out 2FA and purges the session
        session = self.client.session
        session['2fa_admin_userid'] = 'admin_test'
        session['2fa_otp'] = '123456'
        session['2fa_otp_time'] = int(time.time())
        session['2fa_email'] = 'admin@testlibrary.com'
        session['2fa_attempts'] = 9  # 9 failed attempts already
        session.save()

        # 10th failed attempt
        res = self.client.post(reverse('lmsapp:verify_otp'), {'otp': '000000'})
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('lmsapp:login'), res.url)

        # 2FA session must be completely purged
        self.assertIsNone(self.client.session.get('2fa_admin_userid'))
        self.assertIsNone(self.client.session.get('2fa_otp'))

    def test_admin_otp_expiry(self):
        session = self.client.session
        session['2fa_admin_userid'] = 'admin_test'
        session['2fa_otp'] = '123456'
        # Expired 12 minutes ago (> 10 minutes)
        session['2fa_otp_time'] = int(time.time()) - 720
        session['2fa_email'] = 'admin@testlibrary.com'
        session.save()

        res = self.client.post(reverse('lmsapp:verify_otp'), {'otp': '123456'})
        self.assertEqual(res.status_code, 200)
        self.assertIn("OTP has expired", res.content.decode())
        self.assertIsNone(self.client.session.get('adminid'))

    @patch('lmsapp.views.send_otp_email')
    def test_admin_resend_otp_success(self, mock_send_email):
        mock_send_email.return_value = (True, None)

        session = self.client.session
        session['2fa_admin_userid'] = 'admin_test'
        session['2fa_otp'] = '111111'
        session['2fa_otp_time'] = int(time.time()) - 30  # Cooldown of 20s satisfied
        session['2fa_email'] = 'admin@testlibrary.com'
        session['2fa_resends'] = 0
        session.save()

        res = self.client.get(reverse('lmsapp:resend_otp'))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('lmsapp:verify_otp'), res.url)

        new_otp = self.client.session.get('2fa_otp')
        self.assertIsNotNone(new_otp)
        self.assertEqual(len(new_otp), 6)
        mock_send_email.assert_called_once_with('admin@testlibrary.com', new_otp)

    @patch('lmsapp.views.send_otp_email')
    def test_admin_2fa_resend_cooldown(self, mock_send_email):
        # When less than 20 seconds have elapsed since last OTP was sent
        session = self.client.session
        session['2fa_admin_userid'] = 'admin_test'
        session['2fa_otp'] = '111111'
        session['2fa_otp_time'] = int(time.time()) - 5  # Only 5 seconds ago!
        session['2fa_email'] = 'admin@testlibrary.com'
        session.save()

        res = self.client.get(reverse('lmsapp:resend_otp'), follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Please wait", res.content.decode())
        self.assertIn("seconds before requesting a new OTP", res.content.decode())

        # Email must NOT have been sent
        mock_send_email.assert_not_called()
        # OTP must NOT have changed
        self.assertEqual(self.client.session.get('2fa_otp'), '111111')

    @patch('lmsapp.views.send_otp_email')
    def test_admin_2fa_resend_max_session_limit(self, mock_send_email):
        session = self.client.session
        session['2fa_admin_userid'] = 'admin_test'
        session['2fa_otp'] = '111111'
        session['2fa_otp_time'] = int(time.time()) - 100
        session['2fa_email'] = 'admin@testlibrary.com'
        session['2fa_resends'] = 5  # Maximum 5 resends reached
        session.save()

        res = self.client.get(reverse('lmsapp:resend_otp'), follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Maximum OTP resend limit reached", res.content.decode())
        mock_send_email.assert_not_called()

    def test_direct_access_verify_otp_redirects_if_no_session(self):
        res = self.client.get(reverse('lmsapp:verify_otp'))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('lmsapp:login'), res.url)

