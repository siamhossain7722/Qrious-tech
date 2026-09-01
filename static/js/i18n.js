/**
 * Qrious Solution — Universal English (EN) & Bangla (BN) i18n Translation Engine
 */

const phraseMap = {
    // Reviews Section & Inner HTML Node Splits
    "Trusted By Leaders In": "শীর্ষ টেক লিডারদের দ্বারা বিশ্বস্ত:",
    "USA, UAE, Saudi Arabia & Bangladesh": "ইউএসএ, ইউএই, সৌদি আরব ও বাংলাদেশ",
    "Impactful feedback from enterprise agency clients worldwide & certified tech graduates in Bangladesh.": "বিশ্বব্যাপী এন্টারপ্রাইজ ক্লায়েন্ট এবং বাংলাদেশের ভেরিফাইড গ্র্যাজুয়েটদের অভিজ্ঞতা।",

    // Testimonial Quotes
    "Their AI automation expertise is unmatched. The custom Playwright web scraper & Gemini integration saved our team 200+ manual hours every month.": "তাদের এআই অটোমেশন দক্ষতা অনন্য। কাস্টম প্লেরাইট ওয়েব স্ক্র্যাপার এবং জেমিনি ইন্টিগ্রেশন আমাদের টিমের প্রতি মাসে ২০০+ ঘণ্টার কাজ সাশ্রয় করেছে।",
    "Qrious Solution engineered our multi-tenant SaaS platform in record time. The code quality, speed, and scaling architecture on AWS are world-class!": "কিউরিয়াস সলিউশন রেকর্ড সময়ে আমাদের সাবস্ক্রিপশন বিলিংসহ মাল্টি-টেন্যান্ট সাস প্ল্যাটফর্মটি তৈরি করে দিয়েছে। এডব্লিউএস ক্লাউড স্কেলিং আর্কিটেকচার সত্যিই ওয়ার্ল্ড-ক্লাস!",
    "The LinkedIn Autonomous AI Agent transformed our executive hiring pipeline. Submitting targeted applications with Gemini AI cover letters yielded 5x more interview calls.": "লিংকডইন অটোমেটেড এআই এজেন্ট আমাদের এক্সিকিউটিভ নিয়োগ প্রক্রিয়াকে সম্পূর্ণ সহজ করে দিয়েছে। জেমিনি কভার লেটার দিয়ে আবেদন করায় আমরা ৫ গুণ বেশি ইন্টারভিউ কল পেয়েছি।",
    "Outstanding full-stack development and security. They delivered our enterprise web portal and mobile app with flawless precision.": "চমৎকার ফুল-স্ট্যাক ডেভেলপমেন্ট এবং সিকিউরিটি ব্যবস্থা। তারা নিখুঁতভাবে আমাদের এন্টারপ্রাইজ ওয়েব পোর্টাল এবং মোবাইল অ্যাপ ডেলিভারি করেছে।",
    "Fast execution, 100% transparent 1-week sprints, and exceptional UI/UX. Highest recommendation for any serious business!": "দ্রুত ডেলিভারি, ১০০% স্বচ্ছ ১-সপ্তাহের স্প্রিন্ট এবং অসাধারণ ইউআই/ইউএক্স। যেকোনো ব্যবসার জন্য সর্বোচ্চ সুপারিশ থাকবে!",
    "The Django REST Framework and React modules were mind-blowing. Building real SaaS products gave me the confidence to win freelance clients globally.": "জ্যাঙ্গো রেস্ট ফ্রেমওয়ার্ক এবং রিয়্যাক্ট মডিউল অসাধারণ ছিল। রিয়েল সাস প্রোডাক্ট তৈরির অভিজ্ঞতা আমাকে আন্তর্জাতিক ক্লায়েন্ট পাওয়ার আত্মবিশ্বাস দিয়েছে।",
    "Qrious Solution rebuilt our e-commerce platform with Next.js and Django. Our conversion rate increased by 40% in the first month!": "কিউরিয়াস সলিউশন আমাদের ই-কমার্স প্ল্যাটফর্মটি নেক্সট.জেএস এবং জ্যাঙ্গো দিয়ে নতুনভাবে তৈরি করে দিয়েছে। প্রথম মাসেই আমাদের সেলস ৪০% বৃদ্ধি পেয়েছে!",
    "The 10-person small batch mentorship in the Full-Stack Bootcamp was life-changing. I landed a Junior Software Engineer job within 3 weeks of graduation!": "ফুল-স্ট্যাক বুটক্যাম্পের ১০ জনের স্মল ব্যাচ মেন্টরশিপ অত্যন্ত কার্যকর ছিল। কোর্স শেষের ৩ সপ্তাহের মধ্যেই আমি জুনিয়র সফটওয়্যার ইঞ্জিনিয়ার হিসেবে কাজ শুরু করেছি!",
    "Practical 100% project-based training on FB Ads, Copywriting & AI Chatbots. Now I run a successful digital agency serving international clients!": "ফেসবুক এডস, কপিরাইটিং এবং এআই চ্যাটবটের উপর ১০০% প্র্যাকটিক্যাল প্রজেক্ট-বেসড ট্রেনিং। এখন আমি আন্তর্জাতিক ক্লায়েন্টদের সেবা দিচ্ছি!",

    "Product Director, Apex Labs": "প্রোডাক্ট ডিরেক্টর, অ্যাপেক্স ল্যাবস",
    "CTO, NextGen Software": "সিটিও, নেক্সটজেন সফটওয়্যার",
    "Founder, GulfTech Ventures": "ফাউন্ডার, গালফটেক ভেঞ্চার্স",
    "VP Engineering, Riyadh Digital": "ভিপি ইঞ্জিনিয়ারিং, রিয়াদ ডিজিটাল",
    "MD, CloudTech Ltd": "এমডি, ক্লাউডটেক লিমিটেড",
    "Full-Stack Dev Graduate": "ফুল-স্ট্যাক ডেভ গ্র্যাজুয়েট",
    "Digital Growth Graduate": "ডিজিটাল গ্রোথ গ্র্যাজুয়েট",
    "CEO, Oasis E-Commerce": "সিইও, ওয়েসিস ই-কমার্স",

    // Footer Section
    "Engineering high-impact Web Applications, Mobile Apps, SaaS Platforms, and Autonomous AI Agents. Empowering global businesses & training future tech leaders.": "হাই-ইম্প্যাক্ট ওয়েব অ্যাপ্লিকেশন, মোবাইল অ্যাপস, সাস প্ল্যাটফর্ম এবং এআই এজেন্ট তৈরি করে বৈশ্বিক প্রতিষ্ঠান ও টেক লিডারদের সহায়তা করা।",
    "Contact & Agency": "যোগাযোগ ও এজেন্সি",
    "Email Support": "ইমেইল সাপোর্ট",
    "WhatsApp Direct": "হোয়াটসঅ্যাপ যোগাযোগ",
    "Headquarters": "প্রধান কার্যালয়",
    "UAE & International Global Agency": "ইউএই ও গ্লোবাল এজেন্সি",
    "© 2026 Qrious Solution. All rights reserved. Built for global innovation.": "© ২০২৬ কিউরিয়াস সলিউশন। সর্বস্বত্ব সংরক্ষিত। গ্লোবাল উদ্ভাবনের জন্য তৈরি।",
    "Book a Consultation": "পরামর্শ বুক করুন",
    "Contact Our Team": "আমাদের টিমের সাথে যোগাযোগ",
    "Email Us": "আমাদের ইমেইল করুন",
    "AI Job Agent": "এআই জব এজেন্ট",
    "About Qrious Solution": "আমাদের কিউরিয়াস সলিউশন",

    // Navigation & Header
    "Services": "সার্ভিসসমূহ",
    "AI Solutions": "এআই সলিউশন",
    "Courses": "কোর্সসমূহ",
    "About Us": "আমাদের সম্পর্কে",
    "Contact Us": "যোগাযোগ",
    "Websites & Web Apps": "ওয়েবসাইট ও ওয়েব অ্যাপস",
    "Mobile App Development": "মোবাইল অ্যাপ ডেভেলপমেন্ট",
    "SaaS Product Building": "সাস প্রোডাক্ট বিল্ডিং",
    "LinkedIn AI Job Apply Agent": "লিংকডইন এআই জব অ্যাপ্লাই এজেন্ট",
    "Digital Marketing Masterclass": "ডিজিটাল মার্কেটিং মাস্টারক্লাস",
    "Full-Stack Web Development": "ফুল-স্ট্যাক ওয়েব ডেভেলপমেন্ট",
    "Dashboard": "ড্যাশবোর্ড",
    "Sign In": "সাইন ইন",
    "Get Started →": "শুরু করুন →",

    // Hero Section
    "PROGRAMMING HERO OS • POWERED BY AUTONOMOUS AI AGENTS": "প্রোগ্রামিং হিরো ওএস • স্বয়ংক্রিয় এআই এজেন্টচালিত",
    "PROGRAMMING HERO OS MODULES": "প্রোগ্রামিং হিরো ওএস মডিউলসমূহ",
    "Become a Tech Hero & Automate Your Career": "টেক হিরো হন এবং নিজের ক্যারিয়ার অটোমেট করুন",
    "With Programming Hero OS": "প্রোগ্রামিং হিরো ওএস এর সাথে",
    "Master Full-Stack Web Development, Mobile Apps, and Enterprise SaaS Engineering — while deploying autonomous AI Job Agents that auto-apply to LinkedIn jobs 24/7 on autopilot.": "ফুল-স্ট্যাক ওয়েব ডেভেলপমেন্ট, মোবাইল অ্যাপস এবং এন্টারপ্রাইজ সফটওয়্যার ইঞ্জিনিয়ারিং শিখুন — সাথে ২৪/৭ লিঙ্কডইন চাকরিতে স্বয়ংক্রিয় আবেদনকারী এআই এজেন্ট উপভোগ করুন।",
    "Launch Hero Dashboard →": "হিরো ড্যাশবোর্ডে প্রবেশ করুন →",
    "Autonomous AI Agent": "স্বয়ংক্রিয় এআই এজেন্ট",
    "Explore Courses": "কোর্সসমূহ দেখুন",

    // Hero Ecosystem & Module Cards
    "Hero Software Engineering Ecosystem": "হিরো সফটওয়্যার ইঞ্জিনিয়ারিং ইকোসিস্টেম",
    "From requirement analysis and UI/UX prototyping to scalable cloud architecture, we build software products that drive business growth.": "রিকোয়ারমেন্ট অ্যানালিসিস এবং ইউআই/ইউএক্স প্রোটোটাইপিং থেকে স্কেলেবল ক্লাউড আর্কিটেকচার — আমরা ব্যবসা বৃদ্ধিতে সহায়তা করে এমন সফটওয়্যার প্রোডাক্ট তৈরি করি।",
    "Websites & Portals": "ওয়েবসাইট ও পোর্টাল",
    "High-performance marketing sites, web applications, custom CMS portals, and e-commerce platforms using React, Next.js, and Django.": "রিয়্যাক্ট, নেক্সট.জেএস এবং জ্যাঙ্গো ব্যবহার করে হাই-পারফরম্যান্স মার্কেটিং সাইট, ওয়েব অ্যাপ্লিকেশন, কাস্টম সিএমএস পোর্টাল এবং ই-কমার্স প্ল্যাটফর্ম।",
    "Mobile App Dev": "মোবাইল অ্যাপ ডেভেলপমেন্ট",
    "Native and cross-platform iOS & Android mobile apps built with Flutter, React Native, and robust cloud API backends.": "ফ্লাটার, রিয়্যাক্ট নেটিভ এবং ক্লাউড এপিআই ব্যাকএন্ড দিয়ে তৈরি নেটিভ এবং ক্রস-প্ল্যাটফর্ম আইওএস ও অ্যান্ড্রয়েড মোবাইল অ্যাপস।",
    "SaaS Products": "সাস প্রোডাক্টস",
    "Complete multi-tenant SaaS architecture including recurring subscription billing, customer dashboards, and real-time analytics.": "সাবস্ক্রিপশন বিলিং, কাস্টমার ড্যাশবোর্ড এবং রিয়েল-টাইম অ্যানালিটিক্সসহ সম্পূর্ণ মাল্টি-টেন্যান্ট সাস আর্কিটেকচার।",
    "AI Hero Agents": "এআই হিরো এজেন্টস",
    "Custom autonomous AI agents, Gemini LLM integrations, RAG pipelines, and automated bots that replace manual repetitive workflows.": "কাস্টম স্বয়ংক্রিয় এআই এজেন্ট, জেমিনি এলএলএম ইন্টিগ্রেশন, আরএজি পাইপলাইন এবং অটোমেটেড বট যা পুনরাবৃত্তিমূলক কাজ স্বয়ংক্রিয় করে।",

    // Flagship LinkedIn Agent Box
    "FLAGSHIP AUTONOMOUS AI HERO AGENT": "ফ্ল্যাগশিপ স্বয়ংক্রিয় এআই হিরো এজেন্ট",
    "LinkedIn Autonomous AI Job Apply Agent": "লিংকডইন অটোমেটেড এআই জব অ্যাপ্লাই এজেন্ট",
    "Our AI agent automatically searches LinkedIn jobs matching your exact criteria, parses your CV, generates tailored AI cover letters with Gemini, and submits Easy Apply applications 24/7 on auto-pilot.": "আমাদের এআই এজেন্ট স্বয়ংক্রিয়ভাবে আপনার ক্রাইটেরিয়া অনুযায়ী লিংকডইনে চাকরি খুঁজে বের করে, আপনার সিভি স্ক্যান করে, জেমিনি দিয়ে কভার লেটার তৈরি করে এবং ২৪/৭ স্বয়ংক্রিয়ভাবে ইজি অ্যাপ্লাই সম্পন্ন করে।",
    "Explore AI Job Agent →": "এআই জব এজেন্ট জানুন →",
    "Try Free (30 Apps/mo)": "ফ্রি ট্রায়াল দিন (৩০টি আবেদন/মাস)",
    "100% Automated LinkedIn Easy Apply Submissions & Application Tracker": "১০০% স্বয়ংক্রিয় লিংকডইন ইজি অ্যাপ্লাই আবেদন ও ট্র্যাকার",

    // Proven Process Section
    "HOW WE WORK": "আমাদের কাজের ধাপসমূহ",
    "Our Proven Development Process": "আমাদের নির্ভরযোগ্য ডেভেলপমেন্ট প্রসেস",
    "We follow a disciplined 4-step agile engineering blueprint to take your vision from discovery to global launch.": "আমরা আপনার ধারণাকে প্রাথমিক পরিকল্পনা থেকে সফল গ্লোবাল লঞ্চে রূপান্তর করতে চার ধাপের অ্যাজাইল ইঞ্জিনিয়ারিং অনুসরণ করি।",
    "Discovery & Blueprint": "আইডিয়া ও ডিজাইন ব্লুপ্রিন্ট",
    "We analyze business goals, define technical architecture, map database schemas, and create sprint roadmaps.": "আমরা ব্যবসায়িক লক্ষ্য বিশ্লেষণ করি, টেকনিক্যাল আর্কিটেকচার নির্ধারণ করি এবং স্প্রিন্ট রোডম্যাপ তৈরি করি।",
    "UI/UX & Prototyping": "ইউআই/ইউএক্স ও প্রোটোটাইপিং",
    "Designing modern glassmorphism interfaces and interactive prototypes tailored for optimal user experience.": "সেরা ইউজার অভিজ্ঞতার জন্য আধুনিক গ্লাসমরফিজম ইন্টারফেস এবং ইন্টারঅ্যাক্টিভ প্রোটোটাইপ ডিজাইন করা।",
    "Agile Dev & AI Testing": "অ্যাজাইল ডেভেলপমেন্ট ও এআই টেস্টিং",
    "Writing clean modular code, integrating REST/AI APIs, and executing continuous automated testing suite.": "ক্লিন মডুলার কোড লেখা, এআই এপিআই ইন্টিগ্রেশন এবং কন্টিনিউয়াস অটোমেটেড টেস্টিং চালনা করা।",
    "Cloud Launch & Scale": "ক্লাউড লঞ্চ ও স্কেলিং",
    "Deploying to scalable AWS/GCP cloud infrastructure with automated monitoring and 24/7 technical support.": "স্বয়ংক্রিয় মনিটরিং এবং ২৪/৭ টেকনিক্যাল সাপোর্টসহ এডব্লিউএস/জিসিপি ক্লাউড অবকাঠামোয় স্থাপন।",

    // Performance, Security & Scale Cards
    "WHY QRIOUS SOLUTION": "কেন কিউরিয়াস সলিউশন",
    "Built for Performance, Security & Scale": "পারফরম্যান্স, সিকিউরিটি ও স্কেলের জন্য তৈরি",
    "Why global businesses and founders choose us as their long-term software engineering partner.": "কেন বিশ্বমানের প্রতিষ্ঠান ও ফাউন্ডাররা আমাদের তাদের দীর্ঘমেয়াদী টেক পার্টনার হিসেবে বেছে নেন।",
    "Lightning Fast Speed": "সুপারফাস্ট স্পিড",
    "Optimized Core Web Vitals, microsecond database queries, and lightweight assets for maximum conversion rates.": "সর্বোচ্চ কনভার্সন রেটের জন্য অপ্টিমাইজড কোর ওয়েব ভাইটালস, সুপারফাস্ট ডাটাবেস কোয়েরি এবং লাইটওয়েট অ্যাসেট।",
    "Enterprise Security": "এন্টারপ্রাইজ সিকিউরিটি",
    "End-to-end data encryption, OWASP compliant security practices, role-based access control, and SSL protection.": "এন্ড-টু-এন্ড ডাটা এনক্রিপশন, ওডব্লিউএএসপি সিকিউরিটি মানদণ্ড, রোল-বেসড এক্সেস এবং এসএসএল সুরক্ষা।",
    "Scalable Architecture": "স্কেলেবল আর্কিটেকচার",
    "Cloud-native infrastructure ready to handle millions of active users without performance degradation.": "পারফরম্যান্স হ্রাস ছাড়াই লক্ষ লক্ষ সক্রিয় ব্যবহারকারী সামলাতে প্রস্তুত ক্লাউড-নেটিভ অবকাঠামো।",
    "Transparent ROI": "স্বচ্ছ বিয়োগফল ও মূল্য",
    "Clear fixed-price or sprint milestone contracts with no surprise fees and guaranteed milestone delivery.": "কোন সারপ্রাইজ ফি ছাড়াই স্পষ্ট ফিক্সড-প্রাইস বা স্প্রিন্ট মাইলস্টোন চুক্তি এবং সময়মত ডেলিভারির নিশ্চয়তা।",
    "AI-Native Expertise": "এআই-নেটিভ বিশেষজ্ঞতা",
    "Deep specialization in LLM integration, Gemini AI models, Playwright bot automation, and RAG pipelines.": "এলএলএম ইন্টিগ্রেশন, জেমিনি এআই মডেল, প্লেরাইট বট অটোমেশন এবং আরএজি পাইপলাইনে গভীর দক্ষতা।",
    "24/7 Dedicated Support": "২৪/৭ ডেডিকেটেড সাপোর্ট",
    "Direct access to lead engineers via WhatsApp, Email, and Phone for immediate technical support.": "তাৎক্ষণিক টেকনিক্যাল সাপোর্টের জন্য হোয়াটসঅ্যাপ, ইমেইল এবং ফোনের মাধ্যমে লিড ইঞ্জিনিয়ারদের সাথে যোগাযোগের সুবিধা।",

    // Training & Masterclasses
    "Industry Masterclasses & Training": "ইন্ডাস্ট্রি মাস্টারক্লাস ও ট্রেনিং",
    "Learn practical software engineering and digital growth skills from senior practitioners with verified certificates.": "ভেরিফাইড সার্টিফিকেটসহ অভিজ্ঞ টেক পেশাদারদের কাছ থেকে প্র্যাকটিক্যাল সফটওয়্যার ইঞ্জিনিয়ারিং ও ডিজিটাল গ্রোথ স্কিল শিখুন।",
    "Digital Marketing & Growth Mastery": "ডিজিটাল মার্কেটিং ও গ্রোথ মাস্টারি",
    "Master Search Engine Optimization (SEO), Meta & Google Ads performance marketing, conversion funnels, analytics, and social growth strategies.": "সার্চ ইঞ্জিন অপ্টিমাইজেশন (এসএইচও), মেটা ও গুগল এডস পারফরম্যান্স মার্কেটিং, কনভার্সন ফানেল এবং সোশ্যাল গ্রোথ স্ট্র্যাটেজিতে পারদর্শী হন।",
    "Full-Stack Web Development (Python & React)": "ফুল-স্ট্যাক ওয়েব ডেভেলপমেন্ট (পাইথন ও রিয়্যাক্ট)",
    "Build real-world web apps from scratch. Learn HTML, CSS, JavaScript, React, Python, Django, REST APIs, PostgreSQL, and Cloud Deployment.": "একদম শূন্য থেকে রিয়েল-ওয়ার্ল্ড ওয়েব অ্যাপস তৈরি করুন। এইচটিএমএল, সিএসএস, জাভাস্ক্রিপ্ট, রিয়্যাক্ট, জ্যাঙ্গো, এপিআই এবং ক্লাউড ডিপ্লয়মেন্ট শিখুন।",

    // HELP CENTER / FAQ
    "HELP CENTER": "হেল্প সেন্টার",
    "Have Question?": "প্রশ্ন আছে?",
    "We Have Answers": "আমাদের কাছে রয়েছে উত্তর",
    "Everything you need to know about Qrious Solution services, AI agents & courses.": "কিউরিয়াস সলিউশনের সেবা, এআই এজেন্ট এবং কোর্স সম্পর্কে বিস্তারিত জেনে নিন।",
    "Search FAQs...": "প্রশ্ন খুঁজুন...",
    "Most Asked": "সেরা প্রশ্নসমূহ",
    "Web & Apps": "ওয়েব ও অ্যাপস",
    "SaaS & AI": "সাস ও এআই",
    "Academy": "একাডেমি",
    "Security": "সিকিউরিটি",
    "Payment & Other": "পেমেন্ট ও অন্যান্য",
    "Most Asked Questions": "সর্বোচ্চ জিজ্ঞাসিত প্রশ্নসমূহ",
    "Top questions from our customers.": "আমাদের গ্রাহকদের সর্বাধিক জিজ্ঞাসিত প্রশ্ন।",
    "Live Chat": "লাইভ চ্যাট",
    "We reply in seconds": "কয়েক সেকেন্ডে উত্তর দেওয়া হয়",
    "WhatsApp Us": "হোয়াটসঅ্যাপ করুন",
    "Quick response (+971 566631501)": "দ্রুত সাড়া দিন (+971 566631501)",
    "STILL NEED HELP?": "এখনো সহায়তার প্রয়োজন?",
    "Our support team is available 24/7.": "আমাদের সাপোর্ট টিম ২৪/৭ প্রস্তুত রয়েছে।",
    "Avg. Response 1 Min": "গড় উত্তর সময় ১ মিনিট",

    // FAQ QUESTIONS & ANSWERS
    "How often can I use the LinkedIn AI Job Agent?": "আমি কত ঘন ঘন লিংকডইন এআই জব এজেন্ট ব্যবহার করতে পারব?",
    "Yes! Free plan users get 30 automated applications per month. Pro plan subscribers receive up to 1,000 automated Easy Apply submissions per month with automated CV parsing, Gemini AI cover letters, and live application tracking!": "হ্যাঁ! ফ্রি প্ল্যান ব্যবহারকারীরা মাসে ৩০টি স্বয়ংক্রিয় আবেদন পান। প্রোপ্ল্যান গ্রাহকরা সিভিউ স্ক্যান, জেমিনি কভার লেটার এবং লাইভ ট্র্যাকিং সহ মাসে ১,০০০টি ইজি অ্যাপ্লাই আবেদন পান!",

    "What technology stack do you use for Custom Web & Mobile Apps?": "কাস্টম ওয়েব ও মোবাইল অ্যাপের জন্য আপনারা কী টেকনোলজি ব্যবহার করেন?",
    "We build high-performance Web Apps using React, Next.js, Django Python, and PostgreSQL. For Mobile Apps, we specialize in cross-platform iOS & Android development using Flutter and React Native with cloud API backends.": "আমরা রিয়্যাক্ট, নেক্সট.জেএস, জ্যাঙ্গো এবং পোস্টগ্রেসকিউএল দিয়ে হাই-পারফরম্যান্স ওয়েব অ্যাপ তৈরি করি। মোবাইল অ্যাপের ক্ষেত্রে ফ্লাটার এবং রিয়্যাক্ট নেটিভ দিয়ে আইওএস ও অ্যান্ড্রয়েড অ্যাপ তৈরি করা হয়।",

    "Do you build complete multi-tenant SaaS products with billing?": "আপনারা কি সাবস্ক্রিপশন বিলিংসহ মাল্টি-টেন্যান্ট সাস প্রোডাক্ট তৈরি করেন?",
    "Yes! We engineer full multi-tenant SaaS platforms featuring recurring subscription billing (Stripe/PayPal), user role management, analytics dashboards, automated email notifications, and cloud deployment.": "হ্যাঁ! আমরা স্ট্রাইপ/পেপাল পেমেন্ট, রোল ম্যানেজমেন্ট, এনালিটিক্স ড্যাশবোর্ড এবং ক্লাউড ডিপ্লয়মেন্টসহ সম্পূর্ণ মাল্টি-টেন্যান্ট সাস প্ল্যাটফর্ম তৈরি করি।",

    "What is included in the Qrious Tech Academy courses?": "কিউরিয়াস টেক একাডেমির কোর্সে কী কী অন্তর্ভুক্ত রয়েছে?",
    "Our masterclasses include hands-on project training, live instructor sessions, verified downloadable certificates, and 1-on-1 career placement support for Full-Stack Web Dev and Digital Marketing Growth.": "আমাদের মাস্টারক্লাসে রয়েছে হ্যান্ডস-অন প্রজেক্ট ট্রেনিং, লাইভ ক্লাস, ভেরিফাইড সার্টিফিকেট এবং ফুল-স্ট্যাক ডেভ ও ডিজিটাল মার্কেটিংয়ের জন্য ১-অন-১ ক্যারিয়ার সাপোর্ট।",

    "Is client project data encrypted and secure?": "ক্লায়েন্টের প্রজেক্ট ডাটা কি এনক্রিপ্টেড এবং নিরাপদ?",
    "Absolutely. All source code, database records, and API credentials are protected with end-to-end SSL encryption, OWASP-compliant security protocols, and strict non-disclosure agreements (NDA).": "অবশ্যই। সকল সোর্স কোড, ডাটাবেস এবং এপিআই ক্রেডেনশিয়ালস এন্ড-টু-এন্ড এসএসএল এনক্রিপশন এবং ওডব্লিউএএসপি সিকিউরিটি প্রোটোকল দ্বারা সম্পূর্ণ সুরক্ষিত।",

    "What payment methods do you accept for agency projects?": "এজেন্সি প্রজেক্টের ক্ষেত্রে কী কী পেমেন্ট মাধ্যম গ্রহণযোগ্য?",
    "We accept Credit/Debit Cards, Wire Transfers, PayPal, and local bank transfers. We work on clear milestone-based sprint contracts with guaranteed project deliverables.": "আমরা ক্রেডিট/ডেবিট কার্ড, ওয়্যার ট্রান্সফার, পেপাল এবং লোকাল ব্যাংক ট্রান্সফার গ্রহণ করি। আমরা গ্যারান্টিড ডেলিভারিসহ মাইলস্টোন চুক্তিতে কাজ করি।",

    "Still couldn't find what you need?": "আপনার কাঙ্ক্ষিত প্রশ্নটি খুঁজে পাচ্ছেন না?",
    "Submit your query to our customer success team.": "আমাদের কাস্টমার সাকসেস টিমের কাছে আপনার প্রশ্নটি জমা দিন।",
    "Submit a Question": "প্রশ্ন জমা দিন",

    // CTA BANNER
    "Ready to Build Your Next Digital Product?": "আপনার পরবর্তী ডিজিটাল প্রোডাক্ট তৈরি করতে প্রস্তুত?",
    "Get in touch with our engineering team today to discuss custom Web, App, SaaS, or Autonomous AI Agent development.": "আজই আমাদের ইঞ্জিনিয়ারিং টিমের সাথে যোগাযোগ করে কাস্টম ওয়েব, অ্যাপ, সাস অথবা এআই এজেন্ট নিয়ে আলোচনা করুন।",
    "Contact Our Team ✉️": "আমাদের টিমের সাথে যোগাযোগ করুন ✉️",
    "Book Consultation": "পরামর্শ বুক করুন",
    "WhatsApp Chat (+971 566631501)": "হোয়াটসঅ্যাপে চ্যাট করুন (+971 566631501)",

    // Navigation & Brand Common
    "LinkedIn AI Agent": "লিংকডইন এআই এজেন্ট",
    "LinkedIn Auto-Apply Agent": "লিংকডইন অটো-অ্যাপ্লাই এজেন্ট",
    "Pipeline & Jobs": "পাইপলাইন ও চাকরি",
    "All Applications": "সকল আবেদন",
    "Applied Jobs": "সফল আবেদন",
    "Top CV Matches": "সেরা সিভি ম্যাচ",
    "Interview Calls": "ইন্টারভিউ কল",
    "Job Offers": "চাকরির অফার",
    "TIME HORIZONS": "সময়সীমা",
    "Today's Jobs": "আজকের চাকরি",
    "Past 7 Days": "গত ৭ দিন",
    "This Month": "এই মাস",
    "STATUS ARCHIVE": "স্ট্যাটাস আর্কাইভ",
    "Dry Runs": "ড্রাই রান",
    "Rejected": "প্রত্যাখ্যাত",
    "Agent Active": "এজেন্ট সক্রিয়",
    "Manage & Account": "ব্যবস্থাপনা ও অ্যাকাউন্ট",
    "User Profile": "ইউজার প্রোফাইল",
    "Billing & Plan": "বিলিং ও প্ল্যান",
    "Accounts & CV": "অ্যাকাউন্টস ও সিভি",
    "PDF Report (A4)": "পিডিএফ রিপোর্ট (A4)",
    "PDF Report": "পিডিএফ রিপোর্ট",
    "CSV Export": "সিএসভি রিপোর্ট",
    "JSON Export": "জেএসওএন ডাটা",
    "My Courses & Certs": "আমার কোর্স ও সনদ",
    "Master Super Admin Console": "সুপার অ্যাডমিন কনসোল",
    "Super Admin Master Console": "সুপার অ্যাডমিন কনসোল",
    "Admin Panel": "অ্যাডমিন প্যানেল",
    "Logout": "লগআউট",
    "Overview & Progress": "ওভারভিউ ও অগ্রগতি",
    "Video Classroom Portal": "ভিডিও ক্লাসরুম পোর্টাল",
    "Tuition & Invoices": "টিউশন ফি ও রসিদ",
    "Course Curriculum": "কোর্স কারিকুলাম",
    "Verified Certificate": "ভেরিফাইড সার্টিফিকেট",
    "Profile Settings": "প্রোফাইল সেটিংস",
    "Super Admin Console": "সুপার অ্যাডমিন কনসোল",
    "Student Menu": "স্টুডেন্ট মেনু",
    "Services & Profile": "সার্ভিস ও প্রোফাইল",
    "Student Portal Dashboard": "স্টুডেন্ট পোর্টাল ড্যাশবোর্ড",

    // Dashboard Cards & Stats
    "Total Applications": "মোট আবেদন",
    "COURSE PROGRESS RATE": "কোর্স অগ্রগতি হার",
    "TUITION PAID TO DATE": "মোট পরিশোধিত ফি",
    "REMAINING DUE BALANCE": "বকেয়া ব্যালেন্স",
    "CERTIFICATE STATUS": "সার্টিফিকেট স্ট্যাটাস",
    "Active Learning": "সক্রিয় শিক্ষা",
    "Tuition Fees & Payment Receipts": "টিউশন ফি ও পেমেন্ট রসিদ",
    "TOTAL TUITION FEE": "মোট টিউশন ফি",
    "TOTAL AMOUNT PAID": "মোট পরিশোধিত পরিমাণ",
    "Payment Status": "পেমেন্ট স্ট্যাটাস",
    "Paid in Full": "সম্পূর্ণ পরিশোধিত",

    // Actions & Buttons
    "Run Auto-Apply Agent": "অটো-অ্যাপ্লাই চালু করুন",
    "Run Dry Run Test": "টেস্ট ড্রাইভ পরীক্ষা করুন",
    "Filter": "ফিল্টার",
    "Clear": "ক্লিয়ার",
    "Reapply": "পুনরায় আবেদন",
    "Yes, Delete": "হ্যাঁ, ডিলিট করুন",
    "Cancel": "বাতিল",
    "Back to Student Dashboard": "স্টুডেন্ট ড্যাশবোর্ডে ফিরুন",
    "Back to Dashboard": "ড্যাশবোর্ডে ফিরুন",
    "Back to Admin Console": "অ্যাডমিন কনসোলে ফিরুন",
    "Print Invoice": "রসিদ প্রিন্ট করুন",
    "Download Official PDF": "অফিসিয়াল পিডিএফ ডাউনলোড",
    "Start / Resume Learning Portal": "ক্লাসরুম পোর্টালে প্রবেশ করুন",
    "Contact Mentor Support": "মেন্টর সাপোর্ট যোগাযোগ",
    "Change Password": "পাসওয়ার্ড পরিবর্তন",
    "Verify Certificate": "সার্টিফিকেট যাচাই",
    "Verify Online": "অনলাইনে যাচাই করুন",

    // Table Headers & Fields
    "Job Title & Company": "পদের নাম ও কোম্পানি",
    "CV Match": "সিভি ম্যাচ",
    "Location & Workplace": "স্থান ও কর্মক্ষেত্র",
    "Apply Type": "আবেদনের ধরণ",
    "Status": "স্ট্যাটাস",
    "Date": "তারিখ",
    "Actions": "অ্যাকশন",
    "View on LinkedIn": "লিংকডইনে দেখুন",
    "Easy Apply": "ইজি অ্যাপ্লাই",
    "External": "এক্সটার্নাল",
    "Remote": "রিমোট",
    "Hybrid": "হাইব্রিড",
    "On-site": "অন-সাইট",

    // Job Statuses
    "Applied": "আবেদন সম্পন্ন",
    "Dry Run": "ড্রাই রান",
    "Skipped": "স্কিপ করা",
    "Failed": "ব্যর্থ",
    "Interview Call": "ইন্টারভিউ কল",
    "Job Offer": "চাকরির অফার",
    "Pending": "অপেক্ষমাণ",
    "Already Applied": "পূর্বে আবেদনকৃত",

    // Student & Invoice Views
    "Student Learning Dashboard": "স্টুডেন্ট লার্নিং ড্যাশবোর্ড",
    "Welcome back": "স্বাগতম",
    "STUDENT ID": "স্টুডেন্ট আইডি",
    "Certificate Verification System": "সার্টিফিকেট যাচাইকরণ সিস্টেম",
    "Verify the authenticity of Qrious Solution Academy student certificates.": "কিউরিয়াস সলিউশন একাডেমি সনদপত্রের সত্যতা যাচাই করুন।",
    "Official Tuition Payment Receipt & Invoice": "অফিসিয়াল টিউশন ফি পেমেন্ট রসিদ ও ইনভয়েস",
    "PAYMENT RECEIPT": "পেমেন্ট রসিদ",
    "STUDENT INFORMATION": "শিক্ষার্থীর তথ্য",
    "ACADEMY CONTACT": "একাডেমি ঠিকানা",
    "Description": "বিবরণ",
    "Payment Method": "পেমেন্ট মাধ্যম",
    "Transaction Ref": "ট্রানজেকশন আইডি",
    "Amount Paid": "পরিশোধিত পরিমাণ",
    "No jobs found": "কোন চাকরি পাওয়া যায়নি",
    "job applications": "টি আবেদন",
    "Prev": "পূর্ববর্তী",
    "Next": "পরবর্তী",
    "Academy Student Portal": "একাডেমি স্টুডেন্ট পোর্টাল",
    "Qrious Solution Academy": "কিউরিয়াস সলিউশন একাডেমি",
    "Academy": "একাডেমি",
    "Certificate of Completion": "কোর্স সমাপ্তির সনদপত্র",
    "This is to certify that": "এতদ্বারা প্রত্যায়ন করা যাচ্ছে যে",
    "has successfully fulfilled all curriculum requirements, practical assignments, and final capstone challenges for the professional masterclass:": "পেশাদার মাস্টারক্লাসের সকল কোর্স কারিকুলাম, ব্যবহারিক অ্যাসাইনমেন্ট এবং ফাইনাল ক্যাপস্টোন চ্যালেঞ্জ সফলভাবে সম্পন্ন করেছেন:",
    "Lead Technical Instructor": "প্রধান টেকনিক্যাল ইনস্ট্রাক্টর",
    "SCAN TO VERIFY": "যাচাই করতে স্ক্যান করুন"
};

