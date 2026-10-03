# Vetra launch plan

Vetra is the working name for a candidate verification workflow sold to HR teams. The promise is **“Clear evidence. A fairer hiring process.”** Clear the name, domain and trademarks in the launch market before paying for branding or advertising. This plan assumes an initial UK or EU market; choose one country before accepting real screening work.

## Product and market position

Sell a candidate-controlled hiring verification service: an employer requests specific checks, the candidate sees the scope, information is collected, source evidence is reviewed, and discrepancies can be corrected. HR receives a factual record with evidence provenance and a human review history.

Identity proofing, employment background checks and regulated customer KYC are different products. Maigret discovers public accounts associated with usernames; that does not prove account ownership or a person's identity. Identity proofing can establish an identity-provider outcome. Employment screening needs authoritative employment, education or other eligible sources. An AML/KYC program additionally requires the applicable customer due diligence, screening, ongoing monitoring and operating procedures. Vetra must sell only the scope it can substantiate.

Compete first on transparent candidate experience, clear check status and less HR administration. Do not compete with established screening networks by claiming comparable data coverage, turnaround time or accuracy before measuring them. Keep public username discovery, personal social-media profiling, protected-trait inference and automated hiring scores outside the HR product.

## First customer and offer

The initial customer hypothesis is a recruitment agency or growing employer with 5–25 HR/recruiting users, approximately 50–250 hires per year, one primary hiring country and frequent identity or credential follow-up. These are targeting assumptions, not measured market facts.

The economic buyer is the head of people, head of talent acquisition or agency owner. The daily user is an HR operations coordinator. The trigger is a recent credential discrepancy, increasing candidate volume, or verification work spread across email and spreadsheets. Prefer teams already paying for screening or spending measurable coordinator time on it.

Start with three design partners. Use warm introductions and founder-led discovery. Prepare a list of 30 target companies using company-level information; qualify 10, demonstrate to six and propose three paid pilots. These are activity targets, not conversion predictions. Outreach examples are in [the sales kit](SALES-KIT.md); none has been sent.

**Pilot offer:** one hiring country, one agreed role family, up to 20 candidate workflows over 30 days, two HR reviewers, an agreed set of check types, weekly feedback and a factual end-of-pilot report. Begin with synthetic cases. Use real candidates only after the operational gates below are complete. If identity verification is activated, quote its provider fee separately. An unconnected check must be excluded from the statement of work.

## Current capability and build versus buy

| Layer | Current deliverable | Launch approach |
|---|---|---|
| HR workflow | Case queue, invitations, roles, tenant boundaries, manual review, audit and CSV export | Own the workflow and candidate experience; validate with design partners |
| Candidate participation | Scoped approval, statements, selected professional profiles, corrections and withdrawal | Own the portal; explain each check and offer a support route |
| Identity proofing | Stripe Identity adapter with hosted sessions and signed callbacks | Activate a contracted provider and test supported documents/countries; adapter availability alone is not a completed check |
| Employment and education | Candidate statements and explicitly manual evidence review | Contract authoritative issuers or a screening provider; preserve source, result, date and dispute handling |
| Criminal history, sanctions, credit and right to work | No connected providers | Add only when the market, eligibility, contracted source and required process are defined |
| Enterprise operations | Single-instance SQLite pilot and security foundations | Add production storage, workforce identity, durable jobs and validated operations before enterprise sales |

Buy document authenticity, liveness, authoritative registry coverage and country-specific screening access from established providers. Build case orchestration, scope management, status explanations, source provenance, corrections, audit, reporting and ATS workflows. Prefer hosted provider collection so Vetra does not need to store identity documents or biometric media.

Evaluate providers on eligible use cases/countries, evidence quality, candidate dispute support, data hosting/transfers, retention and deletion, webhook reliability, service terms, minimum spend and per-check charges. Request a sandbox and a contract. A provider's identity verification result must not be described as a UK statutory right-to-work check without the required supported process. Reusable open-source software is evaluated separately in [OSS components](OSS-COMPONENTS.md).

## Pricing hypothesis and economics

All prices below are unvalidated launch hypotheses in euros. Tax and contracted identity/screening fees are separate. Quote local currency and applicable tax in the actual pilot agreement.

| Offer | Monthly workflow subscription | Included cases | Intended use |
|---|---:|---:|---|
| Essential | €299 | 20 | Small hiring team and the first scoped paid pilot |
| Professional | €799 | 75 | Higher-volume workflow after pilot validation |
| Enterprise | Quote after scope and operating requirements are assessed | Contracted | SSO, support, integrations and volume needs; not currently ready to sell as an enterprise service |

