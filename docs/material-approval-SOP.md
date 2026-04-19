# Material Approval Page — Standard Operating Procedure

Author: GO Corporation Co., Ltd.
Last updated: 2026-04-19
Owning project: `go-documents`
Template: `leka-material-approval`
Code format: `MA{YY}-{NNN}` (e.g., `MA26-001`)

This SOP explains how to produce a Leka Studio **Request for Material Approval** page
end-to-end — from data gathering to Firestore record to live URL.

---

## 1. When to use this workflow

Use a Material Approval record whenever a material (fabric, membrane, panel, flooring,
hardware, etc.) must be submitted to a Consultant, Designer, or Project Owner for
approval, information, or reference.

Two common shapes:

| Mode | Example | Notes |
|---|---|---|
| **Library record** | `MA26-001` Soltis 502 Proof | `project.project_name = "Material Library"` — reusable seed for future project RFAs. |
| **Project RFA** | `MA26-045` Soltis 86 on project SO26-019 | `project.project_code` set; approvers named; signed dates populated. |

---

## 2. Data model (at a glance)

Firestore writes land in three collections on the `go-documents` database
(`asia-southeast1`):

| Collection | Document ID | Purpose |
|---|---|---|
| `document-templates` | `leka-material-approval` | Template definition (fields, design tokens, example file). |
| `document-records` | `MA{YY}-{NNN}` | One record per approval request. |
| `document_counters` | `material-approval-{year}` | Running number tracker. |

Pydantic models: [`src/firestore_material_approval_models.py`](../src/firestore_material_approval_models.py)

Key shape (simplified):

```
MaterialApproval
├── approval_code          # "MA26-001"
├── document_ref           # optional external ref, e.g. "MAT-SOLTIS-502-PROOF"
├── title
├── status                 # draft / submitted / for_approval / approved / ...
├── project { project_name, project_code, client_owner, consultant_designer }
├── materials[]            # one or more MaterialRecord
│   ├── material_name, code, description, category, main_application
│   ├── attachments[]      { name, url, content_type }
│   ├── images[]           { url, caption, role, credit }
│   ├── colors[]           { code, name, hex, finish, notes }
│   ├── manufacturer_product_url
│   └── composition, weight, thickness, roll_width, use_cases[]
├── approvals[]            # { role, name, decision, signed_at }
├── prepared_by
├── formal_note, submission_notes
├── issue_date, document_date, submitted_at, approved_at
└── created_by, updated_by, revision_history[]
```

---

## 3. End-to-end workflow

### Step 1 — Gather source material

For each material you plan to submit, collect:

1. **Manufacturer product URL** (authoritative, not a reseller).
2. **Product images** — hero / application shots / gallery. Prefer the manufacturer's
   own CDN URLs so they stay live.
3. **Color / finish range** — manufacturer codes are authoritative; hex values are
   display approximations only and must be flagged as such.
4. **Datasheet facts** — composition, weight, thickness, roll width, use cases.
5. **Attachments** — brochure PDFs, spec sheets, warranty docs. Use the Notion/Drive
   URL you plan to persist long-term.

If the manufacturer page is publicly accessible, the `WebFetch` tool is the fastest
way to pull images + colors:

```
WebFetch(
  url = "https://www.sergeferrari.com/en/products/soltis/502-proof/",
  prompt = "Extract all product image URLs (full absolute URLs + short captions) \
  and any list of color names/codes on the page."
)
```

### Step 2 — Pick the approval code

Read `document_counters/material-approval-{year}`, increment `last_number`, and
format the code as `MA{YY}-{NNN}` (e.g., year 2026, number 7 → `MA26-007`).
The document ID in `document-records` equals this code.

### Step 3 — Build the HTML preview (optional but recommended)

Two templates live at the project root:

- [`material-approval-template.html`](../material-approval-template.html) — blank
  starter, Leka Studio design tokens.
- [`docs/materials/soltis-502-proof.html`](./materials/soltis-502-proof.html) —
  reference example with hero, project snapshot, material card, **Pictures**,
  **Color Palette**, Submission Notes, Datasheet Facts, and Approval Routing.

To make a new material page:

1. Copy `docs/materials/soltis-502-proof.html` →
   `docs/materials/<slug>.html` (slug is lowercase kebab-case).
