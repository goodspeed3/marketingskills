---
name: ktmine-tools
description: Fetch patent data and statistics from ktMINE. Use when user asks about patent data, application details, priority claims, inventors, assignees, claims, assignee statistics, filing counts, or any patent-related information that can be retrieved from ktMINE.
allowed-tools: Bash(NODE_ENV=development npx tsx:*), Read, Glob
---

# ktMINE Tools

Collection of scripts to fetch patent data and statistics from ktMINE.

## Available Scripts

### 1. getApplicationData.ts - Fetch Patent by Application Number

Fetches detailed patent/application data for a specific application number.

```bash
NODE_ENV=development npx tsx --tsconfig tsconfig.base.json apps/server/src/poc/ktMINE/skills/getApplicationData.ts <application_number>
```

**Application Number Formats:**
- US application numbers: `12345678`, `US12345678`
- PCT applications: `WO2021055192`
- European patents: `EP12345A1`
- With or without country code prefix
- With or without kind code suffix

**Output includes:**
- `documentNumber` - The patent/publication number
- `inventionTitle` - Title of the invention
- `applicationReference` - Application filing details
- `publicationReference` - Publication details
- `minPriorityDate` - Earliest priority date
- `priorityClaims` - Array of priority claims
- `claims` - Array of patent claims
- `inventors` - Array of inventors
- `applicants` - Array of applicants
- `currentAssignees` - Current patent owners
- `legalStatus` - Current legal status
- `backwardCitations`, `forwardCitations` - Citation data
- `legalEvents` - Patent legal events history
- And more...

### 2. getPublicationData.ts - Fetch Patent by Publication Number

Fetches detailed patent data for a specific publication number.

```bash
NODE_ENV=development npx tsx --tsconfig tsconfig.base.json apps/server/src/poc/ktMINE/skills/getPublicationData.ts <publication_number>
```

**Publication Number Formats:**
- US granted patents: `US11234567B2`, `US11234567`
- US applications: `US20040044924A1`, `US2004044924A1`
- Design patents: `USD551237`
- PCT publications: `WO2021055192A1`
- With or without kind code suffix

**Output:** Same fields as getApplicationData.ts

### 3. getAssigneeStats.ts - Fetch Assignee Statistics

Fetches patent statistics for a given company/assignee name.

```bash
NODE_ENV=development npx tsx --tsconfig tsconfig.base.json apps/server/src/poc/ktMINE/skills/getAssigneeStats.ts "<assignee_name>"
```

**Note:** Assignee name should be quoted if it contains spaces.

**Automatic Company Resolution:**
If the provided company name doesn't return any patents, the script automatically:
1. Searches for similar companies using the ktMINE company search API
2. Queries patent counts for each matching company
3. Groups companies by their parent company ID to aggregate related subsidiaries
4. Selects the company/parent with the highest total patent count
5. Uses that resolved company name for the statistics query

This helps when users provide partial names like "Apple" instead of "Apple Inc" or "Google" instead of "Google LLC".

**Output includes:**
- `assigneeName` - The company name used for the query (may be resolved)
- `originalQuery` - The original input provided by the user
- `wasResolved` - Whether the company name was resolved from the original query
- `usGrantedCount` - Number of granted US patents
- `usPendingCount` - Number of pending US applications
- `worldwideGrantedCount` - Number of granted worldwide patents
- `worldwidePendingCount` - Number of pending worldwide applications
- `yearlyFilings` - Filing counts per year (last 5 years)
- `queryDate` - When the query was run

## Output Location

All scripts save their output to JSON files in:
```
apps/server/src/poc/ktMINE/output/
```

The output files include:
- `request` - Description of the query
- `response` - Full data returned from ktMINE

## Examples

### Get Patent Details

**User asks:** "Get me the priority claims for application WO2021055192"

1. Run: `NODE_ENV=development npx tsx --tsconfig tsconfig.base.json apps/server/src/poc/ktMINE/skills/getApplicationData.ts WO2021055192`
2. Read the output JSON file
3. Extract and display the `priorityClaims` array

**User asks:** "Who are the inventors on patent US12345678?"

1. Run: `NODE_ENV=development npx tsx --tsconfig tsconfig.base.json apps/server/src/poc/ktMINE/skills/getApplicationData.ts US12345678`
2. Read the output JSON file
3. Extract and display the `inventors` array

### Get Patent by Publication Number

**User asks:** "Get details for patent US11234567B2"

1. Run: `NODE_ENV=development npx tsx --tsconfig tsconfig.base.json apps/server/src/poc/ktMINE/skills/getPublicationData.ts US11234567B2`
2. Read the output JSON file
3. Extract and display requested information

**User asks:** "What's the legal status of US20220012345A1?"

1. Run: `NODE_ENV=development npx tsx --tsconfig tsconfig.base.json apps/server/src/poc/ktMINE/skills/getPublicationData.ts US20220012345A1`
2. Read the output JSON file
3. Report the `legalStatus` field

### Get Assignee Statistics

**User asks:** "How many US patents does Apple have?"

1. Run: `NODE_ENV=development npx tsx --tsconfig tsconfig.base.json apps/server/src/poc/ktMINE/skills/getAssigneeStats.ts "Apple Inc"`
2. Read the output JSON file
3. Report the `usGrantedCount` and `usPendingCount`

**User asks:** "What's the average number of patent filings per year for Microsoft?"

1. Run: `NODE_ENV=development npx tsx --tsconfig tsconfig.base.json apps/server/src/poc/ktMINE/skills/getAssigneeStats.ts "Microsoft Corporation"`
2. Read the output JSON file
3. Report the `avgFilingsPerYear` and `filingsLast3Years`

**User asks:** "Compare the patent portfolios of Google and Amazon"

1. Run both commands in parallel:
   - `NODE_ENV=development npx tsx --tsconfig tsconfig.base.json apps/server/src/poc/ktMINE/skills/getAssigneeStats.ts "Google LLC"`
   - `NODE_ENV=development npx tsx --tsconfig tsconfig.base.json apps/server/src/poc/ktMINE/skills/getAssigneeStats.ts "Amazon Technologies Inc"`
2. Read both output JSON files
3. Compare the statistics side by side
