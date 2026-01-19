"""
Test cases for jobs that should be captured by the scraper.
Run with: python -m pytest tests/test_jobs.py -v
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper import score_job, load_filter_config

# Force fresh config load for each test run
config = load_filter_config()


# Job descriptions that SHOULD qualify
SHOULD_QUALIFY = [
    {
        "name": "Westwood Electrical Design Technician",
        "company": "Westwood Professional Services, Inc.",
        "description": """Overview:
Electrical Design Technician
Westwood Professional Services, Inc.

Westwood Professional Services, Inc. is seeking an Electrical Design Technican to join our renewables team in our Englewood, CO office. This position will be responsible for designing elements of utility-scale solar energy systems, primarily using AutoCAD. You'll be utilizing AutoCAD to create construction documents and perform quantity takeoffs. Including site layouts, wire/cable routing plans, one lines, details, equipment/wire schedules, etc.
Duties and Responsibilities:
Construction document production support for commercial and utility scale solar, wind, and energy storage projects.
Coordinate with design team disciplines including civil engineers, geotechnical engineers, and surveyors
Utilize AutoCAD to create construction documents and perform quantity takeoffs. Construction documents will include site layouts, wire/cable routing plans, one lines, details, equipment/wire schedules, etc.
Create wiring/cable schedules based takeoffs and sizing input from senior designers/engineers
Maintain awareness and knowledge of Westwood design/CAD standards
Required Skills:
Proficiency in AutoCAD
Knowledge of NEC and/or NESC
Experience and knowledge of basic electrical design concepts
Required Experience:
Associates Degree or Technical School Certificate in Electrical Design, Solar Design, Architectural/Engineering Drafting, or related degree
Approximately 1 - 4 years of experience in the drafting/design of electrical power/distribution systems
Working knowledge and ability to read construction drawings and specifications
Proficiency with Microsoft Windows/Office products
Professional appearance with excellent written and verbal communications skills
Must have a strong work ethic along with a positive attitude
Must be a supportive team member, able to work in a collaborative environment.
Must be self-motivated with an ability to balance multiple projects under tight deadlines
Preferred Experience:
Bachelor's Degree in Electrical Engineering, Energy Engineering, or similar.
Experience with AutoCAD Civil 3D
Experience with ArcGIS
Proficiency with ETAP, SKM, CYME, or similar software package used to model electrical power systems and perform load flow, short circuit, voltage drop, grounding, thermal, and protective device coordination studies and analysis.
NABCEP Certification
Wind AC collection design
Experience with energy storage systems (battery, fuel cells, flywheel, or capacitor)
Experience with PVsyst, Helioscope, SAM, or other PV production modeling software
Experience with Helios 3D or SunDAT
Experience with Homer Pro"""
    },
    {
        "name": "Pattern Energy Senior Design Engineer",
        "company": "Pattern Energy Group LP",
        "description": """Senior Design Engineer - Solect Energy- job post
Pattern Energy Group LP
3.2
3.2 out of 5 stars
89 Hayden Rowe St, Hopkinton, MA 01748
$89,000 - $112,000 a year - Full-time
Pattern Energy Group LP
89 Hayden Rowe St, Hopkinton, MA 01748
$89,000 - $112,000 a year
You must create an Indeed account before continuing to the company website to apply
Profile insights
Find out how your skills align with the job description
Certifications

Do you have a valid NABCEP Certification certification?
Skills

Do you have experience in Schematic development for electrical drafting?

Job details
Pay
$89,000 - $112,000 a year
Job type
Full-time

Benefits
Pulled from the full job description
Referral program
401(k)
Health insurance
Paid time off
Vision insurance
Dental insurance
Life insurance

Full job description
Overview:
General Summary