A workflow case is one candidate invitation for one agreed screening request, not a successful identity or background check. Corrections and retries within that request do not create a new billable case. No overage, annual commitment, multi-country screening or service-level promise should be implied; agree it explicitly before work starts. Quote provider charges before candidate submission. Candidates are not charged.

The subscription yields €14.95 per included Essential case and approximately €10.65 per included Professional case at full allowance. These figures are allocation calculations, not verification costs.

Illustrative Professional economics at full usage: 75 cases × 8 minutes of manual work × €30/hour loaded labour = €300; assumed hosting and support allocation €100; remaining contribution €399, about 50% of €799. Provider costs are assumed to be charged separately at cost; this example excludes acquisition, legal, tax and general overhead. If manual work doubles to 16 minutes, contribution falls to €99, about 12%. Measure actual labour before promising low-cost packages. Three Essential design partners produce €897 in monthly workflow revenue if all pay; this is a pilot target, not a forecast.

## Thirty-day launch sequence

| Days | Deliverable | Evidence to collect |
|---|---|---|
| 1–5 | Choose one country and check scope; clear working brand; complete six buyer interviews; map current workflow and cost | Buyer, hiring volume, current spend, coordinator minutes and top failure points |
| 6–10 | Run six synthetic demos; select three design partners; agree paid statements of work; select identity and credential partners | Agreed supported scope, actual willingness to pay and provider quotes |
| 11–15 | Deploy private pilot; finish notices, agreements, support and provider setup; run success/failure/correction/withdrawal drills | Signed agreements, tested callbacks, access controls, deletion and recovery evidence |
| 16–25 | Run limited real cases only after gates pass; meet partners weekly; monitor candidate completion and manual workload | Timing by check, provider costs, source quality, candidate issues and support minutes |
| 26–30 | Produce factual pilot report; decide scope/pricing changes; offer renewal to successful partners | Paid renewal decisions, measured margin and a prioritised roadmap |

If privacy, provider or operational setup is incomplete, the 30-day output remains paid product discovery and synthetic workflow testing. Do not silently substitute manual statements for contracted verification.

Pilot success targets to test: three paying partners, at least 80% of eligible invited candidates submitting within three business days, median HR administration below ten minutes per case, and at least two partners requesting renewal. Separate provider turnaround from candidate response time. Report counts and denominators, including withdrawals and unresolved discrepancies; a small pilot cannot establish population-level accuracy.

## Launch gates

Before a real-data pilot, agree the launch country, eligible roles and check scope; execute employer/provider agreements; assign controller/processor responsibilities and the appropriate lawful basis; publish notices; assess a DPIA where required; and set retention, deletion and support procedures. Candidate approval is a workflow record, not proof that consent is the lawful basis for every employment processing activity.

Activate contracted providers and HTTPS callbacks; disable demonstration mode; use stable secrets and authenticated staff access; test tenant isolation, provider failure, correction, withdrawal, deletion and recovery; and document who reviews discrepancies. A withdrawal request must be reconciled with provider work and applicable retention obligations. Promise only the achieved behavior and agreed timescales.

Before an enterprise launch, complete managed Postgres storage, SSO/MFA and staff lifecycle handling, independent authorization/security review, durable provider jobs and reconciliation, monitored operations, backup/restore exercises, support and incident response, billing/entitlements, accessibility testing, provider contracts and country-specific procedures. Complete customer procurement evidence truthfully. SOC 2 and ISO 27001 require their own assessment processes; software controls do not create a certification.

Defer US employment screening until the applicable consumer-reporting role, permissible purpose, employer authorisation/disclosure, adverse-action and dispute processes are designed with the relevant provider and counsel. Defer AI ranking or suitability prediction; if later proposed, assess the applicable employment and AI rules before building it.

## Reference reading for market validation

These are official starting points for review with the selected market's adviser, not a claim of legal clearance or verified current guidance:

- [ICO: employment guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/employment/)
- [UK Government: check a job applicant's right to work](https://www.gov.uk/check-job-applicant-right-to-work)
- [UK Government: criminal record checks](https://www.gov.uk/request-copy-criminal-record)
- [EU GDPR text](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- [European Commission: AI regulatory framework](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)
- [FTC: background checks and employers](https://www.ftc.gov/business-guidance/resources/background-checks-what-employers-need-know)
- [Stripe Identity documentation](https://docs.stripe.com/identity)
