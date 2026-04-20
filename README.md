# MrGrammar


 
Chapter 1 Introduction
Problem Statement
Language teachers need a lot of time to manually correct texts and give constructive feedback. Usually, for a student to really learn from their mistakes, they need to:
1.	See that there is something wrong with a passage/sentence  highlight the area
2.	Think about how to correct it and try out a solution. If it was the correct guess, then go on; else go to step 3. 
3.	The teacher writes some kind of hint next to the highlighted area, for the student to try to guess the correct answer again. If it was the correct guess, then go on; else go to step 4. 
4.	The teacher gives the correct answer.
5.	The student rewrites sentences that were corrected.

The problem is that this workflow is impossible to manually achieve for a single teacher with 100 students. If the teacher needed about 1h for each student per text, with 1 text per week, then just this workflow would take 100h per week. Hence, students do not often write texts, and if they do, teachers do not follow this workflow because it is impractical. Consequently, students receive sub-optimal learning. 

From a student’s perspective, instead of waiting for the teacher’s feedback, they can simply run their text through Grammarly or an LLM and get AI-generated feedback. It is then entirely up to the student to choose to improve on their mistakes by using language-learning practices, or just copy-paste the solution. The easiest option is the most passive and also least optimal, which is copy-pasting or simply clicking “accept suggested improvement”. Language is learned through experimenting and making mistakes and learning from those mistakes, it is grinding. It’s tough, but effective. You simply never get to the same proficiency by just passively writing a text with AI’s help.  

Grammarly partially solves this problem by giving immediate feedback by highlighting the part of the text with various colors, and the student is then prompted to hover or click on the highlighted area to see the recommended solution. This is already great, but the grinding is not really there, and that is where I come with my solution  kinda like Grammarly, but the student needs to grind more before getting the suggested solution. 
the system’s purpose or the aim of the project
The purpose of [sys-name] is to facilitate language learning in terms of language production (writing and speaking) by giving corrective feedback and making space for the student to grind through the learning process. 
-	Helps the student through UI
o	The system shall allow students to enter text, review detected errors, and access progress information.
o	Gives opportunity for the student to experiment and try out different solutions when a mistake is spotted. This influences the student to think explicitly in their learning of their L2. 
-	Helps teacher 
o	Represent student progress over time
o	Catching common patterns 
o	

groups of individuals with whom the system will interact
-	Teachers
-	Students 
-	Administration 
-	IT 


Chapter 2 Requirement Specification
2.1 Objectives
-	Help students improve their language production through constructive feedback 
-	Show student progress to teachers (documentation for grading support)

2.2 Related Work and Scenarios

Grammarly is an AI-powered writing assistant that helps users improve clarity, correctness, and tone in real time. It analyzes text as you type in its web app or browser extension, offering suggestions for grammar, spelling, punctuation, and sentence structure.
Rather than relying solely on large language models, Grammarly combines traditional Natural Language Processing (NLP) techniques—such as syntactic parsing, rule-based systems, and statistical models—with modern machine learning and LLMs. This hybrid approach allows it to provide both precise corrections (e.g., subject–verb agreement) and higher-level feedback (e.g., clarity, tone, and style).
The system processes text by breaking it into linguistic components, identifying errors or improvements, and ranking suggestions based on context. More advanced features, like rewriting sentences or adjusting tone, are typically powered by neural models and LLMs.
Grammarly’s architecture is designed for real-time feedback at scale, using cloud-based services that integrate with browsers and applications. This enables fast, context-aware suggestions while maintaining user experience and privacy considerations.

Grammarly application: 
-	Part of it does have the functionality that I require, such as: 
o	Secure login
o	Dashboard for student that shows all previous work
o	Pannel, search bar, and editing document options in the dashboard UI
o	Once in a document, there is a panel that suggests what to fix, in the editor (main panel), once text is put in, real time feedback with suggested fixes are shown on top of user-input (this is not what I want, but I do want the underlying)
o	Comment panel and other additional panels which are not relevant to what I require. 
-	What Grammarly is missing: 
o	I don’t think it stores error pattern of user, this is what I want. This storage will provide as data for their language journey, showing how their errors improve over time. 
o	I don’t see a linkage between teacher and students (there is no 1:N relationship) 
	I want the teacher to see each class, and in each class to see each student’s texts.
	Student’s progress should be shown. 
	Class patterns should be shown.  this would be great for precise language practice that would help majority of students


