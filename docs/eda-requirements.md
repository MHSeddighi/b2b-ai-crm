# Customer 360 — EDA Requirements

This document defines the requirements for exploratory data analysis (EDA)
of the Customer 360 multi-source dataset.

When asked to create an EDA notebook, read this document first and follow
its requirements. The goal is to understand the structure, quality,
relationships, overlap, and identity-resolution potential of all available
data sources before implementing the Customer 360 pipeline.

Do NOT build the entity-resolution model during EDA.
EDA should provide the evidence needed to design that model later.

---

# 1. EDA Goals

The EDA should answer these questions:

1. What datasets/sources are available?
2. What does each dataset represent?
3. What are the schemas and data types?
4. How large is each dataset?
5. What is the data quality of each source?
6. Which fields can identify a customer?
7. Which fields can be used for entity resolution?
8. How much overlap exists between sources?
9. How many duplicate customer/entity records exist?
10. How inconsistent are customer names, companies, phones, emails, and addresses?
11. Which sources contain useful unstructured text?
12. What information exists about customer behavior?
13. What relationships exist between customers, sales, complaints, CRM interactions,
    and product requests?
14. What evidence supports using exact matching, fuzzy matching, or embeddings?
15. What potential problems could make Customer 360 unreliable?

The notebook should finish with concrete conclusions and recommendations
for the next stage.

---

# 2. Dataset Discovery

The notebook must first automatically discover and inspect the available files.

Supported formats may include:

- CSV
- Excel
- Parquet
- JSON

For every file, report:

- file name
- file type
- number of rows
- number of columns
- column names
- inferred data types
- memory usage when practical
- sample records

Create a summary table:

| Dataset | Rows | Columns | Size | Likely Domain |
|---------|------|---------|------|---------------|

Do not assume dataset names or schemas before inspecting the actual files.

---

# 3. Schema Analysis

For every dataset:

- display column names
- infer data types
- show example values
- calculate missing-value percentage
- calculate unique-value count
- calculate unique-value percentage
- identify likely ID columns
- identify likely categorical columns
- identify numeric columns
- identify date/time columns
- identify text columns

Create a column-level profiling table:

| Column | Type | Missing % | Unique | Unique % | Example | Likely Meaning |
|--------|------|-----------|--------|----------|---------|----------------|

Automatically flag potentially important columns such as:

- customer_id
- client_id
- contact_id
- company_id
- name
- customer_name
- company_name
- email
- phone
- address
- city
- industry
- product
- order_id
- complaint_id
- date
- description
- notes
- text
- comment

Do not assume these exact names exist. Detect similar fields.

---

# 4. Data Quality Analysis

For every dataset analyze:

## Missingness

Calculate:

- missing count
- missing percentage

Visualize missingness using appropriate charts.

Identify:

- completely missing columns
- highly incomplete columns
- columns with moderate missingness
- rows with unusually high missingness

## Duplicates

Analyze:

- exact duplicate rows
- duplicate IDs
- duplicate customer names
- duplicate emails
- duplicate phone numbers
- duplicate company names

Do not assume duplicate records are errors.
Explain whether they could represent multiple transactions,
interactions, complaints, etc.

## Invalid Values

Look for:

- invalid emails
- invalid phone numbers
- impossible dates
- negative quantities where inappropriate
- impossible prices
- empty strings
- placeholder values such as:
  - N/A
  - unknown
  - -
  - null
  - 0
  - test

Report suspicious values rather than automatically deleting them.

---

# 5. Customer Identity Analysis

This is one of the most important parts of the EDA.

Identify all fields that could potentially identify the same customer
across different systems.

Examples:

- customer ID
- company ID
- contact ID
- name
- company name
- email
- phone
- address

For each source, determine:

- which identity fields exist
- their completeness
- their uniqueness
- their stability
- whether they could be shared across sources

Create an identity-field summary:

| Dataset | Field | Missing % | Unique % | Candidate Identifier |
|---------|-------|-----------|----------|----------------------|

---

# 6. Cross-Source Overlap

Analyze whether customer information overlaps between sources.

Examples:

- CRM ↔ Sales
- CRM ↔ Complaints
- CRM ↔ Reports
- Sales ↔ Complaints
- Sales ↔ Product Requests

First use exact normalized matching where possible.

For example:

- normalized email
- normalized phone
- normalized customer ID
- normalized company name

Estimate:

- number of records that can be directly linked
- percentage linked
- number of unmatched records

