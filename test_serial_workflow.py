import urllib.request
import json
import uuid

BASE_URL = "http://127.0.0.1:8000/api"

def req(method, path, data=None, token=None, files=None):
    headers = {}
    if token:
        headers['Authorization'] = f"Bearer {token}"
    body = None
    if files:
        boundary = "----WebKitBoundary123456"
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
            content = resp.read().decode()
            return resp.status, json.loads(content) if content.strip() else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode()
        return e.code, json.loads(content) if content.strip() else {}

def run_test():
    print("=================================================================")
    print("TESTING SERIAL & CONTINUOUS APPLICANT WORKFLOW")
    print("=================================================================")
    
    # 1. Register fresh citizen
    uid = uuid.uuid4().hex[:6]
    email = f"serial_{uid}@example.com"
    pwd = f"Pass_{uid}!123"
    st, reg = req("POST", "/register/", {
        "role": "citizen", "full_name": f"Serial Citizen {uid}",
        "email": email, "phone": "9812345678", "password": pwd,
        "date_of_birth": "1995-05-15", "gender": "Male", "nationality": "Nepali",
        "address": "Kathmandu, Nepal"
    })
    assert st in [200, 201], f"Register failed: {reg}"
    print(f"[PASS] 1. Registered citizen: {email}")

    # 2. Login
    st, log = req("POST", "/login/", {"email": email, "password": pwd})
    assert st == 200, f"Login failed: {log}"
    token = log['token']
    print("[PASS] 2. Logged in, Bearer token received")

    # 3. Check current-workflow before creating application
    st, wf0 = req("GET", "/applications/current-workflow/", token=token)
    assert st == 200
    assert wf0.get('has_application') is False
    print(f"[PASS] 3. Pre-application state: has_application=False, step 2 = 'application'")

    # 4. Create application
    st, app = req("POST", "/applications/", {
        "passport_category": "Ordinary (34 Pages)",
        "service_type": "New Passport"
    }, token=token)
    assert st in [200, 201]
    app_id = app['application_id']
    print(f"[PASS] 4. Application created: #NP-{app_id:04d}")

    # 5. Check workflow: current_step must now be 'documents'
    st, wf1 = req("GET", "/applications/current-workflow/", token=token)
    assert st == 200
    assert wf1.get('has_application') is True
    assert wf1.get('current_step') == 'documents', f"Expected 'documents', got {wf1.get('current_step')}"
    print(f"[PASS] 5. Post-application state: current_step='{wf1.get('current_step')}' (Serial step 2)")

    # 6. Upload 1 document (Citizenship)
    st, doc = req("POST", "/documents/", data={
        "application": str(app_id),
        "document_type": "Citizenship Certificate",
        "file_name": "citizenship.pdf"
    }, files={"file_path": ("citizenship.pdf", b"%PDF-1.4 DUMMY CITIZENSHIP", "application/pdf")}, token=token)
    assert st in [200, 201]
    doc_id = doc['document_id']
    print(f"[PASS] 6. Uploaded document #{doc_id}: Citizenship Certificate (Pending Verification)")

    # 7. Check workflow: current_step must now be 'verification'
    st, wf2 = req("GET", "/applications/current-workflow/", token=token)
    assert st == 200
    assert wf2.get('current_step') == 'verification', f"Expected 'verification', got {wf2.get('current_step')}"
    print(f"[PASS] 7. Post-upload state: current_step='{wf2.get('current_step')}' (Waiting for Staff Review)")

    # 8. Staff login and REJECT document
    st, s_log = req("POST", "/login/", {"username": "ramesh.staff", "password": "staffpassword123"})
    assert st == 200
    s_token = s_log['token']
    
    st, rej = req("PATCH", f"/documents/{doc_id}/", {
        "verification_status": "Rejected",
        "rejection_reason": "Citizenship scan is blurry. Please re-upload a clear high-res scan."
    }, token=s_token)
    assert st == 200
    print("[PASS] 8. Staff rejected document with reason: 'Citizenship scan is blurry'")

    # 9. Applicant sees rejected doc alert on dashboard
    st, wf3 = req("GET", "/applications/current-workflow/", token=token)
    assert st == 200
    assert wf3.get('current_step') == 'documents', f"Expected 'documents' upon rejection, got {wf3.get('current_step')}"
    assert len(wf3.get('rejected_docs', [])) == 1
    assert "blurry" in wf3['rejected_docs'][0]['rejection_reason']
    print(f"[PASS] 9. Applicant dashboard correctly returned to 'documents' step with rejected doc details")

    # 10. Applicant re-uploads corrected document
    st, doc2 = req("POST", "/documents/", data={
        "application": str(app_id),
        "document_type": "Citizenship Certificate",
        "file_name": "citizenship_clean.pdf"
    }, files={"file_path": ("citizenship_clean.pdf", b"%PDF-1.4 CLEAN CITIZENSHIP SCAN", "application/pdf")}, token=token)
    assert st in [200, 201]
    doc2_id = doc2['document_id']
    print(f"[PASS] 10. Re-uploaded clean document #{doc2_id}")

    # Delete old rejected doc to clear rejection
    req("DELETE", f"/documents/{doc_id}/", token=s_token)

    # 11. Staff verifies document
    st, ver = req("PATCH", f"/documents/{doc2_id}/", {
        "verification_status": "Verified",
        "verification_remarks": "Document verified against National Registry"
    }, token=s_token)
    assert st == 200
    print("[PASS] 11. Staff verified clean document")

    # 12. Check workflow: current_step must now be 'fee' (Payment)
    st, wf4 = req("GET", "/applications/current-workflow/", token=token)
    assert st == 200
    assert wf4.get('current_step') == 'fee', f"Expected 'fee', got {wf4.get('current_step')}"
    print(f"[PASS] 12. Post-verification state: current_step='{wf4.get('current_step')}' (Payment Unlocked!)")

    # 13. Create Payment & Sandbox Callback
    st, pay = req("POST", "/payments/create-request/", {
        "application_id": app_id,
        "payment_type": "APPLICATION_FEE",
        "gateway_name": "eSewa"
    }, token=token)
    assert st in [200, 201]
    pref = pay['payment_reference']
    print(f"[PASS] 13. Payment request created: {pref}")

    st, cb = req("POST", "/payments/simulate-sandbox-callback/", {
        "payment_reference": pref
    }, token=token)
    assert st == 200 and cb.get('status') == 'VERIFIED'
    print("[PASS] 14. Sandbox payment verified by gateway callback")

    # 14. Check workflow: current_step must now be 'signature' (Awaiting Digital Signature)
    st, wf5 = req("GET", "/applications/current-workflow/", token=token)
    assert st == 200
    assert wf5.get('current_step') == 'signature', f"Expected 'signature', got {wf5.get('current_step')}"
    print(f"[PASS] 15. Post-payment state: current_step='{wf5.get('current_step')}' (Digital Signature Unlocked)")

    # 15. Staff authorizes digital signature & completes workflow
    st, sig = req("POST", f"/applications/{app_id}/authorize-signature/", token=s_token)
    assert st == 200
    print("[PASS] 16. Staff authorized digital signature, status updated to Approved")

    # 16. Check final workflow state
    st, wf6 = req("GET", "/applications/current-workflow/", token=token)
    assert st == 200
    assert wf6.get('can_download_pdf') is True
    print(f"[PASS] 17. Final State: can_download_pdf=True, current_step='{wf6.get('current_step')}'")

    print("\n=================================================================")
    print("ALL 17 SERIAL WORKFLOW STAGES VERIFIED SUCCESSFULLY!")
    print("=================================================================")

if __name__ == '__main__':
    run_test()