Shi, H., & Aryadoust, V. (2024):
•	The review shows that while low-level feedback (such as grammar and spelling) has a big influence on the improvement of students’ language development. 
•	Less so with higher level feedback (critical thinking, style, genre..). Here, teacher feedback has a larger impact than AI. 
•	This means that Grammarly’s “AI-grader” isn’t of interest for my project, however, their low-level grammar feedback is.
 

Jayakumar et al (2025)

•	Claims to have developed a language learning system that personalizes the learning process in real time using spaCy library (NLP)
•	Comments on the initial huge improvements of this type of learning (32% improvement with spaCy vs 10% improvement with classical teacher), but that long-term, students lose motivation to use it.
•	 Does not have any practical examples, only reports of them using something. However, I can still take their workflow and apply it on my variation of Grammarly.



2.x Scenarios

2.x.1 Problem Scenario 1: Teacher Feedback Overload in Large Classes
Context:
A language teacher is responsible for four classes with approximately 25 students each. Every week, students are expected to submit a short written text (200–300 words) in the target language.
Current Situation:
To provide meaningful corrective feedback, the teacher would ideally highlight errors, give hints, allow students to attempt corrections, and only then provide correct solutions. In practice, this workflow is infeasible. Even spending 30–60 minutes per student quickly results in an unsustainable workload of >50h / week.
As a result:
•	Written assignments are given infrequently.
•	Feedback is reduced to surface-level corrections or symbols.
•	Students are rarely required to actively engage with their mistakes.
Problem Reinforced:
The pedagogically ideal feedback loop described in Chapter 1 collapses under real-world constraints, leading to sub-optimal learning outcomes despite teacher expertise.
 
2.x.2 Problem Scenario 2: Passive AI Usage by Students
Context:
A student receives a writing assignment but knows that detailed teacher feedback will take several days or may not arrive at all.
Current Situation:
Instead of engaging in the learning process, the student copies their text into an AI-based tool such as Grammarly or a general-purpose LLM. The tool highlights errors and suggests fully corrected sentences, which the student accepts with a single click.
While the final text appears polished:
•	The student does not reflect on why the original sentence was incorrect.
•	No attempt is made to hypothesize or test alternative formulations.
•	The same error patterns reappear in future writing.
Problem Reinforced:
Immediate corrective AI feedback encourages efficiency but undermines active learning. The cognitive “grinding” required for durable language acquisition is bypassed.
 
2.x.3 Problem Scenario 3: Lack of Longitudinal Insight for Teachers
Context:
A teacher wants to understand why a class repeatedly struggles with articles and prepositions.
Current Situation:
Although individual texts contain relevant errors, there is no systematic way to:
•	Track error patterns across multiple assignments.
•	Identify shared weaknesses across a class.
•	Observe whether specific error types improve over time.
Any such analysis must be done manually and informally, relying on memory or rough impressions.
Problem Reinforced:
The absence of structured learner data prevents teachers from aligning instruction with actual learner needs and obscures learning progress at both individual and group levels.
 
2.x.4 Visionary Scenario 1: Guided, Active Grammar Correction
Context:
A student writes a short German text using [sys-name].
Visionary Interaction:
As the student submits their text, the system detects grammatical errors (e.g., verb tense, article usage, prepositions) and highlights them using color-coded categories. Instead of immediately showing the correct answer, the system initiates a guided feedback loop:
1.	The student is prompted to identify and attempt a correction.
2.	If the attempt is incorrect, contextual hints are provided.
3.	Only after multiple unsuccessful attempts—or upon request—is the correct solution revealed.
4.	The student rewrites the corrected sentence.
Impact:
The system enforces active engagement while still providing immediate, individualized feedback comparable to ideal teacher guidance.
2.x.5 Visionary Scenario 2: Teacher Insight and Targeted Classroom Support
Context:
 A language teacher manages several classes using [sys-name] and wants to understand how students are progressing over time—not only individually, but also as a group.
Visionary Interaction:
 After students submit and revise their texts in [sys-name], the teacher opens a class dashboard that summarizes learner performance across recent assignments. The system visualizes recurring error categories such as article usage, verb tense, spelling, and prepositions, and shows how frequently these errors occur across the class and for each individual student.
The teacher can select a specific class to identify shared problem areas—for example, noticing that many students continue to struggle with prepositions in the dative case. The system also shows whether these errors are improving over time, which students require repeated hints before correcting them, and which students consistently succeed on their first attempt.
From the same interface, the teacher can open individual student histories and review submitted texts together with correction behavior, such as repeated error types and revision attempts. Based on these insights, the teacher adapts upcoming lessons by preparing a short targeted exercise on the most common class-wide weaknesses, while also identifying students who may need additional support.
Impact:
 The system reduces the teacher’s manual workload while making learner development visible in a structured way. Instead of relying on memory or isolated corrections, the teacher gains actionable insight into both class-level trends and individual progress, enabling more precise feedback, better-informed lesson planning, and stronger support for language development.