2. Replace hero title, eyebrow, description.
3. Update the Project Snapshot grid (client, consultant, main application).
4. Swap the Material Card code, title, description, and pill row.
5. Replace Pictures — use `.img-wrap > img + figcaption` so long captions don't
   clip:

    ```html
    <div class="gallery-item">
      <figure>
        <div class="img-wrap">
          <img src="https://…/photo.jpg" alt="…" loading="lazy">
        </div>
        <figcaption>
          <strong>Caption title</strong>
          Short supporting line — credit manufacturer.
        </figcaption>
      </figure>
    </div>
    ```

6. Rebuild the Color Palette. One `.swatch` per color with manufacturer code under
   the name. Hex values are display-only — always include the palette note:

    > *Hex values are display approximations — verify against manufacturer fan-deck /
    > physical sample before final approval.*

7. Update Datasheet Facts (composition / weight / thickness / roll width).
8. Leave Approval Routing untouched unless you have role-specific names.

### Step 4 — Register in Firestore

Do **not** hand-roll Firestore writes. Use the seed-driven bulk pattern:

1. Add a new entry to [`data/material-approvals.seed.json`](../data/material-approvals.seed.json).
   Fields mirror the Pydantic model.
2. Run the bulk script:

    ```bash
    python push_material_approvals_bulk.py
    ```

   The script is idempotent (it uses `approval_code` as the document ID and
   `.set()` semantics), so re-running is safe and will update existing records.
3. Verify the counter `document_counters/material-approval-{year}` reflects the
   highest `last_number` used.

For one-offs, `push_material_approval_firestore.py` shows the hardcoded pattern
(used for `MA26-001`).

### Step 5 — Serve at the canonical URL

`src/app.py` already routes `/material-approvals/<doc_id>` to the record. No
change needed unless you're adding a new document type.

- Leka Studio materials → `https://docs.leka.studio/material-approvals/MA26-00X`
- Areda-branded materials (template_id starts with `areda`) → `https://docs.aredaatelier.com/…`

If you've uploaded a rendered HTML to GCS, set `generated_html_gcs` on the
record and the app serves it directly. Otherwise the fallback metadata page renders.

### Step 6 — Document and ship

1. Append a semver entry to `CHANGELOG.md` (what, which codes, source).
2. Update `build-summary.html`.
3. `git add` → `git commit` → `git push origin main` (or feature branch + PR).
4. Cloud Build auto-deploys.

---

## 4. Style rules (non-negotiable)

- **Manufacturer codes are authoritative; hex is display-only.** Always label
  hex as an approximation and include the palette note.
- **Captions flow naturally.** Never put `aspect-ratio` + `overflow: hidden` on
  the outer gallery card — captions get clipped. Use `.img-wrap` inside.
- **Breakpoints** (already encoded in `soltis-502-proof.html`):
  - Gallery: 3 → 2 (≤900px) → 1 (≤480px)
  - Palette: 6 → 5 (≤1040px) → 4 (≤900px) → 3 (≤640px) → 2 (≤480px)
  - Hero / project / approvals grids: 2-col on tablets; 1-col at ≤640px.
- **Prepared by** defaults to `GO Corporation Co., Ltd.`
- **Approval roles** default to: Consultant · Designer · Project Owner.
- **Language:** `en` by default; use `th` when the submission is Thai-language only.

---

## 5. Bulk creation (batch import)

To submit a batch of materials at once:

1. Assemble product entries in [`data/material-approvals.seed.json`](../data/material-approvals.seed.json)
   (one object per material approval).
2. Ensure each entry has a unique `approval_code`. The bulk script will **not**
   allocate codes for you — pre-assign them sequentially from the counter.
3. Run:

    ```bash
    python push_material_approvals_bulk.py
    ```

4. The script:
   - Ensures the `leka-material-approval` template exists.
   - Writes every seed entry to `document-records/<approval_code>`.
   - Advances `document_counters/material-approval-{year}` to the max
     `last_number` observed.

Keep the seed file committed — it is the source of truth for all auto-generated
material library records.

---

## 6. Checklist before you ship

- [ ] Approval code follows `MA{YY}-{NNN}` and is not already in use.
- [ ] Manufacturer URL opens and is not a marketing landing page.
- [ ] All image URLs resolve (no 404s); each carries a caption and credit.
- [ ] Colors use real manufacturer codes; hex is labeled as approximate.
- [ ] Datasheet facts are present (composition, weight, thickness, roll width).
- [ ] Project Snapshot is filled (library record *or* project-specific).
- [ ] Approval Routing cards are present even if signatures are blank.
- [ ] Seed entry added + `push_material_approvals_bulk.py` run successfully.
- [ ] CHANGELOG + `build-summary.html` bumped.
- [ ] `git push` complete; Cloud Build green.
