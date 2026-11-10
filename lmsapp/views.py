from django.shortcuts import render, redirect, reverse
from django.db import transaction
from django.contrib import messages
from datetime import date
import time
from .models import Enquiry, Student, Login
from adminapp.models import Program, Branch, Year
from .email_service import generate_otp, mask_email, get_admin_email, send_otp_email
from .security import get_client_ip, SecurityRateLimiter, validate_registration_inputs

def index(request):
    return render(request, "index.html")

def aboutus(request):
    return render(request, "aboutus.html")

def registration(request):
    ip = get_client_ip(request)

    if request.method == "POST":
        # 1. Rate limiting: 30 registration attempts per 5 minutes per IP
        is_limited, retry_after = SecurityRateLimiter.check_rate_limit(
            f"reg_ip:{ip}", max_requests=30, window_seconds=300
        )
        if is_limited:
            messages.error(request, f"Too many registration requests. Please try again after {retry_after} seconds.")
            program = Program.objects.all()
            branch = Branch.objects.all()
            year = Year.objects.all()
            return render(request, "registration.html", locals())

        # 2. Server-side input validation
        is_valid, err_msg = validate_registration_inputs(request.POST)
        if not is_valid:
            messages.error(request, err_msg)
            program = Program.objects.all()
            branch = Branch.objects.all()
            year = Year.objects.all()
            return render(request, "registration.html", locals())

        rollno = request.POST.get('rollno', '').strip()
        password = request.POST.get('password', '')

        # 3. Prevent duplicate account collision
        if Login.objects.filter(userid=rollno).exists() or Student.objects.filter(rollno=rollno).exists():
            messages.error(request, f"Student with Roll Number {rollno} already exists.")
            program = Program.objects.all()
            branch = Branch.objects.all()
            year = Year.objects.all()
            return render(request, "registration.html", locals())

        # 4. Resolve foreign keys
        program_val = request.POST.get('program')
        branch_val = request.POST.get('branch')
        year_val = request.POST.get('year')

        program_obj = (
            Program.objects.filter(id=program_val).first()
            if str(program_val).isdigit()
            else Program.objects.filter(program=program_val).first()
        )
        branch_obj = (
            Branch.objects.filter(id=branch_val).first()
            if str(branch_val).isdigit()
            else Branch.objects.filter(branch=branch_val).first()
        )
        year_obj = (
            Year.objects.filter(id=year_val).first()
            if str(year_val).isdigit()
            else Year.objects.filter(year=year_val).first()
        )

        if not program_obj or not branch_obj or not year_obj:
            messages.error(request, "Invalid Program, Branch, or Year selected.")
            program = Program.objects.all()
            branch = Branch.objects.all()
            year = Year.objects.all()
            return render(request, "registration.html", locals())

        # 5. Create Login and Student atomically
        try:
            with transaction.atomic():
                log = Login(userid=rollno, password=password, usertype='student', status='false')
                log.save()

                stu = Student(
                    login=log,
                    rollno=rollno,
                    name=request.POST.get('name', '').strip(),
                    fname=request.POST.get('fname', '').strip(),
                    mname=request.POST.get('mname', '').strip(),
                    gender=request.POST.get('gender', '').strip(),
                    address=request.POST.get('address', '').strip(),
                    program=program_obj,
                    branch=branch_obj,
                    year=year_obj,
                    contactno=request.POST.get('contactno', '').strip(),
                    emailaddress=request.POST.get('emailaddress', '').strip(),
                    regdate=date.today(),
                )
                stu.save()

            messages.success(request, "Student Registration Is Done")
        except Exception:
            messages.error(request, "An error occurred during registration. Please try again.")

    program = Program.objects.all()
    branch = Branch.objects.all()
    year = Year.objects.all()

    return render(request, "registration.html", locals())

