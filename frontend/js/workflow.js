/**
 * WorkflowManager — Serial Applicant Workflow Engine
 * Nepal Passport Office Management System
 *
 * Determines current step from backend state and drives sequential navigation.
 * Source of truth: /api/applications/current-workflow/
 */

class WorkflowManager {
  static _state = null;
  static _loading = false;
  static _listeners = [];

  /**
   * Sequential steps in order for the applicant-facing workflow.
   * Maps frontend step keys to human context.
   */
  static STEPS = [
    {
      key: 'application',
      label: 'Application',
      icon: 'description',
      description: 'Fill and submit your passport application',
    },
    {
      key: 'documents',
      label: 'Documents',
      icon: 'upload_file',
      description: 'Upload citizenship, NID, and photo',
    },
    {
      key: 'fee',
      label: 'Payment',
      icon: 'payments',
      description: 'Pay the statutory application fee',
    },
    {
      key: 'verification',
      label: 'Verification',
      icon: 'fact_check',
      description: 'Staff review and verification of documents',
    },
    {
      key: 'biometrics',
      label: 'Biometrics',
      icon: 'face',
      description: 'Complete biometric verification with an authorized officer',
    },
    {
      key: 'signature',
      label: 'Digital Signature',
      icon: 'draw',
      description: 'Government digital signature',
    },
    {
      key: 'queue',
      label: 'Queue / Processing',
      icon: 'confirmation_number',
      description: 'Queue token assignment and staff processing',
    },
    {
      key: 'passport_ready',
      label: 'Passport',
      icon: 'verified',
      description: 'Passport generation after processing completes',
    },
  ];

  /**
   * Single Central Workflow State Function
   * Authoritative calculation of the applicant's current active workflow step
   */
  static getCurrentWorkflowStep(state) {
    if (!state || !state.has_application) {
      return 'application';
    }

    const docSummary = state.document_summary || {};
    const totalDocs = docSummary.total || 0;
    const rejectedDocs = docSummary.rejected || 0;
    const verifiedDocs = docSummary.verified || 0;
    const pendingDocs = docSummary.pending || 0;

    // 1. Rejected documents take highest priority — applicant must correct
    if (rejectedDocs > 0 || (state.rejected_docs && state.rejected_docs.length > 0)) {
      return 'documents';
    }

    // 2. Documents missing entirely
    if (totalDocs === 0) {
      return 'documents';
    }

    // 2b. Mandatory passport photo check — must have photo (verified or pending)
    if (!state.has_photo) {
      return 'documents';
    }

    if (state.has_identity_document === false) {
      return 'documents';
    }

    // Required uploads unlock payment. Staff review starts only after the
    // payment gateway has verified the citizen's payment.
    const isPaymentVerified = (state.payment_status === 'VERIFIED') || (state.is_payment_verified === true);
    const isPaymentCompleted = isPaymentVerified ||
      (state.steps && state.steps.find(s => s.key === 'fee')?.status === 'Completed');

    if (!isPaymentCompleted) {
      return 'fee'; // Payment step
    }

    const allDocumentsVerified = totalDocs > 0 &&
      verifiedDocs === totalDocs && pendingDocs === 0 && rejectedDocs === 0;
    if (!allDocumentsVerified) {
      return 'verification';
    }

    // 5. Biometrics must be verified by an authorized staff member.
    const isBiometricsVerified = state.biometric_status === 'Verified' ||
      (state.steps && state.steps.find(s => s.key === 'biometrics')?.status === 'Completed');

    if (!isBiometricsVerified) {
      return 'biometrics';
    }

    // 6. Digital Signature stage: check if digital signature completed
    const isSigDone = state.is_signature_verified === true ||
      (state.steps && state.steps.find(s => s.key === 'signature')?.status === 'Completed');

    if (!isSigDone) {
      return 'signature'; // Digital Signature step
    }

    // 7. Queue stage remains active until staff processing is completed.
    const queueToken = state.queue_token;
    if (!queueToken || queueToken.queue_status !== 'Completed') {
      return 'queue';
    }

    // 8. Completed / Virtual Passport Ready
    return 'passport_ready';
  }

