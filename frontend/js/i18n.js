/**
 * ==========================================================================
 * BILINGUAL TRANSLATION ENGINE (ENGLISH / नेपाली)
 * Official Language Localization for Nepal Department of Passports Portal
 * ==========================================================================
 */

const I18n = {
  currentLang: localStorage.getItem('passport_lang') || 'en',

  translations: {
    en: {
      // Topbar & Brand
      gov_motto: "Government of Nepal • Ministry of Foreign Affairs • Department of Passports",
      toll_free: "Toll Free: 1660-01-00123",
      location: "Tripureshwor, Kathmandu",
      brand_title: "Department of Passports",
      brand_subtitle: "Government of Nepal • Smart Portal",
      
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

      // Hero Section
      hero_badge: "Official Government of Nepal Portal",
      hero_title_1: "Passport Application &",
      hero_title_2: "Queue Management",
      hero_desc: "Apply online, complete seamless digital verification, and access your verified Virtual e-Passport directly on your device. Instant, secure, and 100% paperless passport services for all Nepali citizens.",
      btn_apply_now: "Apply for Digital Passport",
      btn_track_status: "Track Status",
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
      btn_create_account: "Create Citizen Account",

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
      register_btn: "Create Account",
      email_label: "Email Address",
      password_label: "Password",
      fullname_label: "Full Legal Name",
      phone_label: "Phone Number",
      dob_label: "Date of Birth",
      gender_label: "Gender",
      address_label: "Permanent Address",

      // Dashboards & Virtual Passport
      virtual_passport_title: "Official Virtual e-Passport",
      btn_print_save: "Print / Save",
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
    },

    ne: {
      // Topbar & Brand
      gov_motto: "नेपाल सरकार • परराष्ट्र मन्त्रालय • राहदानी विभाग",
      toll_free: "निःशुल्क हटलाइन: १६६०-०१-००१२३",
      location: "त्रिपुरेश्वर, काठमाडौं",
      brand_title: "राहदानी विभाग",
      brand_subtitle: "नेपाल सरकार • डिजिटल राहदानी सेवा प्रणाली",

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

      // Hero Section
      hero_badge: "नेपाल सरकारको आधिकारिक पोर्टल",
      hero_title_1: "विद्युतीय राहदानी आवेदन तथा",
      hero_title_2: "डिजिटल लाम व्यवस्थापन",
      hero_desc: "अनलाइनबाट फाराम भर्नुहोस्, डिजिटल प्रमाणीकरण सम्पन्न गर्नुहोस्, र आफ्नो आधिकारिक भर्चुअल ई-राहदानी तत्काल प्राप्त गर्नुहोस्। पूर्णतया डिजिटल, छरितो र सुरक्षित प्रणाली।",
      btn_apply_now: "डिजिटल राहदानी आवेदन दिनुहोस्",
      btn_track_status: "आवेदन स्थिति हेर्नुहोस्",
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
      btn_create_account: "नयाँ नागरिक खाता खोल्नुहोस्",

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
      fullname_label: "पूरा कानुनी नाम",
      phone_label: "मोबाइल नम्बर",
      dob_label: "जन्म मिति",
      gender_label: "लिङ्ग",
      address_label: "स्थायी ठेगाना",

      // Dashboards & Virtual Passport
      virtual_passport_title: "आधिकारिक भर्चुअल ई-राहदानी",
      btn_print_save: "प्रिन्ट / सुरक्षित गर्नुहोस्",
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
    }
  },

  /**
   * Set active language and apply across DOM
   * @param {string} lang - 'en' or 'ne'
   */
  setLanguage(lang) {
    if (!['en', 'ne'].includes(lang)) lang = 'en';
    this.currentLang = lang;
    localStorage.setItem('passport_lang', lang);
    this.applyTranslations();
    this.updateToggleButtons();
  },

  /**
   * Toggle between EN and NE
   */
  toggle() {
    const nextLang = this.currentLang === 'en' ? 'ne' : 'en';
    this.setLanguage(nextLang);
  },

  /**
   * Get translation text by key
   */
  t(key) {
    const dict = this.translations[this.currentLang] || this.translations.en;
    return dict[key] || this.translations.en[key] || key;
  },

  /**
   * Apply translations to all DOM elements marked with data-i18n
   */
  applyTranslations() {
    const dict = this.translations[this.currentLang] || this.translations.en;

    // 1. Text elements
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (dict[key]) {
        el.innerHTML = dict[key];
      }
    });

    // 2. Placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (dict[key]) {
        el.setAttribute('placeholder', dict[key]);
      }
    });

    // 3. Titles / Tooltips
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      if (dict[key]) {
        el.setAttribute('title', dict[key]);
      }
    });

    // Update document HTML lang attribute
    document.documentElement.lang = this.currentLang;
  },

  /**
   * Update active button states in UI
   */
  updateToggleButtons() {
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

// Auto initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  I18n.init();
});
