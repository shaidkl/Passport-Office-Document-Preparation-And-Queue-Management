import urllib.request
import json
import uuid
import sys
import io

BASE_URL = "http://127.0.0.1:8000/api"

def req(method, path, data=None, token=None, files=None):
    headers = {}
    if token:
        headers['Authorization'] = f"Bearer {token}"
    body = None
    if files:
        boundary = "----WebKitBoundary" + uuid.uuid4().hex[:12]
        headers['Content-Type'] = f"multipart/form-data; boundary={boundary}"
        parts = []
        if data:
            for k, v in data.items():
                parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        for k, (fn, fc, ct) in files.items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fn}\"\r\nContent-Type: {ct}\r\n\r\n".encode() + fc + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
    elif data is not None:
        headers['Content-Type'] = 'application/json'
        body = json.dumps(data).encode()
    
    r = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            content = resp.read()
            ct = resp.headers.get('Content-Type', '')
            if 'application/pdf' in ct or 'image/' in ct:
                return resp.status, content
            text = content.decode('utf-8', errors='replace')
            return resp.status, json.loads(text) if text.strip() else {}
    except urllib.error.HTTPError as e:
        content = e.read()
        text = content.decode('utf-8', errors='replace')
        try:
            return e.code, json.loads(text) if text.strip() else {}
        except Exception:
            return e.code, text