  /**
   * Step unlock rules — maps a step key to the condition that must be true
   * to consider the step accessible. These are evaluated from backend data.
   */
  static _isStepAccessible(stepKey, state) {
    if (!state || !state.has_application) {
      return stepKey === 'application';
    }
    const currentStep = this.getCurrentWorkflowStep(state);
    const ORDER = ['application', 'documents', 'fee', 'verification', 'biometrics', 'signature', 'queue', 'passport_ready'];
    
    let target = stepKey;
    if (target === 'payment') target = 'fee';
    if (target === 'tracking' || target === 'completed') target = 'passport_ready';

    const targetIdx = ORDER.indexOf(target);
    const currentIdx = ORDER.indexOf(currentStep);

    if (targetIdx === -1) return true;
    return targetIdx <= currentIdx;
  }

  /**
   * Load workflow state from the API. Caches for the session.
   */
  static async load(force = false) {
    if (this._state && !force) return this._state;
    if (force) {
      this._loading = false;
      const oldListeners = this._listeners;
      this._listeners = [];
      oldListeners.forEach((fn) => { try { fn(null); } catch (_) {} });
    } else if (this._loading) {
      return new Promise((resolve) => {
        this._listeners.push(resolve);
      });
    }
    this._loading = true;
    try {
      const data = await API.get('/applications/current-workflow/');
      this._state = data;
      this._loading = false;
      const listeners = this._listeners;
      this._listeners = [];
      listeners.forEach((fn) => { try { fn(data); } catch (_) {} });
      return data;
    } catch (err) {
      this._loading = false;
      const listeners = this._listeners;
      this._listeners = [];
      listeners.forEach((fn) => { try { fn(null); } catch (_) {} });
      console.error('[WorkflowManager] Failed to load workflow state:', err.message);
      return null;
    }
  }

  /**
   * Invalidate cached state (call after any state-changing action).
   */
  static invalidate() {
    this._state = null;
    this._loading = false;
    const oldListeners = this._listeners;
    this._listeners = [];
    oldListeners.forEach((fn) => { try { fn(null); } catch (_) {} });
  }

  /**
   * Get the current workflow state (must have called load() first).
   */
  static getState() {
    return this._state;
  }

  /**
   * Get the current step key from loaded state.
   */
  static getCurrentStep() {
    return this.getCurrentWorkflowStep(this._state);
  }

  /**
   * Check if the applicant can access a given step.
   */
  static canAccess(stepKey) {
    return this._isStepAccessible(stepKey, this._state);
  }

  /**
   * Page guard: call at the top of each applicant page.
   * If the applicant should not be here, redirect to dashboard with a message.
   * @param {string} pageStepKey - The step this page represents
   */
  static async guardPage(pageStepKey) {
    if (!Auth.requireAuth(['citizen', 'applicant'])) return false;
    const state = await this.load();
    if (!state) return true; // Let page handle its own error
    if (!this._isStepAccessible(pageStepKey, state)) {
      const current = this.getCurrentWorkflowStep(state);
      console.warn(`[WorkflowManager] Step '${pageStepKey}' not accessible (current: ${current}). Redirecting to dashboard.`);
      window.location.href = `/applicant/dashboard/?step_blocked=${pageStepKey}`;
      return false;
    }
    return true;
  }