def login(request):
    ip = get_client_ip(request)

    if request.method == "POST":
        userid = request.POST.get('userid', '').strip()
        password = request.POST.get('password', '')
        usertype = request.POST.get('usertype', '').strip()

        # 1. Check IP-level lockout
        is_ip_locked, ip_rem = SecurityRateLimiter.is_locked(f"ip:{ip}")
        if is_ip_locked:
            messages.error(request, f"Too many failed login attempts from your IP. Access is temporarily locked for {ip_rem} seconds.")
            return render(request, "login.html")

        # 2. Check User-level lockout
        if userid:
            is_user_locked, user_rem = SecurityRateLimiter.is_locked(f"user:{userid}")
            if is_user_locked:
                messages.error(request, f"This account is temporarily locked due to multiple failed login attempts. Please try again in {user_rem} seconds.")
                return render(request, "login.html")

        # 3. Retrieve user record
        user_record = Login.objects.filter(userid=userid, usertype=usertype).first()

        # 4. Compare passwords using constant-time comparison
        if user_record and SecurityRateLimiter.secure_compare(user_record.password, password):
            # Clear failure counters on successful authentication
            SecurityRateLimiter.clear_failures(f"ip:{ip}")
            if userid:
                SecurityRateLimiter.clear_failures(f"user:{userid}")

            if user_record.usertype == "student":
                # Cycle session key to prevent session fixation
                request.session.cycle_key()
                request.session['rollno'] = userid
                return redirect(reverse('studentapp:studenthome'))

            elif user_record.usertype == "admin":
                # Check 2FA lockout for this admin account
                is_otp_locked, otp_lock_rem = SecurityRateLimiter.is_locked(f"otp_lock:{userid}")
                if is_otp_locked:
                    messages.error(request, f"Admin 2FA is temporarily locked due to failed attempts. Please wait {otp_lock_rem} seconds.")
                    return render(request, "login.html")

                # Rate limit OTP generation per IP (max 15 per 10 mins)
                is_limited, retry_after = SecurityRateLimiter.check_rate_limit(f"otp_send_ip:{ip}", max_requests=15, window_seconds=600)
                if is_limited:
                    messages.error(request, f"Too many OTP dispatch requests. Please wait {retry_after} seconds.")
                    return render(request, "login.html")

                # Prepare 2FA session with fixation protection
                request.session.cycle_key()
                admin_email = get_admin_email(userid)
                otp = generate_otp(6)
                request.session['2fa_admin_userid'] = userid
                request.session['2fa_otp'] = otp
                request.session['2fa_otp_time'] = int(time.time())
                request.session['2fa_email'] = admin_email
                request.session['2fa_attempts'] = 0
                request.session['2fa_resends'] = 0

                success, err = send_otp_email(admin_email, otp)
                masked = mask_email(admin_email)
                if success:
                    messages.success(request, f"A 6-digit OTP has been sent to your registered email ({masked}).")
                else:
                    messages.warning(request, f"OTP generated. Notice: Email sending failed ({err}).")
                return redirect(reverse('lmsapp:verify_otp'))
            else:
                messages.error(request, 'Invalid Userid or Password')
        else:
            # Record failed attempt: 10 attempts for user, 30 for shared IP, 60s cooldown
            ip_locked, ip_fails, ip_rem = SecurityRateLimiter.record_failure(f"ip:{ip}", max_failures=30, lockout_seconds=60)
            user_locked = False
            user_fails = 0
            if userid:
                user_locked, user_fails, user_rem = SecurityRateLimiter.record_failure(f"user:{userid}", max_failures=10, lockout_seconds=60)

            if ip_locked or user_locked:
                messages.error(request, "Too many failed login attempts. Please wait 1 minute before trying again.")
            else:
                remaining = max(1, 10 - user_fails if userid else 30 - ip_fails)
                messages.error(request, f"Invalid Userid or Password. ({remaining} attempt{'s' if remaining > 1 else ''} remaining)")

    return render(request, "login.html")

def verify_otp(request):
    if not request.session.get('2fa_admin_userid'):
        messages.error(request, "Session expired or invalid login attempt. Please log in again.")
        return redirect('lmsapp:login')

    ip = get_client_ip(request)
    userid = request.session['2fa_admin_userid']
    stored_otp = request.session.get('2fa_otp')
    otp_time = request.session.get('2fa_otp_time', 0)
    email = request.session.get('2fa_email', '')
    masked_email = mask_email(email)

    # 1. Check if user is locked out from 2FA
    is_locked, remaining_lock = SecurityRateLimiter.is_locked(f"otp_lock:{userid}")
    if is_locked:
        for key in ['2fa_admin_userid', '2fa_otp', '2fa_otp_time', '2fa_email', '2fa_attempts', '2fa_resends']:
            request.session.pop(key, None)
        messages.error(request, f"2FA verification is locked ({remaining_lock}s remaining). Please log in again later.")
        return redirect('lmsapp:login')

    if request.method == "POST":
        # 2. Rate limit verification submission per IP (max 30 requests per minute)
        is_limited, retry_after = SecurityRateLimiter.check_rate_limit(f"otp_verify_ip:{ip}", max_requests=30, window_seconds=60)
        if is_limited:
            messages.error(request, f"Too many verification attempts. Please wait {retry_after} seconds.")
            return render(request, "verify_otp.html", {'masked_email': masked_email})

        entered_otp = request.POST.get('otp', '').strip()

        # 3. Check OTP expiry (10 minutes = 600 seconds)
        if time.time() - otp_time > 600:
            messages.error(request, "OTP has expired. Please click 'Resend OTP' to get a new code.")
            return render(request, "verify_otp.html", {'masked_email': masked_email, 'expired': True})

        # 4. Constant-time comparison
        if SecurityRateLimiter.secure_compare(entered_otp, stored_otp):
            # Clean up 2FA temporary session
            for key in ['2fa_admin_userid', '2fa_otp', '2fa_otp_time', '2fa_email', '2fa_attempts', '2fa_resends']:
                request.session.pop(key, None)

            # Clear failure counters and lockouts
            SecurityRateLimiter.clear_failures(f"otp_fails:{userid}")
            SecurityRateLimiter.clear_failures(f"otp_lock:{userid}")

            # Cycle session key to prevent session fixation
            request.session.cycle_key()
            request.session['adminid'] = userid
            messages.success(request, "2FA verification successful. Welcome to Admin Dashboard!")
            return redirect(reverse('adminapp:adminhome'))
        else:
            # Failed OTP attempt
            attempts = request.session.get('2fa_attempts', 0) + 1
            request.session['2fa_attempts'] = attempts

            # Track in cache-backed limiter as well: 10 attempts allowed, 120s cooldown
            is_locked, fails, lockout_time = SecurityRateLimiter.record_failure(f"otp_fails:{userid}", max_failures=10, lockout_seconds=120)

            if attempts >= 10 or is_locked:
                # Trigger 2-minute cooldown and purge session
                SecurityRateLimiter.record_failure(f"otp_lock:{userid}", max_failures=1, lockout_seconds=120)
                for key in ['2fa_admin_userid', '2fa_otp', '2fa_otp_time', '2fa_email', '2fa_attempts', '2fa_resends']:
                    request.session.pop(key, None)
                messages.error(request, "Maximum OTP verification attempts exceeded (10/10). Please try logging in again after 2 minutes.")
                return redirect('lmsapp:login')
            else:
                remaining_attempts = 10 - attempts
                messages.error(request, f"Invalid OTP code. {remaining_attempts} attempt{'s' if remaining_attempts > 1 else ''} remaining.")
                return render(request, "verify_otp.html", {'masked_email': masked_email})

    return render(request, "verify_otp.html", {'masked_email': masked_email})

