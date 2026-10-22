---
# DRAFT EXAMPLE. Check every line against your own report, replace the
# [bracketed] placeholders, then change status to: published
status: draft

name: Himadri Speciality Chemical Ltd
nse_symbol: HSCL
bse_code: "[add BSE code]"
sector: chemicals
cap_tier: "[small / mid / large]"
cap_tier_source: "[AMFI list, period]"

# Disclose any holding in this company. Required on every company page.
author_position: "[None / Holds shares — state which]"

summary: >-
  Carbon materials producer adding battery materials. Our review covers
  multiple quarters of calls and filings.

# The top findings shown first on the company page. Facts only, each
# linked to a source below. Aim for about ten; fewer is fine.
takeaways_as_of: 2026-10-21
takeaways:
  - topic: Business model
    text: The business runs on three layers [describe the three layers in one sentence].
    sources: [1]
  - topic: New products
    text: Management has set out five new product lines to be built out through FY28 [name them].
    sources: [2]
  - topic: Other income
    text: Mark-to-market gains on NCD holdings were booked in other income in [quarter], adding [₹ figure] to reported profit.
    sources: [1, 3]
  - topic: Disclosure
    text: The anode revenue figure disclosed for [period] matches the capex figure disclosed for the same line [state both figures].
    sources: [2, 3]
  - topic: Consolidation
    text: Standalone and consolidated figures differ by [₹ figure] in [period], and the gap is not explained in the notes.
    sources: [3]
  - topic: Hedging
    text: Hedging disclosures in [document A] and [document B] describe the policy differently [quote both briefly].
    sources: [1, 2]
  - topic: Unanswered questions
    text: Analyst questions on LFP cost economics were raised on [number] calls without a figure being given in reply.
    sources: [2]

sources:
  - id: 1
    label: Annual Report FY[year]
    url: "[link to the BSE filing]"
  - id: 2
    label: Q[n] FY[year] earnings call transcript
    url: "[link]"
  - id: 3
    label: Q[n] FY[year] financial results filing
    url: "[link]"

# Spreadsheet files readers can download. Put them in content/data/<company-slug>/
data_files:
  - file: signals.csv
    label: Signal table (figures by quarter, with source for each)
---

[Write the business summary here in plain language: what the company makes,
who buys it, how it earns money, and what has changed over time. Three or four
short paragraphs is plenty. Readers who want more go to the full reports below.]