The Senior Design Engineer leads the design of C&I solar PV (ground-mount, canopy, rooftop) and energy storage projects. This includes the full design lifecycle, from concept to as-built drawings, plus construction support, equipment review, and process improvement. This position leads project coordination, mentors designers and interns, and ensures code compliance.
Responsibilities:
Key Functions
Design canopy, ground-mount, and rooftop solar projects using AutoCAD, ensuring compliance with NEC codes and permitting requirements.
Create electrical single-line diagrams for Professional Engineer (PE) review and stamping.
Act as a technical lead in internal and external project coordination meetings for new construction and complex projects (greater than 500kW AC, BESS, EV charging, repowering).
Collaborate with the Regulatory team on utility revisions during the interconnection process.
Develop comprehensive site plans and construction document sets for advanced project development stages. This includes detailed drawings for equipment pad design/layouts, switchgear elevations, grounding details, inverter racking details, and BESS pad details. Create as-built construction documents upon project completion.
Generate detailed site plans illustrating equipment pad/locations, transformer pads, trench routes, and point of interconnection details.
Provide technical support to the construction team through project completion.
Resolve RFIs and technical challenges, review submittals, attend weekly construction calls as needed, and support project closeout tasks.
Review and approve equipment drawings and specifications for procurement. Review project drawings for constructability and code compliance.
Support new product and technology research initiatives.
Lead process improvement initiatives.
Develop and manage relationships with vendors and engineering consultants throughout the project lifecycle.
Support training of engineering department personnel and development of design drawing libraries.
Conduct site visits during construction for project assessment.
Perform Helioscope/PVSyst designs and other design/engineering tasks as required.
Mentor and coach Design Engineers and Design Interns.
Qualifications:
Qualifications
Minimum 3 years of experience in Commercial & Industrial (C&I) Solar PV design and engineering.
Minimum 1 year of Energy Storage experience.
Proficiency in creating electrical single-line diagrams.
Ability to create point-to-point diagrams for storage and PV monitoring systems (a plus).
NABCEP PV Design or Installation Certification (preferred).
Proficiency in AutoCAD, Salesforce, Google Suite, and Microsoft Office.
Proficiency in Helioscope and PVSyst (preferred).
Quality-oriented with strong attention to detail.
Ability to multitask and manage multiple project designs simultaneously with minimal supervision.
Professional and personable demeanor with a willingness to interact with clients, third-party design professionals, utility representatives, and other team members.

Special Position Requirements
Occasional travel may be required in Massachusetts, Rhode Island, and Connecticut.

Please note this job description is not designed to cover or contain a comprehensive listing of activities, duties or responsibilities that are required of the employee for this job. Duties, responsibilities, and activities may change at any time with or without notice.

The expected starting pay range for this role is $89,000 - $112,000 USD. This range is an estimate and base pay may be above or below the ranges based on several factors including but not limited to location, work experience, certifications, and education. In addition to base pay, Pattern's compensation program includes a bonus structure for full-time employees of all levels. We also provide a comprehensive benefits package which includes medical, dental, vision, short and long-term disability, life insurance, voluntary benefits, family care benefits, employee assistance program, paid time off and bonding leave, paid holidays, 401(k)/RRSP retirement savings plan with employer contribution, and employee referral bonuses