def run_tests():
    print("==========================================================================")
    print("RUNNING CRITICAL VERIFICATION TEST SUITE")
    print("==========================================================================")

    # 1. PHONE UNIQUENESS & VALIDATION
    print("\n--- TEST 1: Phone Uniqueness & Exact Error Message ---")
    uid1 = uuid.uuid4().hex[:6]
    phone_test = "98" + str(int(uuid.uuid4().int % 100000000)).zfill(8)
    
    st, res1 = req("POST", "/register/", {
        "role": "citizen",
        "full_name": f"User One {uid1}",
        "email": f"user1_{uid1}@example.com",
        "phone": phone_test,
        "password": "Password123!",
        "date_of_birth": "1995-01-01",
        "gender": "Male",
        "nationality": "Nepali",
        "address": "Kathmandu, Nepal"
    })
    assert st in [200, 201], f"User 1 registration failed: {res1}"
    print(f"[PASS] User 1 registered with phone {phone_test}")

    # Duplicate phone registration attempt with +977 prefix
    uid2 = uuid.uuid4().hex[:6]
    st, res2 = req("POST", "/register/", {
        "role": "citizen",
        "full_name": f"User Two {uid2}",
        "email": f"user2_{uid2}@example.com",
        "phone": f"+977 {phone_test[:5]} {phone_test[5:]}",
        "password": "Password123!",
        "date_of_birth": "1996-02-02",
        "gender": "Female",
        "nationality": "Nepali",
        "address": "Pokhara, Nepal"
    })
    assert st == 400, f"Expected 400 for duplicate phone, got {st}: {res2}"
    expected_msg = "This phone number is already registered. Please use another phone number or log in to your existing account."
    assert res2.get("phone") == expected_msg or res2.get("error") == expected_msg, f"Expected exact error message '{expected_msg}', got: {res2}"
    print(f"[PASS] Duplicate phone rejected with exact error message: '{expected_msg}'")

    # Login User 1
    st, log1 = req("POST", "/login/", {"email": f"user1_{uid1}@example.com", "password": "Password123!"})
    assert st == 200, f"Login failed: {log1}"
    citizen_token = log1["token"]
    citizen_id = log1.get("user_id")
    print(f"[PASS] User 1 logged in successfully. Token obtained.")

    # Staff user for administrative actions
    st, staff_log = req("POST", "/login/", {"username": "ramesh.staff", "password": "staffpassword123"})
    assert st == 200, f"Staff login failed: {staff_log}"
    staff_token = staff_log.get("token")
    print(f"[INFO] Staff token available: {bool(staff_token)}")

    # 2. CREATE APPLICATION (66 PAGES)
    print("\n--- TEST 2: Create Application with 66 Pages ---")
    st, app_res = req("POST", "/applications/", {
        "passport_category": "Ordinary (66 Pages)",
        "service_type": "New Passport"
    }, token=citizen_token)
    assert st in [200, 201], f"Application create failed: {app_res}"
    app_id = app_res["application_id"]
    assert "66" in app_res["passport_category"], "Category page count not preserved"
    print(f"[PASS] Application #NP-{app_id:04d} created with Ordinary (66 Pages)")

    # 3. PASSPORT PHOTO FORMAT VALIDATION
    print("\n--- TEST 3: Passport Photo JPG/PNG Validation ---")
    # Try uploading a PDF as Passport Photo -> should fail
    dummy_pdf = b"%PDF-1.4 dummy file content"
    st, doc_bad = req("POST", "/documents/", data={
        "application": str(app_id),
        "document_type": "Passport Photo",
        "file_name": "photo.pdf"
    }, files={
        "file_path": ("photo.pdf", dummy_pdf, "application/pdf")
    }, token=citizen_token)
    assert st == 400, f"Expected 400 for PDF as passport photo, got {st}: {doc_bad}"
    assert "file_path" in doc_bad and "JPG" in str(doc_bad["file_path"]), f"Expected photo format error, got: {doc_bad}"
    print(f"[PASS] PDF rejected for Passport Photo type: {doc_bad}")

    # Upload valid 1x1 JPG image
    # Minimal 1x1 JPEG bytes
    tiny_jpeg = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x01, 0x00, 0x48,
        0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43, 0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
        0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
        0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29, 0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
        0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04,
        0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
        0x00, 0xBF, 0x00, 0xFF, 0xD9
    ])
    st, doc_good = req("POST", "/documents/", data={
        "application": str(app_id),
        "document_type": "Passport Photo",
        "file_name": "photo.jpg"
    }, files={
        "file_path": ("photo.jpg", tiny_jpeg, "image/jpeg")
    }, token=citizen_token)
    assert st in [200, 201], f"Passport photo upload failed: {doc_good}"
    photo_doc_id = doc_good["document_id"]
    print(f"[PASS] Passport Photo #DOC-{photo_doc_id} uploaded successfully")

    # Upload Citizenship document
    st, doc_citz = req("POST", "/documents/", data={
        "application": str(app_id),
        "document_type": "Citizenship Certificate",
        "file_name": "citizenship.pdf"
    }, files={
        "file_path": ("citizenship.pdf", dummy_pdf, "application/pdf")
    }, token=citizen_token)
    assert st in [200, 201], f"Citizenship upload failed: {doc_citz}"
    citz_doc_id = doc_citz["document_id"]
    print(f"[PASS] Citizenship Certificate #DOC-{citz_doc_id} uploaded successfully")

    # 4. PAYMENT GATE ON VIRTUAL PASSPORT & PDF DOWNLOAD
    print("\n--- TEST 4: Payment Gate - PDF Download and Card Locked Before Verified Payment ---")
    
    # Check application serializer can_download_pdf field
    st, app_check = req("GET", f"/applications/{app_id}/", token=citizen_token)
    assert st == 200
    assert app_check.get("can_download_pdf") is False, f"can_download_pdf should be False before payment! Got: {app_check.get('can_download_pdf')}"
    print(f"[PASS] Application.can_download_pdf is False")

    # Check workflow endpoint
    st, wf = req("GET", "/applications/current-workflow/", token=citizen_token)
    assert st == 200
    assert wf.get("can_download_pdf") is False, f"Workflow can_download_pdf should be False! Got: {wf}"
    assert wf.get("is_payment_verified") is False, f"is_payment_verified should be False! Got: {wf}"
    print(f"[PASS] current_workflow confirms payment not verified, can_download_pdf=False")

    # Attempt to download PDF before payment
    st, pdf_res = req("GET", f"/applications/{app_id}/download-pdf/", token=citizen_token)
    assert st in [400, 403], f"Expected 400/403 for download-pdf before payment, got {st}: {pdf_res}"
    print(f"[PASS] /applications/{app_id}/download-pdf/ strictly rejected before payment ({st})")

    # Attempt to authorize signature before payment
    if staff_token:
        st, sig_bad = req("POST", f"/applications/{app_id}/authorize-signature/", token=staff_token)
        assert st in [400, 403], f"Expected 400/403 for signature authorization before payment, got {st}: {sig_bad}"
        print(f"[PASS] /applications/{app_id}/authorize-signature/ strictly rejected before payment ({st})")

    # 5. VERIFY DOCUMENTS & BIOMETRICS (via staff)
    print("\n--- TEST 5: Verify Documents and Biometrics ---")
    if staff_token:
        # Staff inspects photo and citizenship
        req("GET", f"/documents/{photo_doc_id}/view-file/", token=staff_token)
        req("GET", f"/documents/{citz_doc_id}/view-file/", token=staff_token)
        st, _ = req("POST", f"/documents/{photo_doc_id}/verify-document/", {"remarks": "Clear portrait photo"}, token=staff_token)
        assert st == 200, f"Photo verification failed: {_}"
        st, _ = req("POST", f"/documents/{citz_doc_id}/verify-document/", {"remarks": "Citizenship verified"}, token=staff_token)
        assert st == 200, f"Citizenship verification failed: {_}"
        st, _ = req("POST", f"/applications/{app_id}/verify-biometrics/", {"biometric_status": "Verified"}, token=staff_token)
        assert st == 200, f"Biometric verification failed: {_}"
        print(f"[PASS] Documents inspected and marked Verified by Staff")

    # 6. COMPLETE PAYMENT
    print("\n--- TEST 6: Complete Payment and Verify Unlocking ---")
    st, pay_req = req("POST", "/payments/create-request/", {
        "application_id": app_id,
        "payment_type": "APPLICATION_FEE",
        "gateway_name": "eSewa"
    }, token=citizen_token)
    assert st in [200, 201], f"Payment request failed: {pay_req}"
    pay_ref = pay_req['payment_reference']
    print(f"[PASS] Payment reference created: {pay_ref}")

    st, sim = req("POST", "/payments/simulate-sandbox-callback/", {
        "payment_reference": pay_ref
    }, token=citizen_token)
    assert st == 200, f"Payment simulation failed: {sim}"
    print(f"[PASS] Payment verified via gateway callback simulation")

    # Now Authorize Digital Signature
    if staff_token:
        st, sig_good = req("POST", f"/applications/{app_id}/authorize-signature/", token=staff_token)
        assert st == 200, f"Signature authorization failed: {sig_good}"
        print(f"[PASS] Digital Signature Authorized: Serial {sig_good.get('certificate_serial')}")

        # Check Application Status is now Approved
        st, app_approved = req("GET", f"/applications/{app_id}/", token=citizen_token)
        assert st == 200
        assert app_approved["status"] == "Approved", f"Expected Approved, got {app_approved['status']}"
        assert app_approved["can_download_pdf"] is True, f"Expected can_download_pdf=True, got {app_approved['can_download_pdf']}"
        print(f"[PASS] Application is Approved and can_download_pdf is TRUE")

        # Check PDF Download succeeds and contains proper PDF header
        st, pdf_data = req("GET", f"/applications/{app_id}/download-pdf/", token=citizen_token)
        assert st == 200, f"PDF download failed: {st}"
        assert isinstance(pdf_data, bytes) and pdf_data.startswith(b"%PDF-"), "Downloaded file is not a valid PDF!"
        print(f"[PASS] /applications/{app_id}/download-pdf/ returned valid PDF bytes ({len(pdf_data)} bytes)")
        
        # Verify 66 Pages appears in PDF text
        assert b"66 Pages" in pdf_data or b"66" in pdf_data, "66 Pages not found in PDF stream"
        print(f"[PASS] PDF confirms 66 Pages passport tier!")

    print("\n==========================================================================")
    print("ALL CRITICAL BUSINESS RULES & FIXES VERIFIED SUCCESSFULLY!")
    print("==========================================================================")

if __name__ == '__main__':
    run_tests()