2.x Functional & Nonfunctional Requirements

Functional Requirements
FR‑1 User Management and Roles

FR‑1.1 The system shall allow admins to register and authenticate students, teachers, or administrators.
FR‑1.2 An admin shall be able to assign role-based access rights depending on the user’s role (student, teacher, admin).
FR‑1.3 Admins shall be able to assign student groups or classes to specific teachers. 
FR-1.3 Only a teacher has the right to see their assigned students’ work, not the admin, nor other students or other teachers (unless the other teacher is also assigned to that student or group of students). 


FR‑2 Text Input and Submission

FR‑2.1 The system shall allow students to input written texts via a dedicated text editor interface.
FR‑2.2 The system shall support submission of texts in the target language (e.g., German).
FR‑2.3 The system shall store submitted texts persistently for later review and progress tracking. The stored text shall be saved to the student who submitted it.


FR‑3 Automated Error Detection

FR‑3.1 After/during text input  The system shall analyze each submitted text and identify candidate low-level language errors in grammar, spelling, article use, prepositions, and verb tense.

FR‑3.2 The system shall detect low-level linguistic errors such as grammar, spelling, tense, articles, and prepositions.
FR‑3.3 As an output from the submission The system shall highlight detected errors directly within the submitted text. (or in a read-only panel right next to the student’s text? Idk yet  whatever is most clear to the students)

FR‑4 Guided Feedback Workflow for student (Core Feature)

FR‑4.1 For each detected error, the system shall first request a student correction attempt, then provide a hint if the attempt is incorrect, and reveal the correct solution only after a configurable number of failed attempts or when the student explicitly requests it.

FR‑4.2 The system shall first prompt the student to attempt a correction before providing hints or solutions.
FR‑4.3 The system shall provide contextual hints if the student’s correction attempt is incorrect.
FR‑4.4 The system shall reveal the correct solution only after unsuccessful attempts or on student request.
FR‑4.5 The system shall allow students to rewrite corrected sentences.


FR‑5 Learner Profiling and Progress Tracking

FR‑5.1 The system shall maintain an individual learner profile for each student.
FR‑5.2 The system shall store information about recurring error types, correction attempts, and response times.
FR‑5.3 The system shall calculate changes over time in error frequency per category, first-attempt correction success rate, and average number of hints required per assignment.


FR‑6 Visualization of Learning Progress

FR‑6.1 The system shall provide students with a visual representation of their learning progress.
FR‑6.2 The system shall visualize error frequency and improvement over time.
The system shall display to each student a dashboard showing error counts by category for each submitted assignment and a time-series view of category-specific error frequency across assignments.

FR‑6.3 The system shall allow teachers to view aggregated progress data per student or class.


FR‑7 Teacher Analytics and Insight Support

FR‑7.1 The system shall provide teachers with an analytics dashboard.
FR‑7.2 The system shall identify common error patterns across students or groups.
FR‑7.3 The system shall enable teachers to use aggregated insights to inform classroom instruction.

The system shall allow teachers to open and review all submitted texts of students assigned to their classes and projects.

FR‑8 Administrative and System Configuration

FR‑8.1 The system shall allow administrators to manage user accounts and system settings.
FR‑8.2 The system shall support corrective feedback for student texts written in German.


Non-functional requirements
Product 
External 
-	GDPR
Organizational (school)
-	How do students/teachers ID themselves?
-	School policies 
-	How should the system be used? (I guess, only in school, or with school account from home?)

2.x Non-Functional Requirements
Non-functional requirements define quality constraints and system-wide conditions under which the system must operate. The following requirements are grouped into product requirements, organizational requirements, and external requirements.

2.x.1 Product Requirements
NFR‑1 Performance

NFR‑1.1 The system shall display initial automated feedback for a submitted text of up to 500 words within 5 seconds for at least 95% of requests under normal operating conditions.
NFR‑1.2 The system shall load student and teacher dashboard views within 3 seconds for at least 95% of requests.
NFR‑1.3 The system shall support at least 30 concurrent student users and 3 concurrent teacher users without significant degradation of response time.

NFR‑2 Reliability