Visualize the overlap where useful.

If practical, create an overlap matrix:

| Source | CRM | Sales | Complaints | Reports |
|--------|-----|-------|------------|---------|
| CRM | — | 82% | 61% | 45% |
| Sales | 82% | — | 54% | 39% |
| Complaints | 61% | 54% | — | 31% |

Do not fabricate values.
Calculate them from the data.

---

# 7. Customer Name / Company Name Analysis

Customer/company names are likely to be important for entity resolution.

Analyze:

- number of unique names
- duplicate names
- spelling variations
- casing variations
- whitespace differences
- punctuation differences
- abbreviations
- Persian/English variations
- legal suffixes
- common prefixes/suffixes

Examples of potential normalization:

- "ABC Co."
- "ABC Company"
- "ABC CO"
- "ABC Company Ltd."

These may or may not represent the same entity.

Do NOT automatically merge them during EDA.

Instead, identify the problem and quantify it.

If the data contains Persian text, explicitly inspect:

- Arabic vs Persian characters
- نیم‌فاصله
- ی / ي
- ک / ك
- Persian/Arabic numerals
- inconsistent whitespace
- punctuation

---

# 8. Contact Information Analysis

For phone numbers:

Analyze:

- formatting differences
- country codes
- leading zeros
- spaces
- dashes
- duplicate numbers
- multiple customers sharing a number

For email:

Analyze:

- casing
- whitespace
- malformed emails
- duplicate emails
- multiple emails per customer
- shared organizational emails

The notebook should estimate how useful phone/email could be
for deterministic identity resolution.

---

# 9. Transaction / Sales EDA

For sales/orders:

Analyze:

- total orders
- unique customers
- unique products
- revenue
- quantity
- average order value
- orders per customer
- revenue per customer
- purchase frequency
- purchase recency
- product diversity

Create useful distributions:

- orders per customer
- revenue per customer
- quantity distribution
- product distribution
- customer purchase frequency

Analyze trends over time if dates exist.

Potential customer-level features should be identified,
but not necessarily implemented as the final feature engineering pipeline.

---

# 10. Product and Price EDA

Analyze:

- number of products
- unique product IDs
- product categories
- product names
- price distributions
- price changes
- products per customer
- customer-product relationships

Look for:

- duplicate products
- inconsistent product names
- missing product IDs
- inconsistent pricing

Identify whether product information could later help understand
customer behavior.

---

# 11. CRM EDA

Analyze:

- number of CRM records
- unique customers
- interaction types
- interaction frequency
- dates
- statuses
- sales stages
- text fields
- missingness

If CRM notes or descriptions exist:

Analyze:

- text length
- language
- empty text
- duplicate text
- common keywords
- common topics where practical

Do not perform expensive NLP unnecessarily.

The goal is to understand whether semantic embeddings
could be useful later.

---

# 12. Sales Expert Reports / Notes

Treat expert reports as unstructured data.

Analyze:

- number of reports
- reports per customer
- text length
- average text length
- missing text
- duplicate reports
- date distribution
- language
- common terms/topics

Identify whether reports contain information not present
in structured CRM fields.

Example categories may include:

- customer needs
- complaints
- purchase intention
- competitor information
- product requirements
- relationship status
- risks

Do not assume these categories exist.
Discover them from the actual data.

---

# 13. Complaint EDA

Analyze:

- total complaints
- complaints per customer
- complaint categories
- complaint status
- dates
- resolution time if available
- repeated complaints
- text fields

Investigate:

- most common complaint categories
- customers with unusually high complaint counts
- relationship between complaints and sales when data permits
- temporal relationship between complaints and purchases

Do not infer causality during EDA.

Use language such as:

- "associated with"

rather than:

- "caused by"

---

# 14. Product Development / Innovation Requests

Analyze:

- number of requests
- requests per customer
- request categories
- dates
- status
- text fields
- repeated requests

If text exists:

- text length
- common topics
- semantic similarity potential
- recurring customer needs

Investigate whether multiple customers appear to request
similar products/features.

This may later support customer segmentation or opportunity discovery.

---

# 15. Customer-Level 360 EDA

After understanding each source independently,
create a preliminary customer-level view.

For customers that can be linked reliably,
calculate:

- number of orders
- total revenue
- number of complaints
- number of CRM interactions
- number of sales reports
- number of product requests
- last purchase date
- last interaction date
- complaint frequency
- product diversity

This should answer:

"What information do we actually have about each customer?"

