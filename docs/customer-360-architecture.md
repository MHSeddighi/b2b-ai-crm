# Customer 360 Architecture

> **Persistent technical context.**
> Before making any future architectural or implementation decisions related to Customer 360,
> always read this file first.

## Goal

The goal is to combine customer-related data scattered across multiple organizational
systems and connect each record to a canonical **Customer Master** with a **confidence score**.

Available data sources include:

- Customer master / basic information
- CRM data
- Sales and orders
- Products and prices
- Sales expert reports / notes
- Customer complaints
- Product development requests
- Innovation requests
- Data from multiple organizational systems

## Core Architecture

**Do NOT perform pairwise matching between every data source.**

Instead, create a canonical **Customer Master** and independently link every source to it:

```text
Customer Master
    ├── CRM
    ├── Sales / Orders
    ├── Complaints
    ├── Sales Reports
    └── Product / Innovation Requests
```

Each source record should eventually carry:

- `source`
- `source_record_id`
- `customer_id`
- `confidence`
- `matching_method`

### Example

| Source    | Canonical Customer | Confidence |
| --------- | ------------------ | ---------- |
| CRM       | Customer C1        | 0.98       |
| Sales     | Customer C1        | 0.91       |
| Complaint | Customer C1        | 0.96       |

This produces the unified **Customer 360** view.

## Entity Resolution

The core problem is:

> "Given a record from any source, determine which canonical customer it belongs to."

Use a **staged approach** rather than one complicated algorithm.

### 1. Exact matching

Use reliable identifiers first:

- customer ID
- email
- phone
- company / national identifier

### 2. Candidate generation / blocking

Do not compare every source record with every customer.

First retrieve a small set of likely candidate customers using inexpensive signals such as:

- normalized name
- company name
- phone
- email
- city
- industry

### 3. Detailed matching

For candidates, calculate similarity using appropriate signals:

- exact field matches
- fuzzy string similarity
- structured field similarity
- semantic similarity for free text

### 4. Confidence score

Produce a final confidence score and matching explanation.

Example:

```text
97% match

- phone exact match
- company similarity: 96%
- name similarity: 93%
- semantic similarity: 94%
```

The system **must** be able to return "uncertain" instead of forcing a match.

## Embeddings

Embeddings are **NOT** the solution for every field.

Use **exact / structured matching** for:

- phone
- email
- IDs
- other identifiers

Use **fuzzy matching** for:

- names
- company names
- addresses

Use **embeddings mainly for unstructured text**:

- sales expert reports
- CRM notes
- complaints
- product requests
- innovation requests

Embeddings should be treated as **one source of evidence** in entity resolution,
not as the entire matching system.

## Customer 360 Representation

After records are linked to a canonical customer, the customer can be represented as:

```text
Customer
├── Identity / Profile
├── Sales & Orders
├── CRM interactions
├── Complaints
├── Sales expert reports
└── Product / Innovation needs
```

Keep **structured behavioral data** and **text / embedding representations** separate
where appropriate.

Do **not** create one giant customer embedding by default.

## MVP Strategy

Keep the first implementation simple:

```text
Exact matching
    ↓
Candidate generation
    ↓
Fuzzy / structured similarity
    ↓
Embedding similarity for text when useful
    ↓
Confidence score
    ↓
Customer 360
```

Do **not** introduce complex graph databases, distributed data systems, or custom
deep-learning entity-resolution models unless the dataset proves they are necessary.

## Important Principles

- Every source should ultimately link to the Customer Master.
- Avoid source-to-source pairwise matching.
- Use the simplest reliable matching technique for each field.
- Embeddings are mainly useful for semantic / unstructured information.
- Candidate generation should happen before expensive matching.
- Every match should have a confidence score.
- Low-confidence matches should remain unresolved / reviewable.
- Preserve the matching method and evidence for explainability.
- The LLM should not be responsible for deciding customer identity by itself.