#LI-DR-1"""
    },
    {
        "name": "Vallum Associates Solar Designer",
        "company": "Vallum Associates",
        "description": """Solar Designer- job post
Vallum Associates
Stamford, CT
$100,474.42 - $125,506.84 a year - Full-time
Vallum Associates
Stamford, CT
$100,474.42 - $125,506.84 a year
Profile insights
Find out how your skills align with the job description
Certifications

Do you have a valid NABCEP Certification certification?
Skills

Do you have experience in Technical Proficiency?
Education

Do you have a Bachelor's degree?

Job details
Pay
$100,474.42 - $125,506.84 a year
Job type
Full-time

Benefits
Pulled from the full job description
401(k)
Health insurance
Paid time off
Vision insurance

Full job description
About the Role

We are seeking an experienced Solar Designer - C&I to support the design and development of commercial and industrial solar PV projects. The ideal candidate will have strong technical expertise in PV system design, a solid understanding of C&I electrical infrastructure, and experience working across project development, engineering, and construction teams.

Key Responsibilities

Design rooftop, ground-mounted, and carport solar PV systems for C&I clients
Develop preliminary and detailed system layouts, single-line diagrams (SLDs), and electrical designs
Perform site feasibility assessments, shading analysis, and energy yield simulations
Optimize system designs for performance, cost, constructability, and code compliance
Prepare design packages for permitting, interconnection, and construction
Coordinate with sales, project managers, engineers, and external stakeholders
Ensure designs comply with local AHJs, NEC, utility requirements, and applicable codes
Support value engineering, equipment selection, and technical due diligence
Provide technical support during construction and commissioning as needed
Required Qualifications

Bachelor's degree in Engineering, Renewable Energy, or a related field (or equivalent experience)
2+ years of experience designing commercial & industrial solar PV systems
Strong knowledge of C&I electrical systems, including 3-phase power
Proficiency with solar design tools such as AutoCAD, Aurora, HelioScope, PVsyst, or similar
Solid understanding of NEC, interconnection standards, and permitting processes
Experience with rooftop structural considerations and electrical layouts
Ability to interpret utility bills, load profiles, and site constraints
Preferred Qualifications

NABCEP Certification (PV Design or PV Professional)
Experience with battery energy storage systems (BESS) in C&I applications
Familiarity with utility-scale interconnection studies and utility coordination
Experience supporting EPC or developer-led project teams
Job Type: Full-time

Pay: $100,474.42 - $125,506.84 per year

Benefits:

401(k)
Health insurance
Paid time off
Vision insurance
Work Location: In person"""
    },
    {
        "name": "1st Light Commercial Solar Designer",
        "company": "1st Light Sales Corp.",
        "description": """Commercial Solar Designer- job post
1st Light Sales Corp.
3.2
3.2 out of 5 stars
Manteca, CA 95336
$65,000 - $80,000 a year - Full-time
1st Light Sales Corp.
Manteca, CA 95336
$65,000 - $80,000 a year
Profile insights
Find out how your skills align with the job description
Certifications

Do you have a valid NABCEP Certification certification?
Skills

Do you have experience in Technical Proficiency?

Job details
Pay
$65,000 - $80,000 a year
Job type
Full-time

Benefits
Pulled from the full job description
401(k)
Health insurance
Paid time off
Vision insurance
Dental insurance

Full job description
About Us

1st Light is a leader in renewable energy solutions, specializing in commercial and industrial solar PV installations across the U.S. We design and deliver high-performance solar systems that help businesses reduce energy costs, meet sustainability goals, and transition to clean power. Join our innovative team and contribute to the clean energy transition!

Job Summary This is an in office role; remote work is not an option. We are seeking a skilled Commercial Solar Designer to join our engineering team. In this role, you will be responsible for designing efficient, code-compliant commercial solar photovoltaic (PV) systems for rooftops, carports, ground mounts, and other applications. You will use industry-leading software to create detailed layouts, electrical schematics, and construction documents while collaborating with project managers, installers, and clients to deliver optimized solar solutions. This is an in office role; remote work is not an option. Applicants seeking remote work will not be considered.

Key Responsibilities

Perform site-specific engineering analysis and design of commercial solar PV systems (typically 50 kW to 2 mW scale), including rooftop, canopy, and ground-mounted configurations.
Create detailed design drawings, including site plans, electrical single-line diagrams (SLDs), three-line diagrams, panel layouts, racking plans, conduit/wire schedules, and equipment specifications using CAD software.
Use solar design tools (e.g., Helioscope, Aurora Solar, PVsyst, AutoCAD, or similar) to model energy production, account for shading, orientation, tilt, and system performance.
Select appropriate PV modules, inverters, racking, and balance-of-system components to optimize efficiency, cost, and reliability.
Ensure designs comply with NEC (National Electrical Code), local building codes, utility interconnection requirements, permitting standards, and structural/safety regulations.
Conduct energy yield simulations and provide technical recommendations to maximize system output and ROI for clients.
Collaborate with multi-disciplinary teams (sales, project management, installation, and permitting) to refine designs based on site surveys, client needs, and feedback.
Prepare permit-ready drawing packages, support interconnection applications, and provide technical support during installation, commissioning, and troubleshooting.
Stay current with industry advancements, new technologies (e.g., energy storage integration), and best practices in commercial solar design.
Qualifications & Requirements

4+ years of experience designing commercial solar PV systems.
Proficiency in solar design software such as Helioscope, Aurora Solar, PVsyst, SketchUp, and AutoCAD.
Strong understanding of electrical engineering principles, PV system components, and grid interconnection processes.
Knowledge of NEC, IBC, ASCE standards, and utility requirements for commercial solar projects.
NABCEP PV Design Specialist certification or similar (preferred but not required).
Excellent attention to detail, problem-solving skills, and ability to manage multiple projects with tight deadlines.
Strong communication skills for collaborating with internal teams and explaining technical designs to non-technical stakeholders.
Ability to work independently in a fast-paced environment; remote work possible with reliable internet and tools.
Must be able to reliably report to work as scheduled.
Preferred Skills

Experience integrating battery storage (BESS) with commercial solar systems.
Familiarity with permitting processes in multiple states (especially California).
Prior field experience (e.g., site assessments or installation support).
Pay: $65,000.00 - $80,000.00 per year

Benefits:

401(k)
Dental insurance
Health insurance
Paid time off
Vision insurance
Work Location: In person"""
    },
    {
        "name": "Nexamp Senior Solar Project Engineer",
        "company": "Nexamp",
        "description": """Senior Solar Project Engineer- job post
Nexamp
3.8
3.8 out of 5 stars
Chicago, IL
$100,000 - $140,000 a year
Nexamp
Chicago, IL
$100,000 - $140,000 a year
Profile insights
Find out how your skills align with the job description
Certifications

Do you have a valid NABCEP Certification certification?
Skills

Do you have experience in Vendor relationship management?

Job details
Pay
$100,000 - $140,000 a year

Benefits
Pulled from the full job description
401(k) matching
Paid time off
Vision insurance
Dental insurance
Stock options
Cell phone reimbursement
Commuter assistance

Full job description
Do you want to be a part of the clean energy movement? Are you passionate about improving our environment for this generation and those to follow? Are you ready to take on new challenges and collaborate with a future-focused team leading the way into new markets? Join Nexamp!

This is where you can learn from industry leaders and become one yourself. It's fast-paced, mission-based work that challenges the status quo. Be on the team that's changing the world.

What we're looking for:

Nexamp is seeking to hire a Senior Solar Project Engineer to join it's Project Engineering team. In this role, you will lead technical execution of solar power and energy storage projects, from initial development to the completion of construction. You'll manage and optimize design and engineering packages, ensuring projects meet schedules and minimize costs effectively. Your leadership will extend to developing expertise in technical areas, spearheading new product and technology initiatives, and managing relationships with vendors and engineering consultants. With a focus on leading asset performance modeling, risk mitigation, and generally supporting project teams, your role is critical in driving Nexamp's mission forward. Join us to shape the future of sustainable energy with your project management skills and technical acumen.

We are accepting candidates across our hub offices of Boston, MA and Chicago, IL, where you will be hybrid. You will report to the Manager, Project Engineering.

What you'll do:

Manage engineering and design to support development, permitting, interconnection, construction, and closeout phases for solar power plants and energy storage systems. Create drawings as needed to maintain project timelines. Support construction of engineering designs.
Lead the activities of the project team to deliver optimized design and engineering packages to meet the requirements of the project schedule. Make decisions on project- and portfolio-level tradeoffs to minimize LCOE and achieve project objectives.
Provide technical support to Nexamp development from lead generation to NTP. Communicate with code-enforcement personne l, provide technical context for development conversations with AHJs, complete auxiliary engineering analyses as needed to advance projects (subsurface engineering investigations, glare studies, FAA reports, noise studies, etc.).
Independently develop and defend engineering opinions on any aspect of the PV design process (Energy modelling, Civil/Electrical/Structural design, PV+BESS, etc.).
Lead technical due diligence on grid-tied generation asset designs.
Provide technical support to Nexamp construction from NTP to Substantial Completion. Drive resolutions for RFIs and technical challenges, review submittals, attend weekly construction calls as needed, and support project closeout tasks.
Coordinate project-level engineering activities between teams (Electrical, Civil, SCADA, & Design Engineering). Provide guidance and support to external engineering teams, by resolving technical issues and reducing ambiguity while weighing the impact to project risks, performance, and cost.
Identify, track, and mitigate project risks by maintaining a project risk register and communicating risks to stakeholders.
Own energy production modelling for Nexamp assets utilizing a range of modelling software (PVSYST, Helioscope, SIFT, PVCase Yield, etc.).
Review and approve equipment drawings and specifications for procurement. Review project drawings for constructability and code-compliance.
Develop and maintain design/construction code expertise. Track anticipated code updates and analyze their impact on Nexamp's Engineering standards and Procurement strategies.
Develop subject matter expertise in a technical focus area to support objectives of the engineering department.
Lead new product and technology research initiatives; present findings and conclusions to senior leaders.
Lead process improvement initiatives and own change management.
Develop and manage relationships with a network of vendors and engineering consultants for the entire project life cycle.
Support training of engineering department personnel and development of design drawing libraries.
Perform site visits during construction for project assessment.
What you'll bring:

Degree in Engineering or equivalent education/certification background. NABCEP certification and/or Engineer-in-Training (EIT) credential required.
5+ years of experience in solar project engineering and/or design, including at least 2 years supporting the design, optimization, and construction of grid-tied energy projects-preferably solar, battery energy storage systems (BESS), or wind.
Experience working with third-party engineering firms to deliver construction-ready engineering drawings, calculations, and specifications.
Familiarity with the Distributed Generation (DG) or Community Solar landscape, with an understanding of how it differs from C&I and Utility Scale PV. Knowledge of utility, state, or regional differences that affect PV project execution.
Demonstrated leadership or decision-making responsibilities across the permitting, interconnection, construction, and/or closeout phases of PV or BESS projects.
Strong knowledge of relevant design codes, including the National Electric Code (NEC), International Building Code (IBC), International Fire Code (IFC), and related standards.
High proficiency in PVSYST software, with the ability to explain key inputs and outputs for DG, C&I, and/or Utility Scale PV systems.
Strong understanding of power engineering principles related to PV and BESS projects.
Working knowledge of structural loads in PV and BESS design and common structural mitigation strategies.
Moderate understanding of civil engineering and construction practices for PV and BESS.
Basic understanding of overcurrent protective device (OCPD) coordination.
Familiarity with the design and operation of major PV and BESS components and the ability to review and approve equipment prior to procurement.
Experience applying value engineering and project optimization techniques to enhance system performance and cost-efficiency.
Ability to anticipate and address construction challenges during early project phases.
Working knowledge of AutoCAD software.
Moderate proficiency in Microsoft Word, Excel, and PowerPoint.
Commitment to Nexamp's mission and have a passion for solving tomorrow's climate crisis today.
Demonstrated experience in effectively communicating information, ideas, and perspectives with people inside and beyond your organization.
Experience in showcasing initiative to make improvements to current work, processes, products, and services across the organization. We value accountability and an ownership mentality.
Ability to ask appropriate questions, analyze data, identify the root causes of problems, and present creative solutions.
Expertise in building strong internal and external relationships with customers and stakeholders, instilling trust and loyalty across the industry.
Eagerness to develop a fundamental understanding of how Nexamp operates and then apply that knowledge effectively to inform business decisions.
If you don't meet 100% of the above qualifications, but see yourself contributing, please apply.

At Nexamp, our mission is to build the future of energy so it is clean, simple, and accessible for all. We are committed to providing a work environment free from discrimination. We are proud to be an equal opportunity employer. We do not discriminate against applicants on the basis of race, ethnicity, religion, sex, gender, sexual orientation, gender identity, disability status, veteran status, or any other basis protected by law. By encouraging a culture where ideas and decisions come from all people, we believe it will help us grow, innovate, and be a part of environmental and social change.

You'll love working here because:

Not only will you get to take part in meaningful work and have the chance to change the world alongside innovative, dedicated, and motivated peers, but you will also have access to all the benefits that Nexamp offers! This includes our competitive compensation package; a 401(k) employer-match; health, dental, and vision insurance starting day one; flexible paid time off and holiday PTO; commuter benefits, and cell phone reimbursement. We have headquarters in Boston, MA and Chicago, IL, in addition to growing offices nationwide. We provide healthy snacks, coffee, service days and other volunteer opportunities, company outings, and more!

Compensation

The reasonably estimated salary for this role at Nexamp ranges from $100,000 - $140,000. In addition to base salary, the competitive compensation package may include, depending on the role, participation in an incentive program linked to performance (for example, annual bonus programs based on individual and company performance, non-annual sales incentive plans, or other non-annual incentive plans). Additionally, you may be eligible to participate in the Company's stock option plan. Actual base salary may vary based upon, but is not limited to, skills and qualifications, internal equity, performance, and geographic location.

Nexamp's People team manages all aspects of recruitment and hiring within our organization. We want to inform third-party recruiters, staffing firms, and related agencies that Nexamp does not accept unsolicited resumes. Resumes will only be considered from these entities if a signed agreement is in place and the People team explicitly authorizes external recruiting assistance for a specific position. Any unsolicited resumes received will be deemed the property of Nexamp. We want to emphasize that Nexamp is not liable for any fees associated with unsolicited resumes."""
    },
    {
        "name": "BaRupOn Solar PV Design Engineer",
        "company": "BaRupOn LLC",
        "description": """Solar PV Design Engineer- job post
BaRupOn LLC
Liberty, TX
$24 - $30 an hour - Full-time
BaRupOn LLC
Liberty, TX
$24 - $30 an hour
Profile insights
Find out how your skills align with the job description
Certifications

Do you have a valid OSHA 10 certification?
Skills

Do you have experience in CAD software?
Education

Do you have a Associate's degree?

Job details
Pay
$24 - $30 an hour
Job type
Full-time

Benefits
Pulled from the full job description
401(k) matching
Paid time off
Vision insurance
Dental insurance
Paid holidays

Full job description
Job Summary
The Solar PV Design Engineer will support the layout, drafting, and technical design of utility-scale and commercial solar systems. This associate-level role focuses on preparing construction-ready drawings, conducting site and electrical analysis, and assisting with permitting and interconnection applications. Ideal candidates are proficient in AutoCAD, electrical plan reading, and solar PV components.

Key Responsibilities
Create PV system layouts, single-line diagrams (SLDs), and wiring schematics
Support array layout planning, inverter placement, and trenching routes
Use AutoCAD and PVsyst (or similar tools) to produce construction drawings
Assist with system sizing, stringing calculations, voltage drop, and shading analysis
Coordinate with field engineers, procurement, and permitting teams
Ensure designs comply with NEC, local AHJs, utility interconnection, and safety standards
Revise drawings based on feedback from engineering, AHJs, and utility companies
Maintain document control and support technical submission packages
Qualifications
Associate degree in Electrical Engineering Technology, Renewable Energy Systems, or related field
2–4 years of experience in PV system design (commercial or utility-scale)
Proficient in AutoCAD (required); PVsyst, Helioscope, or SketchUp a plus
Basic understanding of solar PV electrical systems, NEC, and interconnection requirements
Able to read technical drawings and construction documents
Detail-oriented with strong communication and drafting skills
Familiarity with permitting, electrical line diagrams, and local utility standards
Must be able to work independently and in a team environment
Preferred Certifications
NABCEP PV Associate or Installer (preferred, not required)
AutoCAD or design software certification
OSHA 10 or basic site safety training
Benefits
Competitive hourly wage: $24 – $30/hour, depending on experience
Health, dental, and vision insurance
401(k) with employer match
Paid time off and holidays
Growth opportunities in solar design and engineering"""
    },
]


