/**
 * ==========================================================================
 * BILINGUAL TRANSLATION ENGINE (ENGLISH / नेपाली)
 * Official Language Localization for Nepal Department of Passports Portal
 * ==========================================================================
 */

const I18n = {
  currentLang: (typeof localStorage !== 'undefined' && localStorage.getItem('passport_lang')) || 'en',

  translations: {
    en: {
      // Topbar & Brand
      gov_motto: "Government of Nepal • Ministry of Foreign Affairs • Department of Passports",
      toll_free: "Toll Free: 1660-01-00123",
      location: "Tripureshwor, Kathmandu",
      brand_title: "Department of Passports",
      brand_subtitle: "Government of Nepal • Smart Portal",
      choose_language: "Choose Language / भाषा छान्नुहोस्",
      
      // Nav Links
      nav_home: "Home",
      nav_how_to_apply: "How to Apply",
      nav_requirements: "Requirements & Fees",
      nav_track: "Track Application",
      nav_portal: "Portal Dashboard",
      nav_login: "Sign In",
      nav_register: "Register",
      nav_logout: "Sign Out",
      
      // Portals
      portal_citizen: "Citizen Portal",
      portal_staff: "Staff Portal",
      portal_admin: "Admin Portal",

      // Common Buttons & Actions
      btn_apply_now: "Apply for Digital Passport",
      btn_track_status: "Track Status",
      btn_login: "Sign In",
      btn_register: "Register here",
      btn_submit: "Submit",
      btn_cancel: "Cancel",
      btn_save: "Save",
      btn_edit: "Edit",
      btn_delete: "Delete",
      btn_update: "Update",
      btn_view: "View",
      btn_close: "Close",
      btn_back: "Back",
      btn_next: "Next",
      btn_previous: "Previous",
      btn_download: "Download",
      btn_print: "Print",
      btn_export: "Export",
      btn_refresh: "Refresh",
      btn_filter: "Filter",
      btn_search: "Search",
      btn_reset: "Reset",
      btn_confirm: "Confirm",
      btn_proceed: "Proceed",
      btn_renew: "Renew Passport",
      btn_renew_now: "Renew Passport Now",
      btn_upload_document: "Upload Document",
      btn_view_document: "View Document",
      btn_verify_document: "Verify Document",
      btn_reject_document: "Reject Document",
      btn_inspect_file: "Inspect Document File",
      btn_approve_application: "Approve Application",
      btn_reject_application: "Reject Application",
      btn_call_next: "Call Next Token",
      btn_mark_serving: "Mark Serving",
      btn_complete_service: "Complete Service",
      btn_skip_token: "Skip Token",
      btn_pay_now: "Pay Now",
      btn_sign_application: "Sign Application",
      btn_create_account: "Create Citizen Account",
      btn_sign_in_account: "Sign In to Account",
      btn_print_save: "Print / Save",
      btn_copy: "Copy",
      btn_new_application: "New Application",
      btn_reupload: "Re-upload",

      // Common Labels
      label_actions: "Actions",
      label_status: "Status",
      label_date: "Date",
      label_details: "Details",
      label_search: "Search",
      label_filter: "Filter",
      label_all: "All",
      label_none: "None",
      label_loading: "Loading...",
      label_processing: "Processing...",
      label_no_data: "No data available",
      label_not_available: "N/A",
      label_required: "Required",
      label_optional: "Optional",
      label_application_id: "Application ID",
      label_reference: "Reference",
      label_token_number: "Token Number",
      label_full_name: "Full Name",
      label_email: "Email Address",
      label_phone: "Phone Number",
      label_dob: "Date of Birth",
      label_gender: "Gender",
      label_nationality: "Nationality",
      label_district: "District",
      label_province: "Province",
      label_permanent_address: "Permanent Address",
      label_citizenship_no: "Citizenship Number",
      label_issue_date: "Issue Date",
      label_issue_district: "Issue District",
      label_expiry_date: "Expiry Date",
      label_passport_category: "Passport Category",
      label_service_type: "Service Type",
      label_fee_amount: "Fee Amount",
      label_queue_token: "Queue Token",
      label_counter: "Counter / Desk",
      label_served_by: "Served By",
      label_people_ahead: "People Ahead",
      label_est_wait: "Estimated Wait Time",
      label_notes: "Notes / Remarks",
      label_rejection_reason: "Rejection Reason",
      label_created_at: "Created At",
      label_last_updated: "Last Updated",
      label_photo: "Passport Photo",
      label_uploaded_file: "Uploaded File",
      label_file_type: "File Type",
      label_file_size: "File Size",
      label_uploaded_on: "Uploaded On",
      label_inspection_status: "Visual Inspection",
      label_select_application: "Select an Application",

      // Status Labels
      status_pending: "Pending",
      status_under_review: "Under Review",
      status_approved: "Approved",
      status_rejected: "Rejected",
      status_completed: "Completed",
      status_verified: "Verified",
      status_pending_review: "Pending Review",
      status_inspection_required: "Inspection Required",
      status_waiting: "Waiting",
      status_called: "Called",
      status_serving: "Serving",
      status_skipped: "Skipped",
      status_payment_pending: "Payment Pending",
      status_payment_verified: "Payment Verified",
      status_payment_failed: "Payment Failed",
      status_qr_generated: "QR Generated",
      status_signature_pending: "Signature Pending",
      status_signature_completed: "Signature Completed",
      status_biometrics_pending: "Biometrics Pending",
      status_biometrics_verified: "Biometrics Verified",
      status_biometrics_failed: "Biometrics Failed",
      status_active: "ACTIVE",
      status_expired: "EXPIRED",
      status_unknown: "Unknown",

      // Document Types
      doc_citizenship: "Citizenship Certificate",
      doc_nid: "National ID Card (NID)",
      doc_photo: "Passport-size Photo",
      doc_birth_cert: "Birth Registration Certificate",
      doc_marriage_cert: "Marriage Certificate",
      doc_old_passport: "Previous Passport",
      doc_other: "Supporting Document",

      // Workflow Tracker Steps
      wf_application: "Application",
      wf_documents: "Documents",
      wf_verification: "Verification",
      wf_payment: "Payment",
      wf_signature: "Digital Signature",
      wf_queue: "Queue",
      wf_completed: "Completed",

      // Hero Section
      hero_badge: "Official Government of Nepal Portal",
      hero_title_1: "Passport Application &",
      hero_title_2: "Queue Management",
      hero_desc: "Apply online, complete seamless digital verification, and access your verified Virtual e-Passport directly on your device. Instant, secure, and 100% paperless passport services for all Nepali citizens.",
      quick_lookup_title: "Quick Application Status Lookup",
      quick_lookup_placeholder: "Enter Application ID (e.g. 1)",
      
      // Showcase Box
      showcase_title: "Virtual e-Passport Nepal",
      showcase_badge: "100% Digital",
      showcase_feat_1_title: "Instant Virtual Issuance",
      showcase_feat_1_desc: "Upon verification, your digital passport is immediately generated and ready in your portal.",
      showcase_feat_2_title: "Cryptographic QR Verification",
      showcase_feat_2_desc: "Use and present your virtual passport digitally with real-time verification credentials.",
      showcase_feat_3_title: "Real-Time Digital Queue",
      showcase_feat_3_desc: "Automated verification updates and instant alerts as your documents are reviewed.",
      digital_support: "Digital Support:",

      // Statistics
      stat_passports: "Virtual Passports Issued",
      stat_districts: "Districts Supported",
      stat_wait: "Instant Digital Access",
      stat_flow: "Paperless Digital Flow",

      // 9-Step Process
      process_title: "9-Step Digital Application & Verification Journey",
      process_subtitle: "Everything is processed digitally — apply, verify, and use your passport virtually with zero paperwork.",
      step1_title: "Online Registration",
      step1_desc: "Create your citizen profile using your valid details, email, and phone number.",
      step2_title: "Fill Application",
      step2_desc: "Complete your e-passport application form with accurate personal and contact information.",
      step3_title: "Upload Documents",
      step3_desc: "Upload clear scanned copies of your Nepali Citizenship Certificate and required proofs.",
      step4_title: "Queue Token Generation",
      step4_desc: "Receive an automated digital queue token with a designated processing slot.",
      step5_title: "Fee Assessment",
      step5_desc: "Verify your category (34 pages / 66 pages / Urgent Express) and fee details.",
      step6_title: "Digital Biometrics Match",
      step6_desc: "Your digital photo and biometric credentials are authenticated electronically against national databases.",
      step7_title: "Staff Verification",
      step7_desc: "Staff officer reviews and validates your submitted digital documents and verifies eligibility.",
      step8_title: "Government Digital Signature",
      step8_desc: "Upon verification, your Virtual e-Passport is cryptographically signed and authenticated by the Government of Nepal certifying authority.",
      step9_title: "Virtual Passport Ready",
      step9_desc: "Access, view, and use your active Virtual e-Passport directly from your citizen portal anytime.",

      // Tariffs
      tariff_title: "Passport Categories & Fee Structure",
      tariff_subtitle: "Standard official fee tariffs established by the Ministry of Foreign Affairs, Government of Nepal.",
      tier1_title: "Ordinary e-Passport (34 Pages)",
      tier1_desc: "Recommended for regular tourists, students, and travelers.",
      tier1_price: "NPR 5,000 / Standard Delivery",
      tier2_title: "Ordinary e-Passport (66 Pages)",
      tier2_desc: "Ideal for business travelers, frequent flyers, and expatriates.",
      tier2_price: "NPR 10,000 / Standard Delivery",
      tier3_title: "Express Urgent Processing",
      tier3_desc: "Expedited priority queue for medical and official emergencies.",
      tier3_price: "NPR 12,000 / Fast-Track Delivery",
      btn_apply_34: "Apply for 34 Pages",
      btn_apply_66: "Apply for 66 Pages",
      btn_apply_urgent: "Apply Urgent Service",

      // CTA Banner
      cta_title: "Ready to Apply for your Nepali e-Passport?",
      cta_desc: "Register online in less than 2 minutes, submit required documents, and obtain your official queue token.",

      // Footer
      footer_about_title: "Department of Passports",
      footer_about_desc: "Official digital application preparation and smart queue management system for e-Passport services in Nepal.",
      footer_services_title: "Citizen Services",
      footer_hours_title: "Online Portal Availability",
      footer_hours_status: "Available 24 / 7",
      footer_hours_desc: "Submit applications, upload documents, and track your queue token anytime from anywhere.",
      footer_hours_badge: "✅ 100% Digital & Paperless",
      footer_support_title: "Digital Support",
      footer_rights: "© 2026 Department of Passports, Government of Nepal. All Rights Reserved.",

      // Auth Pages
      signin_title: "Sign In",
      signin_subtitle: "Citizen & Administrative Unified Access",
      signin_btn: "Sign In to Account",
      register_title: "Citizen Registration",
      register_subtitle: "Create your official citizen account to apply for a passport, upload documents, and track queue tokens.",
      register_btn: "Create Account",
      register_section_personal: "1. Personal Information",
      register_section_contact: "2. Contact & Permanent Address",
      register_section_security: "3. Account Security",
      email_label: "Email Address",
      password_label: "Password",
      confirm_password_label: "Confirm Password",
      fullname_label: "Full Legal Name",
      phone_label: "Phone Number",
      dob_label: "Date of Birth",
      gender_label: "Gender",
      address_label: "Permanent Address",
      login_identifier_label: "Email Address or Username",
      login_identifier_placeholder: "e.g. citizen@example.com or officer_username",
      password_placeholder: "Enter your account password",
      forgot_password: "Forgot password?",
      remember_me: "Remember me on this device",
      no_account_yet: "Don't have a citizen account yet?",
      already_have_account: "Already registered?",
      login_here: "Sign In here",
      session_expired_msg: "Your session has expired. Please sign in again.",

      // Track Page
      track_page_title: "Live Passport Application Tracking",
      track_page_desc: "Enter your official Application Reference ID or Queue Token number to check your processing status.",
      track_input_placeholder: "e.g. 1 or NP-12345",
      stage_submitted: "Application Submitted",
      stage_submitted_desc: "Online form received",
      stage_review: "Document Review & Biometrics",
      stage_review_desc: "Verification against national registry",
      stage_approved: "Officer Verification & Approval",
      stage_approved_desc: "Digital eligibility and security clearance",
      stage_completed: "Virtual e-Passport Issued",
      stage_completed_desc: "Cryptographically signed and ready in portal",
      queue_assignment_title: "Queue Assignment",
      token_badge_label: "TOKEN",
      no_queue_token: "No queue token assigned yet.",

      // Applicant Portal — Sidebars
      side_citizen_services: "Citizen Services",
      side_dashboard: "Dashboard",
      side_my_application: "My Application",
      side_documents: "Documents",
      side_queue_token: "Queue Token",
      side_notifications: "Notifications",
      side_track_status: "Track Status",
      side_account: "Account",
      side_my_profile: "My Profile",
      side_back_home: "Back to Home",
      side_logout: "Sign Out",

      // Applicant Dashboard
      dash_welcome: "Welcome,",
      dash_welcome_sub: "Manage your passport application, track verification, and access your Virtual e-Passport.",
      dash_active_app_banner: "Active Passport Application",
      dash_active_app_desc: "Your application is being processed through the digital verification workflow.",
      dash_view_progress: "View Progress",
      dash_workflow_tracker: "Application Processing Tracker",
      dash_current_action: "Recommended Action",
      dash_total_apps: "Total Applications",
      dash_active_token: "Active Queue Token",
      dash_docs_verified: "Verified Documents",
      dash_payment_status: "Payment Status",
      dash_my_passports: "My Official Passports",
      dash_passport_badge: "Biometrically Verified",
      dash_issued_on: "Issued On:",
      dash_valid_until: "Valid Until:",
      dash_download_pdf: "Download PDF Certificate",
      dash_expired_notice: "Your passport has expired. You are eligible to apply for Passport Renewal.",
      dash_apps_history: "Application History",
      dash_apply_new: "Apply for Passport",
      dash_no_active_app: "No Active Application",
      dash_no_active_app_desc: "You have not submitted a passport application yet. Get started online in minutes.",
      dash_start_application: "Start Passport Application",

      // Application Form
      app_form_title: "e-Passport Application Form",
      app_form_subtitle: "Government of Nepal • Department of Passports Official Form",
      app_sec_category: "1. Passport Category & Service Type",
      app_sec_personal: "2. Personal & Identity Details",
      app_sec_parents: "3. Family & Emergency Contact Details",
      app_category_34: "Ordinary e-Passport (34 Pages) - NPR 5,000",
      app_category_66: "Ordinary e-Passport (66 Pages) - NPR 10,000",
      app_category_urgent: "Express Urgent Service (34 Pages) - NPR 12,000",
      app_delivery_std: "Standard Office Pickup",
      app_delivery_express: "Express Office Pickup",
      app_fathers_name: "Father's Full Legal Name",
      app_mothers_name: "Mother's Full Legal Name",
      app_spouse_name: "Spouse's Full Legal Name (Optional)",
      app_emergency_name: "Emergency Contact Person",
      app_emergency_rel: "Relationship",
      app_emergency_phone: "Emergency Phone Number",
      app_declaration: "I hereby declare that all information provided in this application is true, complete, and accurate. I understand that submitting false documents or statements is punishable under the Nepal Passport Act.",
      app_declaration_agree: "I confirm and accept the statutory declaration",
      app_existing_active_warning: "You already have an active application. Another application cannot be submitted until your active application is resolved.",

      // Documents Page
      docs_page_title: "Document Preparation & Verification",
      docs_page_subtitle: "Upload clear digital scans of your official Nepali government credentials.",
      docs_select_app: "Select Passport Application",
      docs_upload_heading: "Upload Required Document",
      docs_select_type: "Select Document Type",
      docs_drag_drop: "Drag & drop files here or click to browse",
      docs_format_hint: "Supported formats: PDF, JPG, JPEG, PNG (Max 10MB)",
      docs_photo_card_title: "Mandatory Passport-Size Photo",
      docs_photo_card_desc: "Upload a recent passport-sized digital photograph with plain light background.",
      docs_uploaded_list: "Submitted Documents for This Application",
      docs_no_docs_yet: "No documents have been uploaded for this application yet.",

      // Queue Page
      queue_page_title: "Smart Digital Queue Token",
      queue_page_subtitle: "Real-time queue tracking and live counter status for your passport verification.",
      queue_current_ticket: "Your Official Queue Token",
      queue_token_prefix: "Token #",
      queue_assigned_counter: "Assigned Counter",
      queue_people_ahead_desc: "Applicants ahead of you in line",
      queue_wait_desc: "Estimated waiting time",
      queue_live_board: "Active Counter Status",
      queue_no_token_yet: "No active queue token found.",
      queue_no_token_desc: "A queue token will be automatically assigned once your documents are uploaded and reviewed.",
      queue_info_pages_fee: "Pages & Fee",
      queue_info_token_date: "Token Date",
      queue_info_time_slot: "Time Slot",
      queue_info_called_at: "Called At",
      queue_attend_note: "Please attend the passport office at your scheduled time slot and present this token number.",
      queue_stage_progress: "Queue Stage Progress",
      queue_step_waiting_desc: "Token issued, awaiting your turn",
      queue_step_called_desc: "Your token has been called",
      queue_step_serving_desc: "Currently being processed by staff",
      queue_step_completed_desc: "Processing complete",
      queue_all_tokens: "All Queue Tokens",
      queue_today: "Today",
      queue_standard_queue: "Standard Queue",
      queue_not_yet_called: "Not yet called",
      queue_load_error: "Could not load queue information. Please try again.",

      // Staff Portal
      staff_dash_title: "Staff Verification Desk",
      staff_dash_subtitle: "Real-time applicant inspection, document validation, and queue control.",
      staff_desk_assigned: "Your Counter Desk",
      staff_active_token_title: "Currently Serving Token",
      staff_no_active_token: "No active applicant at your counter.",
      staff_stat_served: "Served Today",
      staff_stat_waiting: "Waiting in Queue",
      staff_stat_verified: "Documents Verified",
      staff_stat_pending_apps: "Pending Applications",
      staff_inspection_alert: "Visual Inspection Mandatory: You must click 'Inspect Document File' to examine the applicant's official file before approving.",
      staff_doc_inspection_title: "Document Review & Inspection",
      staff_verify_bio_btn: "Match Digital Biometrics",
      staff_bio_status_label: "Biometrics Status:",

      // Admin Portal
      admin_dash_title: "Administrative Control Center",
      admin_dash_subtitle: "System overview, issuance statistics, staff management, and audit logs.",
      admin_stat_total_apps: "Total Applications",
      admin_stat_active_staff: "Active Staff Desks",
      admin_stat_verified_payments: "Verified Payments",
      admin_stat_total_revenue: "Total Revenue",
      admin_stat_completed_passports: "Issued Passports",
      admin_nav_apps: "Applications",
      admin_nav_staff: "Staff Management",
      admin_nav_payments: "Payment Audits",
      admin_nav_reports: "Reports & Analytics",
      admin_nav_logs: "Activity Logs",
      admin_add_staff: "Add New Staff Member",
      admin_staff_table_title: "Passport Office Staff Registry",
      admin_recent_apps_title: "Recent Passport Applications",

      // Admin Extra
      admin_sidebar_system: "System Management",
      admin_sidebar_overview: "System Overview",
      admin_sidebar_portals: "Public Portals",
      admin_live_system: "Live System",
      admin_stat_all_time: "All-time submissions",
      admin_stat_requires_processing: "Requires processing",
      admin_stat_verified_issued: "Verified & Issued",
      admin_apps_title: "Central Application Registry",
      admin_apps_subtitle: "Search, inspect, and manage all passport applications across the country.",
      admin_payments_title: "Fee Payment & Financial Audit",
      admin_payments_subtitle: "Audit, track, and reconcile all application fee payments.",
      admin_staff_management_title: "Passport Office Staff Registry",
      admin_staff_management_subtitle: "Manage verification officers, counter assignments, and staff accounts.",
      admin_reports_title: "System Reports & Intelligence",
      admin_reports_subtitle: "Comprehensive analytics on passport issuance, queues, and office performance.",
      admin_logs_title: "Central System Activity & Audit Logs",
      admin_logs_subtitle: "Permanent, chronological audit logs of administrative actions, status transitions, and security events.",
      admin_record_manual_note: "Record Manual Audit Note",
      admin_audit_trail: "Audit Trail",
      admin_super_admin: "Super Admin Access",
      admin_registry_badge: "Live Registry",
      admin_total_payments: "Total Payments",
      admin_verified_revenue: "Verified Revenue",
      admin_pending_payments: "Pending Payments",
      admin_failed_refunded: "Failed / Incomplete",
      admin_export_csv: "Export CSV",
      admin_filter_status: "Filter Status",
      admin_filter_all: "All Statuses",
      admin_filter_pending: "Pending",
      admin_filter_verified: "Verified",
      admin_filter_approved: "Approved",
      admin_filter_rejected: "Rejected",

      // Staff Dashboard Extra
      staff_sidebar_operations: "Operations",
      staff_sidebar_queue_verify: "Queue & Verification",
      staff_sidebar_waiting_roster: "Waiting Roster",
      staff_sidebar_queue: "Queue Management",
      staff_sidebar_verify: "Document Verify",
      staff_queue_title: "Live Queue Management",
      staff_queue_subtitle: "Manage and control the physical queue at your counter.",
      staff_verify_title: "Document Verification Desk",
      staff_verify_subtitle: "Inspect, cross-examine, and verify applicant submitted documents.",
      staff_live_badge: "Live",
      staff_desk_title: "Digital Verification & Queue Desk",
      staff_desk_active: "Desk Active",
      staff_desk_subtitle: "Review citizen applications, verify uploaded digital documents, and grant instant Virtual e-Passports.",
      staff_sync_queue: "Sync Queue",
      staff_currently_serving: "Currently Serving Token",
      staff_no_token_called: "No Token Called",
      staff_awaiting_citizen: "Awaiting Next Citizen",
      staff_stat_waiting_desc: "Awaiting verification",
      staff_stat_pending_desc: "Applications pending",
      staff_stat_verified_desc: "Authenticated files",
      staff_stat_served_desc: "Processed & Verified",
      staff_active_apps_title: "Active Applications & Verification Queue",
      staff_col_token_ref: "Token / Ref",
      staff_col_applicant: "Applicant Details",
      staff_col_doc_type: "Document Type",
      staff_col_file: "File Document",
      staff_modal_title: "Application Review & Verification Desk",
      staff_biometrics_match: "Biometrics Match",
      staff_uploaded_credentials: "Uploaded Verification Credentials",
      staff_biometrics_stage: "Stage 6: Digital Biometrics Matching",
      staff_biometrics_desc: "Validate facial features and fingerprint scans against national identity database.",
      staff_bio_verify_btn: "Mark Biometrics Verified",
      staff_bio_fail_btn: "Flag Biometrics Failed",
      staff_signature_stage: "Stage 8 & 9: Government Digital Signature & Issuance",
      staff_signature_desc: "Authorizing this step issues an encrypted Government RSA-SHA256 digital certificate and generates the downloadable Virtual e-Passport.",
      staff_authorize_btn: "Authorize Digital Signature & Approve",
      staff_close_workspace: "Close Workspace",

      // Dashboards & Virtual Passport
      virtual_passport_title: "Official Virtual e-Passport",
      vp_gov_header: "Government of Nepal • नेपाल सरकार",
      vp_doc_title: "PASSPORT • राहदानी",
      vp_verified_badge: "Biometrically Verified",
      vp_label_name: "Full Name / पूरा नाम",
      vp_label_pass_no: "Passport No. / राहदानी नं.",
      vp_label_nationality: "Nationality / राष्ट्रियता",
      vp_label_dob: "Date of Birth / जन्म मिति",
      vp_label_gender: "Gender / लिङ्ग",
      vp_label_issue: "Date of Issue / जारी मिति",
      vp_label_expiry: "Date of Expiry / म्याद सकिने मिति",
      vp_label_authority: "Authority / जारी गर्ने निकाय",
      vp_authority_val: "DEPT OF PASSPORTS",

      // Dynamic Toast & Error Messages
      msg_doc_verified: "Document verified successfully.",
      msg_doc_rejected: "Document has been rejected.",
      msg_doc_uploaded: "Document uploaded successfully.",
      msg_app_approved: "Application approved successfully.",
      msg_app_submitted: "Application submitted successfully.",
      msg_payment_success: "Payment completed successfully.",
      msg_payment_simulated: "Sandbox payment simulation completed successfully.",
      msg_token_called: "Next token called successfully.",
      msg_token_serving: "Token marked as serving.",
      msg_token_completed: "Token service completed.",
      msg_token_skipped: "Token skipped.",
      msg_staff_created: "Staff member created successfully.",
      msg_copied: "Copied to clipboard!",
      msg_inspection_required: "Visual Inspection Required: You must inspect the actual document file first.",
      err_active_application: "You already have an active passport application. Another cannot be submitted.",
      err_active_passport: "You already have an active valid passport. Renewal is only permitted after expiration.",
      err_expired_apply_renewal: "Your previous passport has expired. Please apply through the Renewal workflow.",
      err_missing_photo: "A verified Passport-size Photo is mandatory.",
      err_missing_citizenship: "A verified Citizenship Certificate or National ID is required.",
      err_unverified_docs: "All submitted documents must be verified by staff before approval.",
      err_network: "Network connection error. Please verify your connection.",
      err_generic: "An error occurred while processing your request.",
      processing_please_wait: "Processing, please wait...",

      // Notifications Page
      notif_page_subtitle: "Updates and alerts about your passport application.",
      notif_mark_all_read: "Mark All Read",
      notif_unread: "Unread",
      notif_read: "Read",
      notif_load_error: "Could not load notifications",
      notif_retry_hint: "Please check your connection and try again.",
      notif_no_unread: "No unread notifications.",
      notif_no_read: "No read notifications.",
      notif_none_yet: "No notifications yet.",
      notif_appear_here: "Notification alerts about your application will appear here.",
      notif_all_already_read: "All notifications are already read.",
      notif_marked_all_read: "All notifications marked as read.",
      notif_mark_all_error: "Could not mark all as read. Please try again.",

      // Profile Page
      profile_page_title: "My Profile",
      profile_page_subtitle: "View and update your citizen account information.",
      profile_active_citizen: "Active Citizen",
      profile_personal_info: "Personal Information",
      profile_loading: "Loading profile...",
      profile_email_helper: "Used for login — contact office to change.",
      profile_save_changes: "Save Changes",
      profile_saving: "Saving...",
      profile_cancel_edit: "Cancel Edit",
      profile_account_security: "Account Security",
      profile_password_label: "Password",
      profile_password_last_changed: "Last changed: Not available",
      profile_change_password: "Change Password",
      profile_change_password_hint: "To change your password, please contact the helpline: 1660-01-00123.",
      profile_verified_label: "Citizen Account Verified",
      profile_verified_desc: "Account registered and active in the Nepal Passport System",
      profile_load_error: "Could not load profile information.",
      profile_update_error: "Could not update profile. Please try again.",
      profile_updated: "Profile updated successfully!",

      // Gender options
      gender_male: "Male",
      gender_female: "Female",
      gender_other: "Other",
    },

    ne: {
      // Topbar & Brand
      gov_motto: "नेपाल सरकार • परराष्ट्र मन्त्रालय • राहदानी विभाग",
      toll_free: "निःशुल्क हटलाइन: १६६०-०१-००१२३",
      location: "त्रिपुरेश्वर, काठमाडौं",
      brand_title: "राहदानी विभाग",
      brand_subtitle: "नेपाल सरकार • डिजिटल राहदानी सेवा प्रणाली",
      choose_language: "भाषा छान्नुहोस् / Choose Language",

      // Nav Links
      nav_home: "गृहपृष्ठ",
      nav_how_to_apply: "आवेदन प्रक्रिया",
      nav_requirements: "कागजात र दस्तुर",
      nav_track: "स्थिति ट्र्याक गर्नुहोस्",
      nav_portal: "ड्यासबोर्ड",
      nav_login: "लग-इन",
      nav_register: "नयाँ दर्ता",
      nav_logout: "लग-आउट",

      // Portals
      portal_citizen: "नागरिक पोर्टल",
      portal_staff: "कर्मचारी पोर्टल",
      portal_admin: "प्रशासक पोर्टल",

      // Common Buttons & Actions
      btn_apply_now: "डिजिटल राहदानी आवेदन दिनुहोस्",
      btn_track_status: "आवेदन स्थिति हेर्नुहोस्",
      btn_login: "लग-इन गर्नुहोस्",
      btn_register: "यहाँ दर्ता गर्नुहोस्",
      btn_submit: "पेश गर्नुहोस्",
      btn_cancel: "रद्द गर्नुहोस्",
      btn_save: "सुरक्षित गर्नुहोस्",
      btn_edit: "सम्पादन",
      btn_delete: "हटाउनुहोस्",
      btn_update: "अद्यावधिक",
      btn_view: "हेर्नुहोस्",
      btn_close: "बन्द गर्नुहोस्",
      btn_back: "पछाडि",
      btn_next: "अगाडि",
      btn_previous: "अघिल्लो",
      btn_download: "डाउनलोड",
      btn_print: "प्रिन्ट",
      btn_export: "निर्यात (Export)",
      btn_refresh: "रिफ्रेस",
      btn_filter: "फिल्टर",
      btn_search: "खोज्नुहोस्",
      btn_reset: "रिसेट",
      btn_confirm: "यकिन गर्नुहोस्",
      btn_proceed: "अगाडि बढ्नुहोस्",
      btn_renew: "राहदानी नवीकरण गर्नुहोस्",
      btn_renew_now: "अहिले राहदानी नवीकरण गर्नुहोस्",
      btn_upload_document: "कागजात अपलोड गर्नुहोस्",
      btn_view_document: "कागजात हेर्नुहोस्",
      btn_verify_document: "कागजात प्रमाणित गर्नुहोस्",
      btn_reject_document: "कागजात अस्वीकृत गर्नुहोस्",
      btn_inspect_file: "कागजात फाइल निरीक्षण गर्नुहोस्",
      btn_approve_application: "आवेदन स्वीकृत गर्नुहोस्",
      btn_reject_application: "आवेदन अस्वीकृत गर्नुहोस्",
      btn_call_next: "अर्को टोकन बोलाउनुहोस्",
      btn_mark_serving: "सेवा सुरु गर्नुहोस्",
      btn_complete_service: "सेवा सम्पन्न गर्नुहोस्",
      btn_skip_token: "टोकन छोड्नुहोस् (Skip)",
      btn_pay_now: "अहिले भुक्तानी गर्नुहोस्",
      btn_sign_application: "डिजिटल हस्ताक्षर गर्नुहोस्",
      btn_create_account: "नयाँ नागरिक खाता खोल्नुहोस्",
      btn_sign_in_account: "खातामा प्रवेश गर्नुहोस्",
      btn_print_save: "प्रिन्ट / सुरक्षित गर्नुहोस्",
      btn_copy: "कपी गर्नुहोस्",
      btn_new_application: "नयाँ आवेदन",
      btn_reupload: "पुनः अपलोड",

      // Common Labels
      label_actions: "कार्यहरू",
      label_status: "स्थिति",
      label_date: "मिति",
      label_details: "विवरण",
      label_search: "खोज्नुहोस्",
      label_filter: "फिल्टर",
      label_all: "सबै",
      label_none: "कुनै पनि होइन",
      label_loading: "लोड हुँदैछ...",
      label_processing: "प्रक्रियामा छ...",
      label_no_data: "कुनै विवरण उपलब्ध छैन",
      label_not_available: "लागू नहुने",
      label_required: "अनिवार्य",
      label_optional: "ऐच्छिक",
      label_application_id: "आवेदन नम्बर",
      label_reference: "सन्दर्भ नम्बर",
      label_token_number: "टोकन नम्बर",
      label_full_name: "पूरा कानुनी नाम",
      label_email: "इमेल ठेगाना",
      label_phone: "मोबाइल नम्बर",
      label_dob: "जन्म मिति",
      label_gender: "लिङ्ग",
      label_nationality: "राष्ट्रियता",
      label_district: "जिल्ला",
      label_province: "प्रदेश",
      label_permanent_address: "स्थायी ठेगाना",
      label_citizenship_no: "नागरिकता नम्बर",
      label_issue_date: "जारी मिति",
      label_issue_district: "जारी जिल्ला",
      label_expiry_date: "म्याद सकिने मिति",
      label_passport_category: "राहदानी प्रकार",
      label_service_type: "सेवा प्रकार",
      label_fee_amount: "तोकिएको दस्तुर",
      label_queue_token: "लाम टोकन",
      label_counter: "काउन्टर / डेस्क",
      label_served_by: "सेवा दिने अधिकृत",
      label_people_ahead: "लाममा अगाडिका सेवाग्राही",
      label_est_wait: "अनुमानित प्रतीक्षा समय",
      label_notes: "कैफियत / टिप्पणी",
      label_rejection_reason: "अस्वीकृतिको कारण",
      label_created_at: "दर्ता मिति",
      label_last_updated: "पछिल्लो अद्यावधिक",
      label_photo: "राहदानी फोटो",
      label_uploaded_file: "अपलोड गरिएको फाइल",
      label_file_type: "फाइल प्रकार",
      label_file_size: "फाइल साइज",
      label_uploaded_on: "अपलोड मिति",
      label_inspection_status: "कागजात निरीक्षण स्थिति",
      label_select_application: "— आवेदन छान्नुहोस् —",

      // Status Labels
      status_pending: "लम्बित",
      status_under_review: "पुनरावलोकनमा",
      status_approved: "स्वीकृत",
      status_rejected: "अस्वीकृत",
      status_completed: "सम्पन्न",
      status_verified: "प्रमाणित",
      status_pending_review: "समीक्षा बाँकी",
      status_inspection_required: "निरीक्षण आवश्यक",
      status_waiting: "प्रतीक्षारत",
      status_called: "बोलाइएको",
      status_serving: "सेवामा",
      status_skipped: "छुटाइएको",
      status_payment_pending: "भुक्तानी बाँकी",
      status_payment_verified: "भुक्तानी सम्पन्न",
      status_payment_failed: "भुक्तानी असफल",
      status_qr_generated: "क्यूआर तयार",
      status_signature_pending: "हस्ताक्षर बाँकी",
      status_signature_completed: "हस्ताक्षर सम्पन्न",
      status_biometrics_pending: "बायोमेट्रिक बाँकी",
      status_biometrics_verified: "बायोमेट्रिक प्रमाणित",
      status_biometrics_failed: "बायोमेट्रिक असफल",
      status_active: "सक्रिय",
      status_expired: "म्याद सकिएको",
      status_unknown: "अज्ञात",

      // Document Types
      doc_citizenship: "नागरिकता प्रमाणपत्र",
      doc_nid: "राष्ट्रिय परिचयपत्र (NID)",
      doc_photo: "राहदानी साइजको फोटो",
      doc_birth_cert: "जन्मदर्ता प्रमाणपत्र",
      doc_marriage_cert: "विवाह दर्ता प्रमाणपत्र",
      doc_old_passport: "पुरानो राहदानी",
      doc_other: "अन्य आवश्यक कागजात",

      // Workflow Tracker Steps
      wf_application: "आवेदन",
      wf_documents: "कागजात",
      wf_verification: "प्रमाणीकरण",
      wf_payment: "भुक्तानी",
      wf_signature: "हस्ताक्षर",
      wf_queue: "लाम टोकन",
      wf_completed: "सम्पन्न",

      // Hero Section
      hero_badge: "नेपाल सरकारको आधिकारिक पोर्टल",
      hero_title_1: "विद्युतीय राहदानी आवेदन तथा",
      hero_title_2: "डिजिटल लाम व्यवस्थापन",
      hero_desc: "अनलाइनबाट फाराम भर्नुहोस्, डिजिटल प्रमाणीकरण सम्पन्न गर्नुहोस्, र आफ्नो आधिकारिक भर्चुअल ई-राहदानी तत्काल प्राप्त गर्नुहोस्। पूर्णतया डिजिटल, छरितो र सुरक्षित प्रणाली।",
      quick_lookup_title: "आवेदन स्थिति द्रुत खोजी",
      quick_lookup_placeholder: "आवेदन नम्बर प्रविष्ट गर्नुहोस् (उदा: १)",

      // Showcase Box
      showcase_title: "भर्चुअल ई-राहदानी नेपाल",
      showcase_badge: "१००% डिजिटल",
      showcase_feat_1_title: "तत्काल भर्चुअल जारी",
      showcase_feat_1_desc: "प्रमाणीकरण पूरा हुनासाथ तपाईंको डिजिटल राहदानी पोर्टलमा तुरुन्तै तयार हुन्छ।",
      showcase_feat_2_title: "सुरक्षित क्यूआर प्रमाणीकरण",
      showcase_feat_2_desc: "कुनै पनि समय आफ्नो भर्चुअल राहदानी डिजिटल माध्यमबाट प्रस्तुत र प्रमाणीकरण गर्न सक्नुहुन्छ।",
      showcase_feat_3_title: "प्रत्यक्ष डिजिटल लाम ट्र्याकिङ",
      showcase_feat_3_desc: "तपाईंको कागजात समीक्षा र प्रमाणीकरणको प्रत्यक्ष सूचना प्राप्त गर्नुहोस्।",
      digital_support: "डिजिटल सहायता:",

      // Statistics
      stat_passports: "जारी भर्चुअल राहदानी",
      stat_districts: "समर्थित जिल्लाहरू",
      stat_wait: "तत्काल डिजिटल पहुँच",
      stat_flow: "कागजविहीन डिजिटल प्रणाली",

      // 9-Step Process
      process_title: "९-चरणीय डिजिटल आवेदन तथा प्रमाणीकरण यात्रा",
      process_subtitle: "सबै कार्यहरू डिजिटल रूपमा हुन्छन् — आवेदन भर्नुहोस्, प्रमाणीकरण गर्नुहोस् र कागजविहीन भर्चुअल राहदानी प्रयोग गर्नुहोस्।",
      step1_title: "१. अनलाइन दर्ता",
      step1_desc: "आफ्नो वैध व्यक्तिगत विवरण, इमेल र मोबाइल नम्बर प्रयोग गरी नागरिक प्रोफाइल बनाउनुहोस्।",
      step2_title: "२. आवेदन फाराम भर्नुहोस्",
      step2_desc: "सही व्यक्तिगत तथा ठेगाना सम्बन्धी विवरणहरू भरी डिजिटल फाराम पूरा गर्नुहोस्।",
      step3_title: "३. कागजात अपलोड",
      step3_desc: "नागरिकता प्रमाणपत्र तथा आवश्यक प्रमाणहरूको स्पष्ट डिजिटल प्रतिलिपि अपलोड गर्नुहोस्।",
      step4_title: "४. डिजिटल लाम टोकन",
      step4_desc: "फाराम दर्ता पश्चात स्वचालित रूपमा निर्धारित समय सहितको डिजिटल टोकन प्राप्त गर्नुहोस्।",
      step5_title: "५. दस्तुर निर्धारण",
      step5_desc: "राहदानी प्रकार (३४ पृष्ठ / ६६ पृष्ठ / द्रुत सेवा) अनुसार तोकिएको दस्तुर विवरण यकिन गर्नुहोस्।",
      step6_title: "६. डिजिटल बायोमेट्रिक मिलान",
      step6_desc: "तपाईंको डिजिटल फोटो तथा बायोमेट्रिक्स विवरण राष्ट्रिय परिचयपत्र प्रणालीसँग प्रमाणीकरण गरिन्छ।",
      step7_title: "७. अधिकृत प्रमाणीकरण",
      step7_desc: "प्रमाणीकरण अधिकृतले पेश गरिएका डिजिटल कागजातहरूको परीक्षण तथा स्वीकृति प्रदान गर्दछ।",
      step8_title: "८. सरकारी डिजिटल हस्ताक्षर",
      step8_desc: "स्वीकृति पश्चात, तपाईंको भर्चुअल ई-राहदानीलाई नेपाल सरकारको आधिकारिक डिजिटल हस्ताक्षर तथा क्रिप्टोग्राफिक प्रमाणपत्रद्वारा प्रमाणीकरण गरिन्छ।",
      step9_title: "९. भर्चुअल राहदानी तयार",
      step9_desc: "आफ्नो नागरिक पोर्टलबाट कुनै पनि समय सक्रिय भर्चुअल ई-राहदानी हेर्न र प्रयोग गर्न सक्नुहुन्छ।",

      // Tariffs
      tariff_title: "राहदानीका प्रकार तथा दस्तुर विवरण",
      tariff_subtitle: "नेपाल सरकार, परराष्ट्र मन्त्रालयद्वारा निर्धारित आधिकारिक दस्तुर दरहरू।",
      tier1_title: "साधारण ई-राहदानी (३४ पृष्ठ)",
      tier1_desc: "सामान्य यात्रु, विद्यार्थी तथा पर्यटकहरूको लागि उपयुक्त।",
      tier1_price: "रु. ५,००० / नियमित सेवा",
      tier2_title: "साधारण ई-राहदानी (६६ पृष्ठ)",
      tier2_desc: "व्यावसायिक तथा बारम्बार विदेश भ्रमण गर्ने यात्रुहरूका लागि।",
      tier2_price: "रु. १०,००० / नियमित सेवा",
      tier3_title: "द्रुत (इमर्जेन्सी) सेवा",
      tier3_desc: "उपचार तथा विशेष आकस्मिक प्रयोजनका लागि प्राथमिकता सेवा।",
      tier3_price: "रु. १२,००० / द्रुत सेवा",
      btn_apply_34: "३४ पृष्ठको लागि आवेदन",
      btn_apply_66: "६६ पृष्ठको लागि आवेदन",
      btn_apply_urgent: "द्रुत सेवा आवेदन",

      // CTA Banner
      cta_title: "के तपाईं नेपाली ई-राहदानीको लागि तयार हुनुहुन्छ?",
      cta_desc: "२ मिनेटमै अनलाइन दर्ता गर्नुहोस्, कागजात पेश गर्नुहोस् र आफ्नो डिजिटल राहदानी प्राप्त गर्नुहोस्।",

      // Footer
      footer_about_title: "राहदानी विभाग",
      footer_about_desc: "नेपालमा ई-राहदानी सेवाका लागि आधिकारिक डिजिटल आवेदन तथा स्मार्ट लाम व्यवस्थापन प्रणाली।",
      footer_services_title: "नागरिक सेवाहरू",
      footer_hours_title: "अनलाइन पोर्टल उपलब्धता",
      footer_hours_status: "२४ घण्टा ७ दिन खुला",
      footer_hours_desc: "जुनसुकै समय र स्थानबाट आवेदन दिनुहोस्, कागजात अपलोड गर्नुहोस् र स्थिति हेर्नुहोस्।",
      footer_hours_badge: "✅ १००% डिजिटल तथा कागजविहीन",
      footer_support_title: "डिजिटल सहायता",
      footer_rights: "© २०२६ राहदानी विभाग, नेपाल सरकार। सर्वाधिकार सुरक्षित।",

      // Auth Pages
      signin_title: "साइन इन (लग-इन)",
      signin_subtitle: "नागरिक तथा प्रशासनिक एकीकृत पहुँच",
      signin_btn: "खातामा प्रवेश गर्नुहोस्",
      register_title: "नागरिक दर्ता",
      register_btn: "नयाँ खाता खोल्नुहोस्",
      email_label: "इमेल ठेगाना",
      password_label: "पासवर्ड",
      confirm_password_label: "पासवर्ड पुष्टि गर्नुहोस्",
      fullname_label: "पूरा कानुनी नाम",
      phone_label: "मोबाइल नम्बर",
      dob_label: "जन्म मिति",
      gender_label: "लिङ्ग",
      address_label: "स्थायी ठेगाना",
      login_identifier_label: "इमेल ठेगाना वा प्रयोगकर्ता नाम",
      login_identifier_placeholder: "उदा: citizen@example.com वा प्रयोगकर्ता नाम",
      password_placeholder: "आफ्नो खाताको पासवर्ड प्रविष्ट गर्नुहोस्",
      forgot_password: "पासवर्ड बिर्सनुभयो?",
      remember_me: "यस डिभाइसमा सम्झिराख्नुहोस्",
      no_account_yet: "नागरिक खाता छैन?",
      already_have_account: "पहिले नै दर्ता भइसक्नुभएको छ?",
      login_here: "यहाँ लग-इन गर्नुहोस्",
      session_expired_msg: "तपाईंको सत्र समाप्त भएको छ। कृपया पुनः लग-इन गर्नुहोस्।",

      // Track Page
      track_page_title: "प्रत्यक्ष राहदानी आवेदन ट्र्याकिङ",
      track_page_desc: "आफ्नो आधिकारिक आवेदन सन्दर्भ नम्बर वा लाम टोकन नम्बर प्रविष्ट गरी प्रक्रियागत स्थिति हेर्नुहोस्।",
      track_input_placeholder: "उदा: १ वा NP-१२३४५",
      stage_submitted: "आवेदन पेश भयो",
      stage_submitted_desc: "अनलाइन फाराम प्राप्त भयो",
      stage_review: "कागजात समीक्षा तथा बायोमेट्रिक्स",
      stage_review_desc: "राष्ट्रिय परिचयपत्र प्रणालीसँग मिलान",
      stage_approved: "अधिकृत प्रमाणीकरण तथा स्वीकृति",
      stage_approved_desc: "सुरक्षा तथा योग्यता प्रमाणीकरण सम्पन्न",
      stage_completed: "भर्चुअल ई-राहदानी जारी",
      stage_completed_desc: "डिजिटल रूपमा प्रमाणित र पोर्टलमा उपलब्ध",
      queue_assignment_title: "लाम टोकन विवरण",
      token_badge_label: "टोकन",
      no_queue_token: "अहिलेसम्म लाम टोकन जारी भएको छैन।",

      // Applicant Portal — Sidebars
      side_citizen_services: "नागरिक सेवाहरू",
      side_dashboard: "ड्यासबोर्ड",
      side_my_application: "मेरो आवेदन",
      side_documents: "कागजातहरू",
      side_queue_token: "लाम टोकन",
      side_notifications: "सूचनाहरू",
      side_track_status: "स्थिति हेर्नुहोस्",
      side_account: "खाता",
      side_my_profile: "मेरो प्रोफाइल",
      side_back_home: "गृहपृष्ठमा फर्कनुहोस्",
      side_logout: "लग-आउट",

      // Applicant Dashboard
      dash_welcome: "स्वागत छ,",
      dash_welcome_sub: "आफ्नो राहदानी आवेदन व्यवस्थापन गर्नुहोस्, प्रमाणीकरण स्थिति हेर्नुहोस्, र भर्चुअल ई-राहदानी प्राप्त गर्नुहोस्।",
      dash_active_app_banner: "सक्रिय राहदानी आवेदन",
      dash_active_app_desc: "तपाईंको आवेदन डिजिटल प्रमाणीकरण प्रक्रियामा छ।",
      dash_view_progress: "प्रगति हेर्नुहोस्",
      dash_workflow_tracker: "आवेदन प्रक्रिया ट्र्याकर",
      dash_current_action: "प्रक्रियागत सिफारिस",
      dash_total_apps: "जम्मा आवेदनहरू",
      dash_active_token: "सक्रिय लाम टोकन",
      dash_docs_verified: "प्रमाणित कागजात",
      dash_payment_status: "भुक्तानी स्थिति",
      dash_my_passports: "मेरो आधिकारिक राहदानी",
      dash_passport_badge: "बायोमेट्रिक प्रमाणीकृत",
      dash_issued_on: "जारी मिति:",
      dash_valid_until: "म्याद बहाल:",
      dash_download_pdf: "प्रमाणपत्र पीडीएफ डाउनलोड",
      dash_expired_notice: "तपाईंको राहदानीको म्याद समाप्त भएको छ। तपाईं राहदानी नवीकरणको लागि योग्य हुनुहुन्छ।",
      dash_apps_history: "आवेदन इतिहास",
      dash_apply_new: "राहदानीको लागि आवेदन दिनुहोस्",
      dash_no_active_app: "कुनै सक्रिय आवेदन छैन",
      dash_no_active_app_desc: "तपाईंले अहिलेसम्म राहदानी आवेदन पेश गर्नुभएको छैन। केही मिनेटमै अनलाइन सुरु गर्नुहोस्।",
      dash_start_application: "राहदानी आवेदन सुरु गर्नुहोस्",

      // Application Form
      app_form_title: "विद्युतीय राहदानी आवेदन फाराम",
      app_form_subtitle: "नेपाल सरकार • राहदानी विभाग आधिकारिक फाराम",
      app_sec_category: "१. राहदानीको प्रकार तथा सेवा",
      app_sec_personal: "२. व्यक्तिगत तथा परिचय विवरण",
      app_sec_parents: "३. पारिवारिक तथा आपतकालीन सम्पर्क",
      app_category_34: "साधारण ई-राहदानी (३४ पृष्ठ) - रु. ५,०००",
      app_category_66: "साधारण ई-राहदानी (६६ पृष्ठ) - रु. १०,०००",
      app_category_urgent: "द्रुत इमर्जेन्सी सेवा (३४ पृष्ठ) - रु. १२,०००",
      app_delivery_std: "नियमित कार्यालय संकलन",
      app_delivery_express: "द्रुत कार्यालय संकलन",
      app_fathers_name: "बुबाको पूरा नाम",
      app_mothers_name: "आमाको पूरा नाम",
      app_spouse_name: "पति/पत्नीको पूरा नाम (ऐच्छिक)",
      app_emergency_name: "आपतकालीन सम्पर्क व्यक्ति",
      app_emergency_rel: "नाता",
      app_emergency_phone: "आपतकालीन सम्पर्क नम्बर",
      app_declaration: "म यसद्वारा प्रमाणित गर्दछु कि यस फाराममा दिइएका सम्पूर्ण विवरणहरू सत्य, पूर्ण र सही छन्। झुट्टा विवरण वा कागजात पेश गर्नु नेपालको राहदानी ऐन बमोजिम दण्डनीय हुनेछ।",
      app_declaration_agree: "म माथि उल्लिखित वैधानिक घोषणा स्वीकार गर्दछु",
      app_existing_active_warning: "तपाईंको पहिले नै एक सक्रिय आवेदन प्रक्रियामा छ। उक्त आवेदन नसकिएसम्म अर्को आवेदन पेश गर्न सकिँदैन।",

      // Documents Page
      docs_page_title: "कागजात तयारी तथा प्रमाणीकरण",
      docs_page_subtitle: "आफ्ना सरकारी प्रमाणपत्रहरूको स्पष्ट डिजिटल प्रतिलिपि अपलोड गर्नुहोस्।",
      docs_select_app: "राहदानी आवेदन छान्नुहोस्",
      docs_upload_heading: "आवश्यक कागजात अपलोड",
      docs_select_type: "कागजात प्रकार छान्नुहोस्",
      docs_drag_drop: "फाइल यहाँ तानेर ल्याउनुहोस् वा ब्राउज गर्नुहोस्",
      docs_format_hint: "समर्थित ढाँचा: PDF, JPG, JPEG, PNG (अधिकतम १० MB)",
      docs_photo_card_title: "अनिवार्य राहदानी साइजको फोटो",
      docs_photo_card_desc: "सादा हल्का पृष्ठभूमिसहितको हालसालै खिचिएको डिजिटल फोटो अपलोड गर्नुहोस्।",
      docs_uploaded_list: "यस आवेदनका लागि पेश गरिएका कागजातहरू",
      docs_no_docs_yet: "यस आवेदनको लागि कुनै कागजात अपलोड गरिएको छैन।",

      // Queue Page
      queue_page_title: "स्मार्ट डिजिटल लाम टोकन",
      queue_page_subtitle: "राहदानी प्रमाणीकरणको प्रत्यक्ष लाम स्थिति तथा काउन्टर विवरण।",
      queue_current_ticket: "तपाईंको आधिकारिक लाम टोकन",
      queue_token_prefix: "टोकन नं.",
      queue_assigned_counter: "तोकिएको काउन्टर",
      queue_people_ahead_desc: "लाममा तपाईं भन्दा अगाडि रहेका सेवाग्राही",
      queue_wait_desc: "अनुमानित प्रतीक्षा समय",
      queue_live_board: "प्रत्यक्ष काउन्टर बोर्ड",
      queue_no_token_yet: "कुनै सक्रिय लाम टोकन फेला परेन।",
      queue_no_token_desc: "कागजातहरू अपलोड र समीक्षा भएपछि स्वचालित रूपमा टोकन उपलब्ध गराइनेछ।",
      queue_info_pages_fee: "पृष्ठ र दस्तुर",
      queue_info_token_date: "टोकन मिति",
      queue_info_time_slot: "समय स्लट",
      queue_info_called_at: "बोलाएको समय",
      queue_attend_note: "कृपया तोकिएको समय स्लटमा राहदानी कार्यालयमा उपस्थित भई यो टोकन नम्बर प्रस्तुत गर्नुहोस्।",
      queue_stage_progress: "लाम चरण प्रगति",
      queue_step_waiting_desc: "टोकन जारी गरिएको छ, तपाईंको पालोको प्रतीक्षा",
      queue_step_called_desc: "तपाईंको टोकन बोलाइएको छ",
      queue_step_serving_desc: "हाल कर्मचारीद्वारा प्रक्रियामा",
      queue_step_completed_desc: "प्रक्रिया सम्पन्न",
      queue_all_tokens: "सबै लाम टोकनहरू",
      queue_today: "आज",
      queue_standard_queue: "साधारण लाम",
      queue_not_yet_called: "अहिलेसम्म बोलाइएको छैन",
      queue_load_error: "लाम जानकारी लोड गर्न सकिएन। कृपया पुनः प्रयास गर्नुहोस्।",

      // Staff Portal
      staff_dash_title: "कर्मचारी प्रमाणीकरण डेस्क",
      staff_dash_subtitle: "प्रत्यक्ष सेवाग्राही निरीक्षण, कागजात प्रमाणीकरण तथा लाम नियन्त्रण।",
      staff_desk_assigned: "तपाईंको काउन्टर डेस्क",
      staff_active_token_title: "हाल सेवामा रहेको टोकन",
      staff_no_active_token: "काउन्टरमा हाल कुनै सेवाग्राही छैन।",
      staff_stat_served: "आज सेवा दिइएको",
      staff_stat_waiting: "लाममा प्रतीक्षारत",
      staff_stat_verified: "प्रमाणित कागजात",
      staff_stat_pending_apps: "लम्बित आवेदनहरू",
      staff_inspection_alert: "कागजात निरीक्षण अनिवार्य: कागजात स्वीकृत गर्नुपूर्व तपाईंले 'कागजात फाइल निरीक्षण गर्नुहोस्' मा क्लिक गरी सक्कल फाइल हेर्नु अनिवार्य छ।",
      staff_doc_inspection_title: "कागजात समीक्षा तथा निरीक्षण",
      staff_verify_bio_btn: "डिजिटल बायोमेट्रिक मिलान गर्नुहोस्",
      staff_bio_status_label: "बायोमेट्रिक स्थिति:",

      // Admin Portal
      admin_dash_title: "प्रशासकीय नियन्त्रण केन्द्र",
      admin_dash_subtitle: "समग्र प्रणाली स्थिति, जारी तथ्याङ्क, कर्मचारी व्यवस्थापन तथा अडिट लगहरू।",
      admin_stat_total_apps: "कुल आवेदनहरू",
      admin_stat_active_staff: "सक्रिय कर्मचारी डेस्क",
      admin_stat_verified_payments: "प्रमाणित भुक्तानी",
      admin_stat_total_revenue: "कुल संकलित राजस्व",
      admin_stat_completed_passports: "जारी राहदानी",
      admin_nav_apps: "आवेदनहरू",
      admin_nav_staff: "कर्मचारी व्यवस्थापन",
      admin_nav_payments: "राजस्व अडिट",
      admin_nav_reports: "प्रतिवेदन तथा विश्लेषण",
      admin_nav_logs: "प्रणाली गतिविधि लग",
      admin_add_staff: "नयाँ कर्मचारी थप्नुहोस्",
      admin_staff_table_title: "राहदानी विभाग कर्मचारी सूची",
      admin_recent_apps_title: "हालै प्राप्त राहदानी आवेदनहरू",

      // Admin Extra
      admin_sidebar_system: "प्रणाली व्यवस्थापन",
      admin_sidebar_overview: "प्रणाली सिंहावलोकन",
      admin_sidebar_portals: "सार्वजनिक पोर्टलहरू",
      admin_live_system: "प्रत्यक्ष प्रणाली",
      admin_stat_all_time: "संपूर्ण पेश गरिएका",
      admin_stat_requires_processing: "प्रक्रिया आवश्यक",
      admin_stat_verified_issued: "प्रमाणित र जारी",
      admin_apps_title: "केन्द्रीय आवेदन दर्ता किताब",
      admin_apps_subtitle: "देशभरका सबै राहदानी आवेदनहरू खोज्नुहोस्, निरीक्षण गर्नुहोस् र व्यवस्थापन गर्नुहोस्।",
      admin_payments_title: "दस्तुर भुक्तानी तथा वित्तीय अडिट",
      admin_payments_subtitle: "सबै आवेदन दस्तुर भुक्तानीहरूको अडिट, ट्र्याकिङ तथा मिलान गर्नुहोस्।",
      admin_staff_management_title: "राहदानी कार्यालय कर्मचारी पञ्जीका",
      admin_staff_management_subtitle: "प्रमाणीकरण अधिकृत, काउन्टर तोक्ने कार्य र कर्मचारी खाताहरू व्यवस्थापन गर्नुहोस्।",
      admin_reports_title: "प्रणाली प्रतिवेदन तथा विश्लेषण",
      admin_reports_subtitle: "राहदानी वितरण, लाम र कार्यालयको कार्यसम्पादन सम्बन्धी विस्तृत विश्लेषण।",
      admin_logs_title: "केन्द्रीय प्रणाली गतिविधि तथा अडिट लगहरू",
      admin_logs_subtitle: "प्रशासकीय कार्यहरू, स्थिति परिवर्तन र सुरक्षा गतिविधिहरूको स्थायी, कालक्रमानुसार अडिट लगहरू।",
      admin_record_manual_note: "म्यानुअल अडिट टिपोट दर्ता गर्नुहोस्",
      admin_audit_trail: "अडिट विवरण",
      admin_super_admin: "प्रमुख प्रशासक पहुँच",
      admin_registry_badge: "प्रत्यक्ष दर्ता",
      admin_total_payments: "कुल भुक्तानी",
      admin_verified_revenue: "प्रमाणित राजस्व",
      admin_pending_payments: "लम्बित भुक्तानी",
      admin_failed_refunded: "असफल / अपूर्ण",
      admin_export_csv: "CSV निर्यात",
      admin_filter_status: "स्थिति फिल्टर",
      admin_filter_all: "सबै स्थिति",
      admin_filter_pending: "लम्बित",
      admin_filter_verified: "प्रमाणित",
      admin_filter_approved: "स्वीकृत",
      admin_filter_rejected: "अस्वीकृत",

      // Staff Dashboard Extra
      staff_sidebar_operations: "कार्यसञ्चालन",
      staff_sidebar_queue_verify: "लाम र प्रमाणीकरण",
      staff_sidebar_waiting_roster: "प्रतीक्षा सूची",
      staff_sidebar_queue: "लाम व्यवस्थापन",
      staff_sidebar_verify: "कागजात प्रमाणीकरण",
      staff_queue_title: "प्रत्यक्ष लाम व्यवस्थापन",
      staff_queue_subtitle: "आफ्नो काउन्टरमा प्रत्यक्ष लाम व्यवस्थापन तथा नियन्त्रण गर्नुहोस्।",
      staff_verify_title: "कागजात प्रमाणीकरण डेस्क",
      staff_verify_subtitle: "आवेदकले पेश गरेका कागजातहरूको निरीक्षण, जाँच तथा प्रमाणीकरण गर्नुहोस्।",
      staff_live_badge: "प्रत्यक्ष",
      staff_desk_title: "डिजिटल प्रमाणीकरण र लाम डेस्क",
      staff_desk_active: "डेस्क सक्रिय",
      staff_desk_subtitle: "नागरिक आवेदनहरूको समीक्षा, डिजिटल कागजात प्रमाणीकरण र भर्चुअल ई-राहदानी जारी गर्नुहोस्।",
      staff_sync_queue: "लाम सिंक गर्नुहोस्",
      staff_currently_serving: "हाल सेवामा रहेको टोकन",
      staff_no_token_called: "कुनै टोकन बोलाइएको छैन",
      staff_awaiting_citizen: "अर्को नागरिकको प्रतीक्षामा",
      staff_stat_waiting_desc: "प्रमाणीकरणको प्रतीक्षामा",
      staff_stat_pending_desc: "आवेदनहरू लम्बित",
      staff_stat_verified_desc: "प्रमाणित फाइलहरू",
      staff_stat_served_desc: "प्रक्रिया र प्रमाणित",
      staff_active_apps_title: "सक्रिय आवेदन र प्रमाणीकरण लाम",
      staff_col_token_ref: "टोकन / सन्दर्भ",
      staff_col_applicant: "आवेदकको विवरण",
      staff_col_doc_type: "कागजातको प्रकार",
      staff_col_file: "फाइल कागजात",
      staff_modal_title: "आवेदन समीक्षा र प्रमाणीकरण डेस्क",
      staff_biometrics_match: "बायोमेट्रिक मिलान",
      staff_uploaded_credentials: "अपलोड गरिएका प्रमाणपत्रहरू",
      staff_biometrics_stage: "चरण ६: डिजिटल बायोमेट्रिक मिलान",
      staff_biometrics_desc: "राष्ट्रिय परिचयपत्र डेटाबेससँग अनुहार र औंठाछापको प्रमाणीकरण।",
      staff_bio_verify_btn: "बायोमेट्रिक प्रमाणित गर्नुहोस्",
      staff_bio_fail_btn: "बायोमेट्रिक असफल चिन्ह लगाउनुहोस्",
      staff_signature_stage: "चरण ८ र ९: सरकारी डिजिटल हस्ताक्षर र जारी",
      staff_signature_desc: "यो चरण अधिकृत गर्दा RSA-SHA256 डिजिटल प्रमाणपत्र जारी हुन्छ र भर्चुअल ई-राहदानी उत्पन्न हुन्छ।",
      staff_authorize_btn: "डिजिटल हस्ताक्षर अधिकृत गरी स्वीकृत गर्नुहोस्",
      staff_close_workspace: "कार्यक्षेत्र बन्द गर्नुहोस्",

      // Dashboards & Virtual Passport
      virtual_passport_title: "आधिकारिक भर्चुअल ई-राहदानी",
      vp_gov_header: "नेपाल सरकार • Government of Nepal",
      vp_doc_title: "राहदानी • PASSPORT",
      vp_verified_badge: "बायोमेट्रिक प्रमाणीकृत",
      vp_label_name: "पूरा नाम / Full Name",
      vp_label_pass_no: "राहदानी नं. / Passport No.",
      vp_label_nationality: "राष्ट्रियता / Nationality",
      vp_label_dob: "जन्म मिति / Date of Birth",
      vp_label_gender: "लिङ्ग / Gender",
      vp_label_issue: "जारी मिति / Date of Issue",
      vp_label_expiry: "म्याद सकिने मिति / Date of Expiry",
      vp_label_authority: "जारी गर्ने निकाय / Authority",
      vp_authority_val: "राहदानी विभाग, नेपाल",

      // Dynamic Toast & Error Messages
      msg_doc_verified: "कागजात सफलतापूर्वक प्रमाणित गरियो।",
      msg_doc_rejected: "कागजात अस्वीकृत गरिएको छ।",
      msg_doc_uploaded: "कागजात सफलतापूर्वक अपलोड गरियो।",
      msg_app_approved: "आवेदन सफलतापूर्वक स्वीकृत गरियो।",
      msg_app_submitted: "आवेदन सफलतापूर्वक पेश गरियो।",
      msg_payment_success: "भुक्तानी सफलतापूर्वक सम्पन्न भयो।",
      msg_payment_simulated: "स्यान्डबक्स परीक्षण भुक्तानी सम्पन्न भयो।",
      msg_token_called: "अर्को टोकन सफलतापूर्वक बोलाइयो।",
      msg_token_serving: "टोकन सेवामा चिन्हित गरियो।",
      msg_token_completed: "टोकन सेवा सम्पन्न भयो।",
      msg_token_skipped: "टोकन छुटाइयो।",
      msg_staff_created: "नयाँ कर्मचारी सफलतापूर्वक थपियो।",
      msg_copied: "क्लिपबोर्डमा कपी गरियो!",
      msg_inspection_required: "कागजात निरीक्षण अनिवार्य: कृपया पहिले वास्तविक फाइल निरीक्षण गर्नुहोस्।",
      err_active_application: "तपाईंको सक्रिय राहदानी आवेदन पहिले नै प्रक्रियामा छ। अर्को पेश गर्न सकिँदैन।",
      err_active_passport: "तपाईंसँग पहिले नै सक्रिय मान्य राहदानी छ। म्याद सकिएपछि मात्र नवीकरण गर्न सकिन्छ।",
      err_expired_apply_renewal: "तपाईंको पुरानो राहदानीको म्याद समाप्त भएको छ। कृपया नवीकरण प्रक्रिया मार्फत आवेदन दिनुहोस्।",
      err_missing_photo: "प्रमाणित राहदानी साइजको फोटो अनिवार्य छ।",
      err_missing_citizenship: "प्रमाणित नागरिकता प्रमाणपत्र वा राष्ट्रिय परिचयपत्र आवश्यक छ।",
      err_unverified_docs: "राहदानी स्वीकृतिपूर्व सबै पेश गरिएका कागजातहरू प्रमाणित हुनुपर्छ।",
      err_network: "इन्टरनेट कनेक्सनमा समस्या भयो। कृपया आफ्नो नेटवर्क जाँच्नुहोस्।",
      err_generic: "अनुरोध प्रक्रिया गर्दा त्रुटि भयो।",
      processing_please_wait: "प्रक्रिया हुँदैछ, कृपया प्रतीक्षा गर्नुहोस्...",

      // Notifications Page
      notif_page_subtitle: "तपाईंको राहदानी आवेदनका बारेमा अद्यावधिक र सूचनाहरू।",
      notif_mark_all_read: "सबै पढिएको चिन्ह लगाउनुहोस्",
      notif_unread: "नपढिएको",
      notif_read: "पढिएको",
      notif_load_error: "सूचनाहरू लोड गर्न सकिएन",
      notif_retry_hint: "कृपया आफ्नो कनेक्सन जाँच्नुहोस् र पुनः प्रयास गर्नुहोस्।",
      notif_no_unread: "कुनै नपढिएको सूचना छैन।",
      notif_no_read: "कुनै पढिएको सूचना छैन।",
      notif_none_yet: "अहिलेसम्म कुनै सूचना छैन।",
      notif_appear_here: "तपाईंको आवेदनका बारेमा सूचनाहरू यहाँ देखिनेछन्।",
      notif_all_already_read: "सबै सूचनाहरू पहिले नै पढिएको छ।",
      notif_marked_all_read: "सबै सूचनाहरू पढिएको चिन्ह लगाइयो।",
      notif_mark_all_error: "सबै पढिएको चिन्ह लगाउन सकिएन। कृपया पुनः प्रयास गर्नुहोस्।",

      // Profile Page
      profile_page_title: "मेरो प्रोफाइल",
      profile_page_subtitle: "आफ्नो नागरिक खाताको जानकारी हेर्नुहोस् र अद्यावधिक गर्नुहोस्।",
      profile_active_citizen: "सक्रिय नागरिक",
      profile_personal_info: "व्यक्तिगत जानकारी",
      profile_loading: "प्रोफाइल लोड हुँदैछ...",
      profile_email_helper: "लग-इनको लागि प्रयोग हुन्छ — परिवर्तनको लागि कार्यालयमा सम्पर्क गर्नुहोस्।",
      profile_save_changes: "परिवर्तन सुरक्षित गर्नुहोस्",
      profile_saving: "सुरक्षित हुँदैछ...",
      profile_cancel_edit: "सम्पादन रद्द गर्नुहोस्",
      profile_account_security: "खाता सुरक्षा",
      profile_password_label: "पासवर्ड",
      profile_password_last_changed: "पछिल्लो परिवर्तन: उपलब्ध छैन",
      profile_change_password: "पासवर्ड परिवर्तन गर्नुहोस्",
      profile_change_password_hint: "पासवर्ड परिवर्तन गर्न कृपया हटलाइनमा सम्पर्क गर्नुहोस्: १६६०-०१-००१२३।",
      profile_verified_label: "नागरिक खाता प्रमाणित",
      profile_verified_desc: "नेपाल राहदानी प्रणालीमा खाता दर्ता र सक्रिय छ",
      profile_load_error: "प्रोफाइल जानकारी लोड गर्न सकिएन।",
      profile_update_error: "प्रोफाइल अद्यावधिक गर्न सकिएन। कृपया पुनः प्रयास गर्नुहोस्।",
      profile_updated: "प्रोफाइल सफलतापूर्वक अद्यावधिक गरियो!",

      // Gender options
      gender_male: "पुरुष",
      gender_female: "महिला",
      gender_other: "अन्य",
    }
  },

  /**
   * Set active language and apply across DOM
   * @param {string} lang - 'en' or 'ne'
   */
  setLanguage(lang) {
    if (!['en', 'ne'].includes(lang)) lang = 'en';
    this.currentLang = lang;
    try {
      localStorage.setItem('passport_lang', lang);
    } catch (e) {
      console.warn('localStorage not accessible for passport_lang', e);
    }
    this.applyTranslations();
    this.updateToggleButtons();

    // Dispatch global event so dynamic pages and components can re-render immediately
    try {
      window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang } }));
    } catch {
      // Ignore if event dispatch fails
    }
  },

  /**
   * Toggle between EN and NE
   */
  toggle() {
    const nextLang = this.currentLang === 'en' ? 'ne' : 'en';
    this.setLanguage(nextLang);
  },

  /**
   * Get translation text by key with optional fallback
   * @param {string} key
   * @param {string} [fallback]
   */
  t(key, fallback = null) {
    if (!key) return '';
    const dict = this.translations[this.currentLang] || this.translations.en;
    if (dict && dict[key] !== undefined) return dict[key];
    if (this.translations.en && this.translations.en[key] !== undefined) return this.translations.en[key];
    return fallback !== null ? fallback : key;
  },

  /**
   * Translate backend or standard status strings to the current language
   * @param {string} status
   */
  translateStatus(status) {
    if (!status) return this.t('status_unknown', 'Unknown');
    const raw = String(status).trim();
    const lower = raw.toLowerCase();

    // Specific mapping table
    if (lower === 'pending') return this.t('status_pending', 'Pending');
    if (lower === 'under review' || lower === 'under_review' || lower === 'review') return this.t('status_under_review', 'Under Review');
    if (lower === 'approved') return this.t('status_approved', 'Approved');
    if (lower === 'rejected') return this.t('status_rejected', 'Rejected');
    if (lower === 'completed') return this.t('status_completed', 'Completed');
    if (lower === 'verified') return this.t('status_verified', 'Verified');
    if (lower === 'pending review' || lower === 'pending_review') return this.t('status_pending_review', 'Pending Review');
    if (lower === 'waiting') return this.t('status_waiting', 'Waiting');
    if (lower === 'called') return this.t('status_called', 'Called');
    if (lower === 'serving') return this.t('status_serving', 'Serving');
    if (lower === 'skipped') return this.t('status_skipped', 'Skipped');
    if (lower === 'active') return this.t('status_active', 'ACTIVE');
    if (lower === 'expired') return this.t('status_expired', 'EXPIRED');
    if (lower.includes('payment') && lower.includes('pending')) return this.t('status_payment_pending', 'Payment Pending');
    if (lower.includes('payment') && lower.includes('verifi')) return this.t('status_payment_verified', 'Payment Verified');
    if (lower.includes('payment') && lower.includes('fail')) return this.t('status_payment_failed', 'Payment Failed');
    if (lower === 'qr_generated') return this.t('status_qr_generated', 'QR Generated');
    if (lower.includes('signature') && lower.includes('pending')) return this.t('status_signature_pending', 'Signature Pending');
    if (lower.includes('signature') && (lower.includes('complet') || lower.includes('verifi'))) return this.t('status_signature_completed', 'Signature Completed');
    if (lower.includes('bio') && lower.includes('pending')) return this.t('status_biometrics_pending', 'Biometrics Pending');
    if (lower.includes('bio') && (lower.includes('match') || lower.includes('verifi'))) return this.t('status_biometrics_verified', 'Biometrics Verified');
    if (lower.includes('bio') && lower.includes('fail')) return this.t('status_biometrics_failed', 'Biometrics Failed');

    return raw;
  },

  /**
   * Translate document type names
   */
  translateDocType(docType) {
    if (!docType) return '';
    const lower = String(docType).toLowerCase();
    if (lower.includes('photo')) return this.t('doc_photo', 'Passport Photo');
    if (lower.includes('citizen')) return this.t('doc_citizenship', 'Citizenship Certificate');
    if (lower.includes('nid') || lower.includes('national id')) return this.t('doc_nid', 'National ID Card (NID)');
    if (lower.includes('birth')) return this.t('doc_birth_cert', 'Birth Registration Certificate');
    if (lower.includes('marriage')) return this.t('doc_marriage_cert', 'Marriage Certificate');
    if (lower.includes('passport')) return this.t('doc_old_passport', 'Previous Passport');
    return docType;
  },

  /**
   * Translate known backend error messages to current language
   */
  translateError(msg) {
    if (!msg) return this.t('err_generic', 'An error occurred.');
    const text = String(msg);
    if (text.includes('active passport application')) return this.t('err_active_application');
    if (text.includes('active valid passport') || text.includes('already have an active passport')) return this.t('err_active_passport');
    if (text.includes('previous passport has expired')) return this.t('err_expired_apply_renewal');
    if (text.includes('Passport Photo is mandatory')) return this.t('err_missing_photo');
    if (text.includes('Citizenship Certificate or National ID')) return this.t('err_missing_citizenship');
    if (text.includes('All documents must be verified')) return this.t('err_unverified_docs');
    if (text.includes('Network') || text.includes('Failed to fetch')) return this.t('err_network');
    if (text.includes('Inspection') || text.includes('visually inspected')) return this.t('msg_inspection_required');
    return text;
  },

  /**
   * Apply translations to all DOM elements marked with data-i18n attributes
   * @param {HTMLElement|Document} [root=document]
   */
  applyTranslations(root = document) {
    if (!root) return;
    const dict = this.translations[this.currentLang] || this.translations.en;

    // 1. Text elements [data-i18n]
    root.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (dict[key] !== undefined) {
        el.innerHTML = dict[key];
      }
    });

    // 2. Placeholders [data-i18n-placeholder]
    root.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (dict[key] !== undefined) {
        el.setAttribute('placeholder', dict[key]);
      }
    });

    // 3. Titles / Tooltips [data-i18n-title]
    root.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      if (dict[key] !== undefined) {
        el.setAttribute('title', dict[key]);
      }
    });

    // 4. Aria Labels [data-i18n-aria-label]
    root.querySelectorAll('[data-i18n-aria-label]').forEach(el => {
      const key = el.getAttribute('data-i18n-aria-label');
      if (dict[key] !== undefined) {
        el.setAttribute('aria-label', dict[key]);
      }
    });

    // 5. Dynamic raw statuses [data-raw-status]
    root.querySelectorAll('[data-raw-status]').forEach(el => {
      const raw = el.getAttribute('data-raw-status');
      if (raw) {
        el.textContent = this.translateStatus(raw);
      }
    });

    // Update document HTML lang attribute
    if (typeof document !== 'undefined' && document.documentElement) {
      document.documentElement.lang = this.currentLang;
    }
  },

  /**
   * Update active button states in UI
   */
  updateToggleButtons() {
    if (typeof document === 'undefined') return;
    const isNe = this.currentLang === 'ne';
    document.querySelectorAll('.lang-btn-en').forEach(btn => {
      btn.classList.toggle('active', !isNe);
    });
    document.querySelectorAll('.lang-btn-ne').forEach(btn => {
      btn.classList.toggle('active', isNe);
    });
    document.querySelectorAll('.lang-current-label').forEach(el => {
      el.textContent = isNe ? 'नेपाली' : 'English';
    });
  },

  /**
   * Initialize i18n upon page load
   */
  init() {
    this.applyTranslations();
    this.updateToggleButtons();
  }
};

// Global exports
if (typeof window !== 'undefined') {
  window.I18n = I18n;
  window.t = (key, fallback) => I18n.t(key, fallback);

  // Auto initialize when DOM is loaded or immediately if already interactive
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => I18n.init());
  } else {
    I18n.init();
  }
}