// Sort phrase entries by length descending (longest phrases first)
const sortedEntries = Object.entries(phraseMap).sort((a, b) => b[0].length - a[0].length);

let isTranslating = false;

/**
 * Switch language between English ('en') and Bangla ('bn')
 */
function switchLanguage(lang) {
    if (!lang) {
        const currentLang = localStorage.getItem('app_lang') || 'en';
        lang = currentLang === 'en' ? 'bn' : 'en';
    }

    localStorage.setItem('app_lang', lang);
    applyLanguage(lang);
}

/**
 * Apply current language dictionary to DOM elements
 */
function applyLanguage(lang) {
    const selectedLang = lang || localStorage.getItem('app_lang') || 'en';

    // Update Language Toggle Button Text & State
    document.querySelectorAll('.lang-toggle-btn').forEach(btn => {
        if (selectedLang === 'bn') {
            btn.innerHTML = '🇧🇩 বাংলা';
            btn.setAttribute('title', 'Switch to English');
        } else {
            btn.innerHTML = '🇬🇧 English';
            btn.setAttribute('title', 'বাংলা ভাষায় সুইচ করুন');
        }
    });

    // Run Full-DOM Text Node Replacement
    translateDOM(selectedLang);

    // Translate dynamic status dropdown options
    document.querySelectorAll('.status-select option').forEach(opt => {
        const text = opt.textContent.trim();
        if (selectedLang === 'bn') {
            if (!opt._origText) opt._origText = text;
            for (const [en, bn] of sortedEntries) {
                if (text.includes(en)) {
                    opt.textContent = text.split(en).join(bn);
                }
            }
        } else if (opt._origText !== undefined) {
            opt.textContent = opt._origText;
        }
    });

    document.documentElement.lang = selectedLang;
}