NFR‑2.1 Once a text submission has been confirmed to the user, the system shall store the submission persistently so that it remains available after logout, refresh, or system restart.
NFR‑2.2 The system shall recover from a server restart without loss of already confirmed submissions.
NFR‑2.3 System errors shall be logged with at least a timestamp, user role, and affected component.

NFR‑3 Usability

NFR‑3.1 A first-time student user shall be able to submit a text and begin the correction workflow within 3 minutes without external assistance.
NFR‑3.2 A first-time teacher user shall be able to open a class overview and inspect an individual student submission within 5 minutes without external assistance.
NFR‑3.3 The interface shall present feedback in clear, non-technical language appropriate for language learners.
NFR‑3.4 The system shall provide consistent navigation and terminology across student and teacher interfaces.

NFR‑4 Accessibility

NFR‑4.1 Error categories shall not be communicated by color alone; each error highlight shall also include a text label, symbol, or tooltip.
NFR‑4.2 All core functionality shall be operable using keyboard-only input.
NFR‑4.3 The user interface shall remain usable at 200% browser zoom without loss of essential functionality.
NFR‑4.4 Text and interactive elements shall meet at least WCAG 2.1 AA contrast requirements.

NFR‑5 Security

NFR‑5.1 The system shall require user authentication before access to submissions, feedback history, or analytics.
NFR‑5.2 The system shall enforce role-based access control so that users can access only data permitted by their role.
NFR‑5.3 The system shall terminate inactive sessions after 15 minutes of inactivity.
NFR‑5.4 All communication between client and server shall be encrypted using HTTPS.
NFR‑5.5 If local passwords are used, they shall be stored only as salted cryptographic hashes and never in plain text.

NFR‑6 Privacy and Data Protection

NFR‑6.1 The system shall collect and store only personal data necessary for authentication, text feedback, and progress tracking.
NFR‑6.2 The system shall provide a privacy notice explaining which learner data are stored and for what purpose.
NFR‑6.3 The system shall allow authorized administrators to delete or anonymize personal data in accordance with school retention policy.
NFR‑6.4 Student texts and learner analytics shall not be shared with unauthorized users or external services without explicit administrative approval.

NFR‑7 Compatibility

NFR‑7.1 The system shall support the latest two stable versions of Google Chrome, Microsoft Edge, and Mozilla Firefox.
NFR‑7.2 The system shall be optimized for desktop and laptop use; mobile support is not required in version 1.0.
NFR‑7.3 The system shall remain fully usable on displays with a minimum resolution of 1366 × 768.

NFR‑8 Maintainability

NFR‑8.1 The system shall separate presentation logic, application logic, and language-processing components into distinct modules.
NFR‑8.2 The source code shall be documented sufficiently for another developer to understand and extend the system.
NFR‑8.3 Core services for authentication, submission storage, and feedback workflow shall be covered by automated tests.
NFR‑8.4 Configuration values such as the maximum number of correction attempts before revealing a solution shall be modifiable without changing source code.


2.x.2 Organizational Requirements
NFR‑9 Deployment and Use Context

NFR‑9.1 The system shall be deployable on school-managed infrastructure or on an institutionally approved cloud service.
NFR‑9.2 The system shall be intended for use by enrolled students, teachers, and authorized administrators only.
NFR‑9.3 The system shall support access both on school premises and remotely from home, provided the user authenticates successfully.
NFR‑9.4 The system shall use school-managed user accounts where such accounts are available; otherwise, accounts shall be created by an administrator.

NFR‑10 Scope Constraints

NFR‑10.1 Version 1.0 of the system shall support corrective feedback for German written texts only.
NFR‑10.2 Version 1.0 shall focus on low-level language feedback (e.g., spelling, grammar, articles, prepositions, verb tense) and shall not provide automated grading of higher-level writing quality.
NFR‑10.3 The system shall not expose raw model output directly to end users without presentation through the defined feedback interface.


References

Jayakumar, P., Priyadharshini, P., Nisha, M. S., T, A., Savitha, K., & Hariharan,
          G. (2025). AI-Powered English Language Learning Systems: A Framework for
          Personalized Education Using Natural Language Processing. 2025 2nd International
          Conference on Artificial Intelligence and Knowledge Discovery in Concurrent
          Engineering (ICECONF), Artificial Intelligence and Knowledge Discovery in
          Concurrent Engineering (ICECONF), 2025 2nd International Conference On, 1–7.
          https://doi.org/10.1109/ICECONF65644.2025.11379566

Shi, H., & Aryadoust, V. (2024). A systematic review of AI-based automated written feedback research. ReCALL, 36(2), 187–209. doi:10.1017/S0958344023000265