Identify customers with:

- rich data
- sparse data
- only sales data
- only CRM data
- only complaints
- multiple sources
- no reliable cross-source linkage

---

# 16. Entity Resolution Readiness

The notebook must explicitly evaluate how suitable the dataset is
for entity resolution.

Create a final analysis such as:

### Strong signals

- exact customer ID
- exact email
- exact phone

### Medium signals

- company name
- person name
- address
- city

### Weak/semantic signals

- free-text CRM notes
- sales reports
- complaints
- product requests

Then estimate how many records could be matched using:

1. exact identifiers
2. normalized identifiers
3. structured/fuzzy matching
4. semantic matching

This section should provide evidence for which matching strategy
should be implemented next.

---

# 17. Text / Embedding Readiness

For each text-containing dataset, report:

- number of text records
- average text length
- median text length
- empty percentage
- duplicate percentage
- language distribution if practical
- sample representative texts

Then answer:

"Where could semantic embeddings provide value?"

Potential use cases:

- resolving ambiguous customer records
- finding similar complaints
- finding similar customer needs
- retrieving relevant customer interactions
- semantic search for the AI Copilot

Do not generate embeddings in the EDA notebook unless explicitly requested.

EDA should determine whether embeddings are justified.

---

# 18. Relationships Between Data Sources

Investigate relationships such as:

- Customer → Orders
- Customer → Complaints
- Customer → CRM interactions
- Customer → Sales reports
- Customer → Product requests
- Customer → Products

Create simple relationship statistics.

Example:

```text
Customer
 ├── 12 Orders
 ├── 3 Complaints
 ├── 7 CRM Interactions
 ├── 2 Sales Reports
 └── 4 Product Requests
```

Look for sources that contain valuable information
not available elsewhere.

---

# 19. Visualizations

Use visualizations only when they answer a question.

Preferred visualizations:

* missing-value bar charts
* distributions
* histograms
* time-series charts
* customer activity distributions
* top categories
* source overlap
* relationship counts
* correlation heatmaps where meaningful

Avoid producing dozens of meaningless charts.

Every visualization should have:

* clear title
* axis labels
* useful interpretation

---

# 20. Notebook Structure

The generated notebook should follow this structure:

1. Environment and imports
2. Dataset discovery
3. Dataset overview
4. Schema profiling
5. Data quality
6. Duplicate analysis
7. Customer identity analysis
8. Cross-source overlap
9. Customer/company name analysis
10. Contact information analysis
11. Sales/orders EDA
12. Product/price EDA
13. CRM EDA
14. Sales expert reports EDA
15. Complaints EDA
16. Product/innovation requests EDA
17. Preliminary Customer 360
18. Entity resolution readiness
19. Embedding/text readiness
20. Cross-source relationships
21. Key findings
22. Recommendations for the next modeling stage

The notebook should be readable and modular.

---

# 21. Final EDA Report

The final notebook section must provide a concise summary.

Include:

## Dataset Summary

What data exists?

## Data Quality

What are the biggest quality problems?

## Identity Resolution

What identifiers exist?
How much data can be matched directly?

## Cross-Source Coverage

Which sources can be connected?
Which sources are isolated?

## Text Data

Which sources contain useful unstructured information?

## Customer 360 Potential

What can realistically be built from the available data?

## Recommended Next Steps

Recommend the next technical steps based ONLY on findings from the EDA.

For example:

* normalization
* exact matching
* candidate generation
* fuzzy matching
* embedding-based matching
* customer-level feature engineering

Do not make recommendations that are unsupported by the observed data.

---

# Important Rules

1. Inspect the actual data before making assumptions.
2. Never fabricate statistics.
3. Never silently drop data.
4. Clearly distinguish missing data from zero values.
5. Do not perform entity resolution as part of EDA.
6. Do not train ML models during EDA.
7. Do not generate embeddings unless explicitly requested.
8. Do not claim causality from correlations.
9. Preserve raw data.
10. Prefer efficient processing for large datasets.
11. Use Polars/Pandas appropriately based on dataset size.
12. Make the notebook reproducible.
13. Store intermediate EDA outputs only when useful.
14. Keep visualizations focused and interpretable.
15. End with concrete findings that directly inform Customer 360 design.

The purpose of this notebook is not simply to "explore the data".

Its purpose is to answer:

> "What does this multi-source dataset actually contain, how can we reliably connect the sources to the same customers, and what architecture should we build based on the evidence?"