def resend_otp(request):
    if not request.session.get('2fa_admin_userid'):
        messages.error(request, "Please log in first.")
        return redirect('lmsapp:login')

    ip = get_client_ip(request)
    userid = request.session['2fa_admin_userid']

    # 1. Check if 2FA is locked
    is_locked, remaining_lock = SecurityRateLimiter.is_locked(f"otp_lock:{userid}")
    if is_locked:
        messages.error(request, f"2FA is locked due to excessive failed attempts ({remaining_lock}s remaining).")
        return redirect('lmsapp:login')

    # 2. Relaxed 20-second cooldown between OTP sends
    last_otp_time = request.session.get('2fa_otp_time', 0)
    elapsed = int(time.time()) - last_otp_time
    COOLDOWN_SECONDS = 20
    if elapsed < COOLDOWN_SECONDS:
        wait_seconds = COOLDOWN_SECONDS - elapsed
        messages.warning(request, f"Please wait {wait_seconds} seconds before requesting a new OTP.")
        return redirect('lmsapp:verify_otp')

    # 3. Maximum 5 resends per session
    resends = request.session.get('2fa_resends', 0)
    if resends >= 5:
        messages.error(request, "Maximum OTP resend limit reached for this session (5/5). Please return to login.")
        return redirect('lmsapp:verify_otp')

    # 4. IP rate limit (max 15 resends per 10 minutes)
    is_limited, retry_after = SecurityRateLimiter.check_rate_limit(f"otp_resend_ip:{ip}", max_requests=15, window_seconds=600)
    if is_limited:
        messages.error(request, f"Too many OTP resend requests from your network. Please wait {retry_after} seconds.")
        return redirect('lmsapp:verify_otp')

    # 5. Generate and send fresh OTP
    email = request.session.get('2fa_email') or get_admin_email(userid)
    new_otp = generate_otp(6)

    request.session['2fa_otp'] = new_otp
    request.session['2fa_otp_time'] = int(time.time())
    request.session['2fa_resends'] = resends + 1
    request.session['2fa_attempts'] = 0  # Reset failed attempt count for new OTP

    success, err = send_otp_email(email, new_otp)
    masked = mask_email(email)
    if success:
        messages.success(request, f"A new OTP has been sent to {masked}. (Resend {resends + 1}/5)")
    else:
        messages.warning(request, f"New OTP generated, but email sending failed: {err}")

    return redirect('lmsapp:verify_otp')

def contactus(request):
    ip = get_client_ip(request)
    if request.method == "POST":
        # Rate limit contact submissions: max 20 per 5 minutes per IP
        is_limited, retry_after = SecurityRateLimiter.check_rate_limit(f"contact_ip:{ip}", max_requests=20, window_seconds=300)
        if is_limited:
            messages.error(request, f"Too many enquiries submitted. Please try again after {retry_after} seconds.")
            return render(request, "contactus.html")

        name = request.POST.get('name', '').strip()
        contactno = request.POST.get('contactno', '').strip()
        emailaddress = request.POST.get('emailaddress', '').strip()
        enquirytext = request.POST.get('enquirytext', '').strip()

        if not name or not contactno or not emailaddress or not enquirytext:
            messages.error(request, "Please fill in all required enquiry fields.")
            return render(request, "contactus.html")

        enq = Enquiry(
            name=name,
            gender=request.POST.get('gender', 'male'),
            address=request.POST.get('Address', request.POST.get('address', '')),
            contactno=contactno,
            emailaddress=emailaddress,
            enquirytext=enquirytext,
            enquirydate=date.today(),
        )
        enq.save()
        messages.success(request, 'Your enquiry is submitted')
    return render(request, "contactus.html")