/**
 * Full-DOM recursive text node translator
 */
function translateDOM(lang) {
    if (isTranslating) return;
    isTranslating = true;

    const toBangla = (lang === 'bn');

    function processNode(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            let text = node.nodeValue;
            if (!text || !text.trim()) return;

            if (toBangla) {
                if (!node._origText) {
                    node._origText = text;
                }
                let updated = text;
                for (const [en, bn] of sortedEntries) {
                    if (updated.includes(en)) {
                        updated = updated.split(en).join(bn);
                    }
                }
                if (updated !== text) {
                    node.nodeValue = updated;
                }
            } else if (node._origText !== undefined) {
                node.nodeValue = node._origText;
            }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            const tag = node.tagName.toLowerCase();
            if (tag === 'script' || tag === 'style' || tag === 'svg' || tag === 'noscript' || tag === 'code') return;

            if (node.placeholder) {
                if (toBangla) {
                    if (!node._origPlaceholder) node._origPlaceholder = node.placeholder;
                    for (const [en, bn] of sortedEntries) {
                        if (node.placeholder.includes(en)) {
                            node.placeholder = node.placeholder.split(en).join(bn);
                        }
                    }
                } else if (node._origPlaceholder !== undefined) {
                    node.placeholder = node._origPlaceholder;
                }
            }

            for (let child of node.childNodes) {
                processNode(child);
            }
        }
    }

    processNode(document.body);
    isTranslating = false;
}

// Auto-run on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    const savedLang = localStorage.getItem('app_lang') || 'en';
    applyLanguage(savedLang);
});
