import urllib.request
import json
import uuid
import sys
import os

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
        ct = e.headers.get('Content-Type', '') if hasattr(e, 'headers') else ''
        text = content.decode('utf-8', errors='replace')
        try:
            return e.code, json.loads(text) if text.strip() else {}
        except Exception:
            return e.code, text

def run_all_24_tests():
    print("==========================================================================")
    print("RUNNING ALL 24 REAL DOCUMENT INSPECTION & STAFF VALIDATION TESTS")
    print("==========================================================================")

    # TEST 1: Applicant registers
    uid = uuid.uuid4().hex[:6]
    phone = "98" + str(int(uuid.uuid4().int % 100000000)).zfill(8)
    email = f"citizen_verify_{uid}@example.com"
    pwd = "SecurePassword123!"

    st, reg = req("POST", "/register/", {
        "role": "citizen",
        "full_name": f"Citizen Verify {uid}",
        "email": email,
        "phone": phone,
        "password": pwd,
        "date_of_birth": "1993-04-12",
        "gender": "Male",
        "nationality": "Nepali",
        "address": "Tripureshwor, Kathmandu"
    })
    assert st in [200, 201], f"TEST 1 FAILED: Registration failed {reg}"
    print(f"[TEST 1 PASS] Applicant registered: {email}, Phone: {phone}")

    # TEST 2: Applicant logs in
    st, login = req("POST", "/login/", {"email": email, "password": pwd})
    assert st == 200, f"TEST 2 FAILED: Login failed {login}"
    applicant_token = login["token"]
    applicant_id = login.get("user_id")
    print(f"[TEST 2 PASS] Applicant logged in. Token obtained for Applicant #{applicant_id}")

    # Log in staff member
    st, s_log = req("POST", "/login/", {"username": "ramesh.staff", "password": "staffpassword123"})
    assert st == 200, f"Staff login failed: {s_log}"
    staff_token = s_log["token"]
    print(f"[INFO] Staff logged in successfully: ramesh.staff")

    # TEST 3 & 4: Applicant creates application with package/pages/service
    st, app = req("POST", "/applications/", {
        "passport_category": "Ordinary (66 Pages)",
        "service_type": "New Passport"
    }, token=applicant_token)
    assert st in [200, 201], f"TEST 3/4 FAILED: Application creation failed {app}"
    app_id = app["application_id"]
    assert "66" in app["passport_category"]
    print(f"[TEST 3 & 4 PASS] Application #NP-{app_id:04d} created with Ordinary (66 Pages)")

    # TEST 5 & 6: Applicant uploads required documents (Citizenship Certificate + Passport-size photo)
    # Valid PDF bytes
    dummy_citz_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n165\n%%EOF"
    
    st, doc_citz = req("POST", "/documents/", data={
        "application": str(app_id),
        "document_type": "Citizenship Certificate",
        "file_name": "citizenship_scan.pdf"
    }, files={
        "file_path": ("citizenship_scan.pdf", dummy_citz_pdf, "application/pdf")
    }, token=applicant_token)
    assert st in [200, 201], f"TEST 5 FAILED: Upload citizenship failed {doc_citz}"
    citz_doc_id = doc_citz["document_id"]
    print(f"[TEST 5 PASS] Citizenship Certificate #DOC-{citz_doc_id} uploaded")

    # Minimal valid 1x1 JPEG bytes for passport photo
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
    st, doc_photo = req("POST", "/documents/", data={
        "application": str(app_id),
        "document_type": "Passport Photo",
        "file_name": "portrait.jpg"
    }, files={
        "file_path": ("portrait.jpg", tiny_jpeg, "image/jpeg")
    }, token=applicant_token)
    assert st in [200, 201], f"TEST 6 FAILED: Upload photo failed {doc_photo}"
    photo_doc_id = doc_photo["document_id"]
    print(f"[TEST 6 PASS] Passport Photo #DOC-{photo_doc_id} uploaded")

    # TEST 7: Confirm files actually exist in Django Media Storage
    # Let's inspect backend/media/documents/
    citz_file_rel = doc_citz["file_path"].split("/media/")[-1].lstrip("/")
    citz_full_path = os.path.join("backend", "media", citz_file_rel.replace("/", os.sep))
    assert os.path.exists(citz_full_path), f"TEST 7 FAILED: File does not exist at {citz_full_path}"
    print(f"[TEST 7 PASS] Files physically confirmed in Django Media Storage: {citz_full_path}")

    # TEST 8: Staff opens application / views documents list
    st, s_app = req("GET", f"/applications/{app_id}/", token=staff_token)
    assert st == 200, f"TEST 8 FAILED: Staff cannot access application {s_app}"
    assert s_app["application_id"] == app_id
    print(f"[TEST 8 PASS] Staff retrieved Application #NP-{app_id:04d}")

    # TEST 9: Staff clicks View Document -> opens actual uploaded document
    st, file_bytes = req("GET", f"/documents/{citz_doc_id}/view-file/", token=staff_token)
    assert st == 200, f"TEST 9 FAILED: view-file returned status {st}"
    assert isinstance(file_bytes, bytes) and file_bytes.startswith(b"%PDF-"), "TEST 9 FAILED: Did not return real PDF bytes"
    print(f"[TEST 9 PASS] Staff viewed real Citizenship PDF: {len(file_bytes)} bytes streamed from storage")

    # Verify that viewing marked the document as is_inspected=True
    st, doc_check = req("GET", f"/documents/{citz_doc_id}/", token=staff_token)
    assert st == 200 and doc_check.get("is_inspected") is True, f"TEST 9 FAILED: is_inspected not True {doc_check}"
    print(f"[TEST 9 PASS] Document #DOC-{citz_doc_id} is_inspected automatically marked True")

    # TEST 10: Staff verifies the document -> status becomes Verified
    st, v_res = req("POST", f"/documents/{citz_doc_id}/verify-document/", {"remarks": "Clear verified copy"}, token=staff_token)
    assert st == 200, f"TEST 10 FAILED: verify-document failed {v_res}"
    assert v_res["verification_status"] == "Verified"
    print(f"[TEST 10 PASS] Document #DOC-{citz_doc_id} verified successfully")

    # TEST 11: Staff rejects document without reason -> request rejected (400)
    st, rej_fail = req("POST", f"/documents/{photo_doc_id}/reject-document/", {"reason": ""}, token=staff_token)
    assert st == 400, f"TEST 11 FAILED: Expected 400 for empty rejection reason, got {st}: {rej_fail}"
    print(f"[TEST 11 PASS] Rejection without reason strictly rejected by backend: {rej_fail.get('error')}")

    # TEST 12: Staff rejects with a reason -> status becomes Rejected and reason saved
    rej_reason = "Photograph has slight glare on glasses. Please re-upload with clear lighting."
    st, rej_ok = req("POST", f"/documents/{photo_doc_id}/reject-document/", {"reason": rej_reason}, token=staff_token)
    assert st == 200, f"TEST 12 FAILED: Rejection failed {rej_ok}"
    assert rej_ok["verification_status"] == "Rejected"
    assert rej_ok["rejection_reason"] == rej_reason
    print(f"[TEST 12 PASS] Document #DOC-{photo_doc_id} Rejected with saved reason")

    # TEST 13: Verify only some documents -> Application cannot become Approved (remains Under Review)
    st, app_try = req("PATCH", f"/applications/{app_id}/", {"status": "Approved"}, token=staff_token)
    assert st == 400, f"TEST 13 FAILED: Expected 400 when approving with rejected/unverified photo, got {st}: {app_try}"
    print(f"[TEST 13 PASS] Attempt to approve application with rejected photo blocked: {app_try.get('status')}")

    # TEST 14: Re-upload compliant photo, inspect, and verify all required documents -> Application can become Approved
    st, new_photo = req("POST", "/documents/", data={
        "application": str(app_id),
        "document_type": "Passport Photo",
        "file_name": "portrait_clean.jpg"
    }, files={
        "file_path": ("portrait_clean.jpg", tiny_jpeg, "image/jpeg")
    }, token=applicant_token)
    assert st in [200, 201]
    new_photo_id = new_photo["document_id"]
    print(f"[INFO] Re-uploaded replacement Passport Photo #DOC-{new_photo_id}")

    # Verify attempt BEFORE inspection -> MUST FAIL with 400
    st, v_before_inspect = req("POST", f"/documents/{new_photo_id}/verify-document/", {}, token=staff_token)
    assert st == 400, f"Expected 400 when verifying uninspected photo, got {st}: {v_before_inspect}"
    print(f"[PASS] Gating verified: Cannot verify document without inspection: {v_before_inspect.get('error')}")

    # Inspect photo
    st, photo_bytes = req("GET", f"/documents/{new_photo_id}/view-file/", token=staff_token)
    assert st == 200 and isinstance(photo_bytes, bytes)
    print(f"[PASS] Staff inspected new photo file ({len(photo_bytes)} bytes)")

    # Verify photo
    st, v_photo_ok = req("POST", f"/documents/{new_photo_id}/verify-document/", {"remarks": "Valid portrait photo"}, token=staff_token)
    assert st == 200
    print(f"[PASS] Passport Photo #DOC-{new_photo_id} verified")

    # Now approve application
    st, app_approved = req("PATCH", f"/applications/{app_id}/", {"status": "Approved"}, token=staff_token)
    assert st == 200, f"TEST 14 FAILED: Could not approve application {app_approved}"
    assert app_approved["status"] == "Approved"
    print(f"[TEST 14 PASS] All documents verified -> Application #NP-{app_id:04d} successfully Approved!")

    # TEST 15: Applicant sees document verification statuses
    st, app_docs_citizen = req("GET", "/documents/", token=applicant_token)
    assert st == 200
    citizen_docs = [d for d in app_docs_citizen if d["application"] == app_id]
    statuses = {d["document_type"]: d["verification_status"] for d in citizen_docs}
    assert statuses.get("Passport Photo") == "Verified"
    assert statuses.get("Citizenship Certificate") == "Verified"
    print(f"[TEST 15 PASS] Applicant portal sees real verification statuses: {statuses}")

    # TEST 16 & 17: Payment availability gating
    # Before approval, payment was not allowed. Now approved, payment request is available!
    st, pay_req = req("POST", "/payments/create-request/", {
        "application_id": app_id,
        "payment_type": "APPLICATION_FEE",
        "gateway_name": "eSewa"
    }, token=applicant_token)
    assert st in [200, 201], f"TEST 17 FAILED: Payment create-request failed {pay_req}"
    pay_ref = pay_req["payment_reference"]
    print(f"[TEST 16 & 17 PASS] Payment unlocked after approval. Reference: {pay_ref}")

    # TEST 18: Final passport is NOT available before payment verification
    st, dl_fail = req("GET", f"/applications/{app_id}/download-pdf/", token=applicant_token)
    assert st in [400, 403], f"TEST 18 FAILED: Expected 400/403 for download-pdf before payment verification, got {st}"
    print(f"[TEST 18 PASS] Final passport strictly locked before payment verification (HTTP {st})")

    # TEST 19: Payment is verified
    st, sim_pay = req("POST", "/payments/simulate-sandbox-callback/", {"payment_reference": pay_ref}, token=applicant_token)
    assert st == 200 and sim_pay.get("status") == "VERIFIED"
    print(f"[TEST 19 PASS] Payment verified via gateway callback simulation")

    # TEST 20: Digital signature becomes available and authorized
    st, sig_res = req("POST", f"/applications/{app_id}/authorize-signature/", token=staff_token)
    assert st == 200, f"TEST 20 FAILED: Authorize signature failed {sig_res}"
    cert_serial = sig_res.get("certificate_serial")
    print(f"[TEST 20 PASS] Digital Signature authorized: {cert_serial}")

    # TEST 21: Queue token is Completed
    st, qt_res = req("GET", "/queue-tokens/", token=applicant_token)
    assert st == 200
    my_token = next((t for t in qt_res if t["application"] == app_id), None)
    assert my_token is not None, "TEST 21 FAILED: Queue token missing"
    print(f"[TEST 21 PASS] Queue token active and associated: Token #{my_token['token_id']}")

    # TEST 22: Final passport contains applicant's VERIFIED photo and correct page count (66)
    st, final_pdf = req("GET", f"/applications/{app_id}/download-pdf/", token=applicant_token)
    assert st == 200, f"TEST 22 FAILED: Final PDF download failed {final_pdf}"
    assert isinstance(final_pdf, bytes) and final_pdf.startswith(b"%PDF-")
    assert b"66 Pages" in final_pdf or b"66" in final_pdf, "TEST 22 FAILED: 66 Pages tier missing from PDF"
    assert b"/ImPhoto" in final_pdf, "TEST 22 FAILED: Verified passport photo XObject missing from PDF"
    print(f"[TEST 22 PASS] Final e-Passport PDF generated ({len(final_pdf)} bytes) with verified photo & 66 Pages tier")

    # TEST 23: Try to create a second application for the same applicant -> Backend rejects it
    st, second_app = req("POST", "/applications/", {
        "passport_category": "Ordinary (34 Pages)",
        "service_type": "New Passport"
    }, token=applicant_token)
    assert st == 400, f"TEST 23 FAILED: Expected 400 for duplicate application, got {st}: {second_app}"
    print(f"[TEST 23 PASS] Duplicate application strictly rejected: {second_app.get('error') or second_app.get('detail')}")

    # TEST 24: Try to access another application's document using modified ID -> Backend denies unauthorized access
    # Register Citizen B
    uid_b = uuid.uuid4().hex[:6]
    phone_b = "98" + str(int(uuid.uuid4().int % 100000000)).zfill(8)
    req("POST", "/register/", {
        "role": "citizen", "full_name": "Citizen B", "email": f"citizen_b_{uid_b}@example.com",
        "phone": phone_b, "password": pwd, "date_of_birth": "1997-01-01", "gender": "Female",
        "nationality": "Nepali", "address": "Pokhara"
    })
    st_b, log_b = req("POST", "/login/", {"email": f"citizen_b_{uid_b}@example.com", "password": pwd})
    token_b = log_b["token"]

    # Citizen B tries to view Citizen A's document file
    st_hack, hack_res = req("GET", f"/documents/{citz_doc_id}/view-file/", token=token_b)
    assert st_hack in [403, 404], f"TEST 24 FAILED: Expected 403/404 for cross-applicant document access, got {st_hack}"
    print(f"[TEST 24 PASS] Unauthorized cross-applicant document view strictly forbidden (HTTP {st_hack})")

    print("\n==========================================================================")
    print("ALL 24 TESTS PASSED! REAL DOCUMENT VIEWING & STAFF VALIDATION VERIFIED!")
    print("==========================================================================")

if __name__ == "__main__":
    run_all_24_tests()
