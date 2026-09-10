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
        boundary = "----WebKitBoundary98765"
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

def test_exact_user_bug_scenario():
    print("==========================================================================")
    print("TESTING EXACT BUG SCENARIO: APPLICATION APPROVED -> UNLOCK PAYMENT FLOW")
    print("==========================================================================")

    # A. Register & Login as Citizen
    uid = uuid.uuid4().hex[:6]
    email = f"citizen_bug_{uid}@example.com"
    pwd = f"SecurePass_{uid}!123"
    st, reg = req("POST", "/register/", {
        "role": "citizen", "full_name": f"Approved Citizen {uid}",
        "email": email, "phone": "9841002003", "password": pwd,
        "date_of_birth": "1994-03-20", "gender": "Female", "nationality": "Nepali",
        "address": "Lalitpur, Nepal"
    })
    assert st in [200, 201], f"Register failed: {reg}"
    print(f"[A] Citizen Registered: {email}")

    st, log = req("POST", "/login/", {"email": email, "password": pwd})
    assert st == 200
    token = log['token']
    print("[A] Citizen Logged In successfully")

    # B. Submit Application
    st, app = req("POST", "/applications/", {
        "passport_category": "Ordinary (34 Pages)",
        "service_type": "New Passport"
    }, token=token)
    assert st in [200, 201]
    app_id = app['application_id']
    print(f"[B] Application Submitted: #NP-{app_id:04d}")

    # C. Upload Required Documents
    st, doc = req("POST", "/documents/", data={
        "application": str(app_id),
        "document_type": "Citizenship Certificate",
        "file_name": "citizenship_card.pdf"
    }, files={"file_path": ("citizenship_card.pdf", b"%PDF-1.4 DUMMY CITIZENSHIP SCAN", "application/pdf")}, token=token)
    assert st in [200, 201]
    doc_id = doc['document_id']
    print(f"[C] Uploaded Document #{doc_id} (Citizenship Certificate)")

    # Verify state while awaiting staff
    st, wf_await = req("GET", "/applications/current-workflow/", token=token)
    assert st == 200
    assert wf_await['current_step'] == 'verification', f"Expected 'verification', got {wf_await['current_step']}"
    print(f"[C] Verified current_step='verification' while awaiting staff review")

    # D. Login as Staff
    st, s_log = req("POST", "/login/", {"username": "ramesh.staff", "password": "staffpassword123"})
    assert st == 200
    s_token = s_log['token']
    print("[D] Logged in as Staff (ramesh.staff)")

    # E. Staff verifies all documents
    st, vdoc = req("PATCH", f"/documents/{doc_id}/", {
        "verification_status": "Verified",
        "rejection_reason": ""
    }, token=s_token)
    assert st == 200
    print("[E] Staff verified document #DOC-" + str(doc_id))

    # F. Staff explicitly approves the Application (status = 'Approved')
    st, app_upd = req("PATCH", f"/applications/{app_id}/", {
        "status": "Approved"
    }, token=s_token)
    assert st == 200
    assert app_upd.get('status') == 'Approved', f"Expected 'Approved', got {app_upd.get('status')}"
    print("[F] Staff set Application #NP-" + str(app_id) + " status to 'Approved'")

    # G. Logout Staff (session cleared)
    s_token = None
    print("[G] Staff session closed")

    # H. Login as Citizen again
    st, log2 = req("POST", "/login/", {"email": email, "password": pwd})
    assert st == 200
    token = log2['token']
    print("[H] Citizen logged in again after Staff approval")

    # I. Open Citizen Dashboard (GET /api/applications/current-workflow/)
    st, wf_dash = req("GET", "/applications/current-workflow/", token=token)
    assert st == 200
    print(f"Backend Returned Application Status: '{wf_dash.get('status')}'")
    print(f"Backend Computed Current Step: '{wf_dash.get('current_step')}'")

    # CRITICAL CHECK: Must NOT be stuck at documents, Must be 'fee' (Payment)
    assert wf_dash.get('status') == 'Approved', f"Expected status 'Approved', got {wf_dash.get('status')}"
    assert wf_dash.get('current_step') == 'fee', f"CRITICAL BUG: Expected current_step='fee', got '{wf_dash.get('current_step')}'!"
    print("[I] [PASS] Citizen Portal is NOT stuck at documents!")
    print("    Progress Tracker: [OK Application] -> [OK Documents] -> [OK Verification] -> [CURRENT Payment]")
    print("    Next Step Card unlocked: 'Pay Application Fee' (Amount: NPR 5,000)")

    # J. Complete payment flow
    st, pay_req = req("POST", "/payments/create-request/", {
        "application_id": app_id,
        "payment_type": "APPLICATION_FEE",
        "gateway_name": "eSewa"
    }, token=token)
    assert st in [200, 201]
    pay_ref = pay_req['payment_reference']
    print(f"[J] Generated Payment Reference: {pay_ref}")

    st, sim = req("POST", "/payments/simulate-sandbox-callback/", {
        "payment_reference": pay_ref
    }, token=token)
    assert st == 200, f"Payment callback simulation failed: {sim}"
    print("[J] Sandbox payment completed successfully and verified in DB.")

    # Check workflow after payment: Payment becomes OK, Digital Signature becomes [CURRENT]
    st, wf_pay = req("GET", "/applications/current-workflow/", token=token)
    assert st == 200
    assert wf_pay.get('is_payment_verified') is True, "is_payment_verified should be True"
    assert wf_pay.get('current_step') == 'signature', f"Expected current_step='signature', got '{wf_pay.get('current_step')}'"
    print("[J] [PASS] Payment verified! Workflow advanced to: 'signature'")
    print("    Progress Tracker: [OK Payment] -> [CURRENT Digital Signature]")
    print("    Next Step Card unlocked: 'Sign Application'")

    # K. Complete digital signature flow
    st, sig_res = req("POST", "/digital-signatures/", {
        "application": app_id
    }, token=token)
    assert st in [200, 201], f"Digital signature failed: {sig_res}"
    print(f"[K] Digital Signature completed: Certificate Serial: {sig_res.get('certificate_serial')}")

    # Check workflow after signature: Signature becomes OK, Queue becomes [CURRENT] or token displayed
    st, wf_sig = req("GET", "/applications/current-workflow/", token=token)
    assert st == 200
    print(f"[K] After signature: has_queue_token={bool(wf_sig.get('queue_token'))}, current_step='{wf_sig.get('current_step')}'")
    assert wf_sig.get('is_signature_verified') is True
    assert wf_sig.get('current_step') in ['queue', 'passport_ready']
    print("[K] [PASS] Digital Signature verified! Workflow advanced to: Queue Token / Biometric Ready")

    # L. Check Queue Token
    st, tokens = req("GET", "/queue-tokens/", token=token)
    assert st == 200
    token_list = tokens if isinstance(tokens, list) else tokens.get('results', [])
    app_tokens = [t for t in token_list if t.get('application') == app_id]
    assert len(app_tokens) == 1, f"Expected exactly 1 queue token, got {len(app_tokens)}"
    q_token = app_tokens[0]
    print(f"[L] [PASS] Queue Token verified: T-{q_token.get('token_number'):03d}, Status: {q_token.get('queue_status')}")
    print(f"    No duplicate queue tokens created (count = {len(app_tokens)})")

    print("\n==========================================================================")
    print("BUG FIX VERIFIED: APPROVED APPLICATIONS SEAMLESSLY PROGRESS TO PAYMENT -> SIGNATURE -> QUEUE!")
    print("==========================================================================")

if __name__ == '__main__':
    test_exact_user_bug_scenario()