  /**
   * Compute "Next Step" card content from the current workflow state.
   */
  static getNextStepCard(state) {
    if (!state) return null;
    const isNe = (typeof I18n !== 'undefined' && I18n.currentLang === 'ne');

    if (!state.has_application) {
      return {
        type: 'start_application',
        title: isNe ? 'आफ्नो राहदानी आवेदन सुरु गर्नुहोस्' : 'Start Your Passport Application',
        description: isNe ? 'आधिकारिक प्रक्रिया सुरु गर्न आफ्नो राहदानी आवेदन विवरण भर्नुहोस्।' : 'Fill in your passport application details to begin the official process.',
        buttonLabel: isNe ? 'आवेदन सुरु गर्नुहोस्' : 'Start Application',
        buttonAction: 'openNewApplicationModal()',
        buttonUrl: null,
        icon: 'note_add',
        color: 'primary',
      };
    }

    const step = this.getCurrentWorkflowStep(state);

    // Rejected photo — show specific re-upload card
    if (state.photo_rejected) {
      return {
        type: 'photo_rejected',
        title: isNe ? 'कारबाही आवश्यक: राहदानी फोटो अस्वीकृत भयो' : 'Action Required: Passport Photo Rejected',
        description: isNe
          ? `तपाईंको राहदानी आकारको फोटो अस्वीकृत भयो। कारण: "${state.photo_rejection_reason || 'मापदण्ड पुगेन'}"। कृपया सेतो पृष्ठभूमि भएको स्पष्ट फोटो पुनः अपलोड गर्नुहोस्।`
          : `Your passport-size photograph was rejected. Reason: "${state.photo_rejection_reason || 'Does not meet requirements'}". Please re-upload a clear, white-background photo.`,
        buttonLabel: isNe ? 'फोटो पुनः अपलोड गर्नुहोस्' : 'Re-upload Passport Photo',
        buttonAction: null,
        buttonUrl: '/applicant/documents/',
        icon: 'no_photography',
        color: 'error',
      };
    }

    // Rejected documents — highest priority
    if (state.rejected_docs && state.rejected_docs.length > 0) {
      return {
        type: 'rejected_documents',
        title: isNe ? 'कारबाही आवश्यक: कागजातहरू अस्वीकृत भए' : 'Action Required: Documents Rejected',
        description: isNe
          ? `${state.rejected_docs.length} कागजात अस्वीकृत भए। कृपया सच्याएर पुनः अपलोड गर्नुहोस्।`
          : `${state.rejected_docs.length} document(s) were rejected. Please re-upload with corrections.`,
        buttonLabel: isNe ? 'कागजात पुनः अपलोड गर्नुहोस्' : 'Re-upload Documents',
        buttonAction: null,
        buttonUrl: '/applicant/documents/',
        icon: 'error',
        color: 'error',
        rejectedDocs: state.rejected_docs,
      };
    }

    // Passport photo missing — applicant must upload
    if (state.has_application && !state.has_photo) {
      return {
        type: 'photo_required',
        title: isNe ? 'कारबाही आवश्यक: राहदानी फोटो आवश्यक छ' : 'Action Required: Passport Photo Missing',
        description: isNe
          ? 'अगाडि बढ्नको लागि तपाईंले राहदानी आकारको फोटो (सेतो पृष्ठभूमि, JPG/PNG, अधिकतम ५MB) अपलोड गर्नुपर्छ।'
          : 'You must upload a passport-size photograph (white background, JPG/PNG, max 5MB) before proceeding. This is mandatory for passport issuance.',
        buttonLabel: isNe ? 'फोटो अपलोड गर्नुहोस् →' : 'Upload Passport Photo →',
        buttonAction: null,
        buttonUrl: `/applicant/documents/?application_id=${state.application_id}&photo=1`,
        icon: 'add_a_photo',
        color: 'warning',
      };
    }

    switch (step) {
      case 'application':
        return {
          type: 'fill_application',
          title: isNe ? 'आफ्नो आवेदन पूरा गर्नुहोस्' : 'Complete Your Application',
          description: isNe ? 'तपाईंको राहदानी आवेदन लम्बित छ। कृपया आवश्यक विवरणहरू भर्नुहोस्।' : 'Your passport application is pending. Please fill in the required details.',
          buttonLabel: isNe ? 'आवेदन भर्नुहोस्' : 'Fill Application',
          buttonAction: 'openNewApplicationModal()',
          buttonUrl: null,
          icon: 'description',
          color: 'primary',
        };

      case 'documents':
        return {
          type: 'upload_documents',
          title: isNe ? 'आवश्यक कागजात अपलोड गर्नुहोस्' : 'Upload Required Documents',
          description: isNe ? `आवेदन पेश गरियो। अब आफ्नो नागरिकता, राष्ट्रिय परिचयपत्र र फोटो अपलोड गर्नुहोस्।` : `Application #${state.reference} submitted. Now upload your Citizenship Certificate, NID, and photo.`,
          buttonLabel: isNe ? 'कागजात अपलोडमा जानुहोस् →' : 'Continue to Document Upload →',
          buttonAction: null,
          buttonUrl: `/applicant/documents/?application_id=${state.application_id}`,
          icon: 'upload_file',
          color: 'primary',
        };

      case 'verification': {
        const docSummary = state.document_summary || {};
        return {
          type: 'awaiting_verification',
          title: isNe ? 'कागजात पुनरावलोकनमा' : 'Documents Under Review',
          description: (typeof I18n !== 'undefined')
            ? I18n.format('workflow_documents_review_after_payment_desc', 'Payment is confirmed. {count} document(s) are awaiting officer verification.', { count: docSummary.total || 0 })
            : `Payment is confirmed. ${docSummary.total || 0} document(s) are awaiting officer verification.`,
          buttonLabel: isNe ? 'स्थिति हेर्नुहोस्' : 'View Status',
          buttonAction: null,
          buttonUrl: '/applicant/documents/',
          icon: 'hourglass_top',
          color: 'secondary',
          isWaiting: true,
        };
      }

      case 'fee': {
        const fee = state.fee_amount || 5000;
        const cardDesc = (typeof I18n !== 'undefined')
          ? I18n.format(
              'workflow_payment_after_upload_desc',
              'Your required documents are uploaded. Pay NPR {amount} so staff verification can begin.',
              { amount: parseFloat(fee).toLocaleString() }
            )
          : `Your required documents are uploaded. Pay NPR ${parseFloat(fee).toLocaleString()} so staff verification can begin.`;

        if (state.payment_status === 'QR_GENERATED' || state.payment_status === 'PENDING') {
          return {
            type: 'complete_payment',
            title: isNe ? 'भुक्तानी पूरा गर्नुहोस्' : 'Complete Your Payment',
            description: isNe ? `रु. ${parseFloat(fee).toLocaleString()} को क्यूआर तयार छ। भुक्तानी गर्नुहोस् वा परीक्षण सिमुलेट गर्नुहोस्।` : `Payment QR generated for NPR ${parseFloat(fee).toLocaleString()}. Scan or simulate to verify payment.`,
            buttonLabel: isNe ? 'भुक्तानी जारी राख्नुहोस्' : 'Continue Payment',
            buttonAction: 'openPaymentPanel()',
            buttonUrl: null,
            icon: 'qr_code',
            color: 'warning',
            paymentReference: state.payment_reference,
          };
        }
        return {
          type: 'initiate_payment',
          title: isNe ? 'दस्तुर भुक्तानी गर्नुहोस्' : 'Pay Application Fee',
          description: cardDesc,
          buttonLabel: isNe ? 'दस्तुर भुक्तानी गर्नुहोस्' : 'Pay Application Fee',
          buttonAction: 'openPaymentPanel()',
          buttonUrl: null,
          icon: 'payments',
          color: 'primary',
          feeAmount: fee,
        };
      }

      case 'biometrics': {
        const biometricFailed = state.biometric_status === 'Failed';
        return {
          type: 'awaiting_biometrics',
          title: (typeof I18n !== 'undefined')
            ? I18n.t(biometricFailed ? 'workflow_biometrics_failed_title' : 'workflow_biometrics_waiting_title', biometricFailed ? 'Biometric Verification Failed' : 'Awaiting Biometric Verification')
            : (biometricFailed ? 'Biometric Verification Failed' : 'Awaiting Biometric Verification'),
          description: biometricFailed
            ? ((typeof I18n !== 'undefined') ? I18n.t('workflow_biometrics_failed_desc', 'The biometric match was unsuccessful. Please contact the passport office for another supervised capture.') : 'The biometric match was unsuccessful. Please contact the passport office for another supervised capture.')
            : ((typeof I18n !== 'undefined') ? I18n.t('workflow_biometrics_waiting_desc', 'Your payment is verified. An authorized staff member must complete biometric verification before issuance.') : 'Your payment is verified. An authorized staff member must complete biometric verification before issuance.'),
          buttonLabel: (typeof I18n !== 'undefined') ? I18n.t('btn_refresh_status', 'Refresh Status') : 'Refresh Status',
          buttonAction: null,
          buttonUrl: null,
          icon: biometricFailed ? 'face_retouching_off' : 'face',
          color: biometricFailed ? 'error' : 'secondary',
          isWaiting: true,
        };
      }

      case 'signature':
        return {
          type: 'awaiting_signature',
          title: isNe ? 'डिजिटल हस्ताक्षर' : 'Digital Signature',
          description: isNe ? 'भुक्तानी र बायोमेट्रिक्स प्रमाणित भयो। सरकारी अधिकृतको हस्ताक्षर प्रतीक्षामा छ।' : 'Payment and biometrics are verified. An authorized officer must now issue the government digital signature.',
          buttonLabel: isNe ? 'स्थिति रिफ्रेस गर्नुहोस्' : 'Refresh Status',
          buttonAction: null,
          buttonUrl: null,
          icon: 'draw',
          color: 'primary',
          isWaiting: true,
        };

      case 'queue': {
        const qt = state.queue_token;
        if (qt) {
          const qStatus = (typeof I18n !== 'undefined' && I18n.translateStatus) ? I18n.translateStatus(qt.queue_status) : qt.queue_status;
          return {
            type: 'view_queue',
            title: isNe ? 'तपाईंको लाम टोकन' : 'Your Queue Token',
            description: isNe ? `टोकन T-${String(qt.token_number).padStart(3, '0')} जारी भयो। प्रक्रिया स्थिति: ${qStatus}` : `Processing token T-${String(qt.token_number).padStart(3, '0')} assigned. Status: ${qStatus}`,
            buttonLabel: isNe ? 'लाम टोकन हेर्नुहोस्' : 'View Queue Token',
            buttonAction: null,
            buttonUrl: '/applicant/queue/',
            icon: 'confirmation_number',
            color: 'success',
            queueToken: qt,
          };
        }
        return {
          type: 'awaiting_queue',
          title: isNe ? 'लाम टोकन निर्धारण' : 'Queue Token Assignment',
          description: isNe ? 'डिजिटल हस्ताक्षर प्रमाणीकरण भयो। प्रशोधन टोकन तयार गरिँदैछ।' : 'Digital signature authorized. Assigning your processing token.',
          buttonLabel: isNe ? 'लाम टोकन हेर्नुहोस्' : 'View Queue Token',
          buttonAction: null,
          buttonUrl: '/applicant/queue/',
          icon: 'hourglass_top',
          color: 'secondary',
          isWaiting: true,
        };
      }

      case 'passport_ready':
        return {
          type: 'passport_ready',
          title: isNe ? '🎉 राहदानी तयार' : '🎉 Passport Ready',
          description: isNe ? `आवेदन स्वीकृत र आधिकारिक रूपमा डिजिटल प्रमाणित भयो। आफ्नो भर्चुअल ई-राहदानी डाउनलोड गर्नुहोस्।` : `Application #${state.reference} approved and digitally certified. Download your official Virtual e-Passport.`,
          buttonLabel: isNe ? 'पीडीएफ डाउनलोड' : 'Download PDF',
          buttonAction: 'downloadVirtualPassport()',
          buttonUrl: null,
          icon: 'badge',
          color: 'success',
        };
    }

    return null;
  }