def test_all_jobs_qualify():
    """Test that all jobs in SHOULD_QUALIFY list pass the filter."""
    failures = []

    for job in SHOULD_QUALIFY:
        result = score_job(job["description"], job.get("company"), config)
        if not result.qualified:
            failures.append({
                "name": job["name"],
                "score": result.score,
                "reasons": result.reasons
            })

    if failures:
        msg = "\n\nJobs that should qualify but didn't:\n"
        for f in failures:
            msg += f"\n  {f['name']}:\n"
            msg += f"    Score: {f['score']}\n"
            msg += f"    Reasons: {f['reasons']}\n"
        assert False, msg


def test_individual_jobs():
    """Individual tests for each job for better error reporting."""
    for job in SHOULD_QUALIFY:
        result = score_job(job["description"], job.get("company"), config)
        assert result.qualified, f"{job['name']} should qualify. Score: {result.score}, Reasons: {result.reasons}"


if __name__ == "__main__":
    print("Testing job scoring...\n")
    print("=" * 60)

    all_passed = True
    for job in SHOULD_QUALIFY:
        result = score_job(job["description"], job.get("company"), config)
        status = "PASS" if result.qualified else "FAIL"
        print(f"\n[{status}] {job['name']}")
        print(f"  Company: {job.get('company', 'N/A')}")
        print(f"  Score: {result.score} (threshold: {result.threshold})")
        print(f"  Reasons:")
        for r in result.reasons:
            print(f"    {r}")

        if not result.qualified:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print(f"All {len(SHOULD_QUALIFY)} jobs passed!")
    else:
        print("SOME JOBS FAILED - see above for details")
        exit(1)