  /**
   * Render the horizontal progress tracker HTML for a given state.
   */
  static renderProgressTracker(state) {
    const effectiveState = state || { has_application: false, current_step: 'application' };
    const ORDER = ['application', 'documents', 'fee', 'verification', 'biometrics', 'signature', 'queue', 'passport_ready'];
    let currentKey = this.getCurrentWorkflowStep(effectiveState);
    
    let currentIdx = ORDER.indexOf(currentKey);
    if (currentIdx === -1) currentIdx = 0;

    return this.STEPS.map((step, idx) => {
      let stateClass = 'upcoming';
      let iconName = 'radio_button_unchecked';

      if (idx < currentIdx) {
        stateClass = 'completed';
        iconName = 'check_circle';
      } else if (idx === currentIdx) {
        stateClass = 'current';
        iconName = step.icon;
      } else {
        stateClass = 'upcoming';
        iconName = 'radio_button_unchecked';
      }

      // Special: rejected docs always flags error on documents step
      if (step.key === 'documents' && state.rejected_docs && state.rejected_docs.length > 0) {
        stateClass = 'error';
        iconName = 'error';
      }

      const connector = idx < this.STEPS.length - 1
        ? `<div class="wf-connector ${idx < currentIdx ? 'wf-connector-done' : ''}"></div>`
        : '';

      const stepKey = `wf_${step.key === 'fee' ? 'payment' : (step.key === 'passport_ready' ? 'completed' : step.key)}`;
      const stepLabel = (typeof I18n !== 'undefined' && I18n.t) ? I18n.t(stepKey, step.label) : step.label;
      const stepDescriptionKey = `wf_desc_${step.key === 'fee' ? 'payment' : (step.key === 'passport_ready' ? 'completed' : step.key)}`;
      const stepDescription = (typeof I18n !== 'undefined' && I18n.t) ? I18n.t(stepDescriptionKey, step.description) : step.description;

      return `
        <div class="wf-step wf-step-${stateClass}" title="${stepDescription}">
          <div class="wf-step-icon">
            <span class="material-symbols-outlined">${iconName}</span>
          </div>
          <div class="wf-step-label" data-i18n="${stepKey}">${stepLabel}</div>
        </div>
        ${connector}
      `;
    }).join('');
  }
}

// Global export for central use across all scripts
window.WorkflowManager = WorkflowManager;
window.getCurrentWorkflowStep = (state) => WorkflowManager.getCurrentWorkflowStep(state);
