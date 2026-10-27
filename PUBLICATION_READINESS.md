# Publication Readiness Audit

**Status: READY WITH LIMITATIONS for a review branch and pull request.** The user reports that the separately configured Desktop test copy opened and refreshed successfully, both pages loaded and six actual-model DAX checks passed. The candidate remains sanitized. The assistant did not independently execute the Desktop tests, and a fresh-clone placeholder setup and exhaustive filter/DAX coverage remain unverified. Review and approval are required before publication.

## Control results

| Area | Status | Evidence / limitation |
|---|---|---|
| Candidate contents | PASS | PBIP/PBIR/TMDL, theme, Python, SQL, synthetic CSV/SQLite, generated HTML, tests, references and instructions included. |
| GitHub comparison | PASS, read-only | Compared with main tree `61e80ab524f6cdd4043baaf2dfe39c2e2804f254`; see `PUBLICATION_MANIFEST.md`. Existing `LEARNING_TASKS.md` is unchanged. No remote files omitted from the candidate at comparison time. |
| Clean Python environment | PASS | New isolated virtual environment, `pip install -r requirements.txt` and `pip check`; no system tools installed. |
| Data pipeline | PASS | Generated 1,600 loans, 19,200 monthly records, SQLite, three KPI CSVs and HTML dashboard in a disposable test copy. |
| Python test suite | PASS | `pytest -q -p no:cacheprovider`: **37 passed** on the clean test copy. Tests do not execute DAX. |
| SQL | PASS | SQLite has 1,600 loans and 19,200 snapshots; three queries ran and returned 12, 13 and 3 rows respectively. |
| Regenerated data | PASS, semantic | Source and regenerated CSV tables compare equal as parsed data. Windows uses CRLF whereas the candidate contains LF; byte hashes differ. HTML can differ due to generated markup. |
| Original DAX export reconciliation | PASS, conditional | Real exports provided by the user, 12 + 36 rows × four measures = 192 values, passed against regenerated Python data. January/Subprime 90+ BLANK is normalized under the documented strict policy; the user separately confirmed BLANK in Power BI. The assistant did not independently query the model. |
| PBIP/PBIR/TMDL | PASS, user-verified test copy | The user reports successful open, refresh and loading of both pages. After Desktop verification, candidate and test-copy Power BI files match byte for byte except the configured path; the test copy also has local `.platform` metadata and three extra QA queries. Full visualContainer 2.14 schema validation and opening the unconfigured placeholder directly were not performed. |
| New page / presentation DAX | PASS, representative checks | The user reports all six `QA_Desktop_Check.dax` checks passed against the refreshed model: December KPI; January and previous month; multiple months not summed; four buckets and total; bucket share; segment and product. The assistant did not run the query. This does not exhaustively cover all months, filters, tooltips or visual states. |
| Privacy | PASS, limited scan | No Windows user paths, account-name string, private key marker, common GitHub token or AWS key pattern found in the candidate. A second heuristic text credential scan found no match, excluding third-party Plotly HTML and binary files. These scans are not proof that no secret exists; visually review images and all output before publishing. |
| Documentation links | PASS | Local Markdown links were checked after creation of this audit and manifest. External URLs were not revalidated in this audit. |
| Screenshots | PASS | User-provided Power BI images for Executive Overview and Delinquency & Portfolio Analysis are included and visually reviewed. The existing HTML dashboard preview is separately identified. |

## Isolated test versions

Python 3.12.14, NumPy 2.5.4, pandas 2.3.3, Plotly 6.9.0, pytest 9.1.1, pip 25.0.1. Transitive versions: colorama 0.4.6, iniconfig 2.3.1, narwhals 2.28.0, packaging 26.3, pluggy 1.7.0, Pygments 2.21.0, python-dateutil 3.0.0, pytz 2026.5, six 1.17.0 and tzdata 2026.5. These satisfy the declared version ranges; the ranges are not a lockfile.

## Publish and exclude

Candidate files listed in `PUBLICATION_MANIFEST.md`, plus that manifest and this audit, are the proposed publish set. Keep tracked synthetic data, SQLite, reference KPI tables, SQL, HTML, PBIP/PBIR/TMDL, registered theme resources and reproducible tests. Preserve `LEARNING_TASKS.md` unchanged. Never upload the isolated `.venv`, temp directory, `.pbi/cache.abf`, per-user `.pbi` settings, local logs, raw `.tsv` DAX exports, screenshots that reveal private information, or local audit hash files from the development workspace. `.gitignore` covers common future artifacts; review staged files manually.

`DataFolderPath` in the candidate is `SET_DATA_FOLDER_PATH`, not a real location. A person opening the project must change it to the clone's absolute `data` directory in Power Query, then apply changes and refresh. This is one-step configuration, not automatic relative-path resolution. Excluding the cache means data is unavailable until refresh. The user verified refresh in the separately configured test copy; setting the placeholder manually in a new clone has not been independently exercised.

## Changes relative to GitHub main

See `PUBLICATION_MANIFEST.md` for the exact file-level list. At comparison time, 15 existing files matched Git blob hashes, three existing files were modified (`README.md`, `powerbi/BUILD_GUIDE.md`, `src/pipeline.py`), 70 files were new, and none of the existing repository files were omitted. This audit and the manifest are two further new files. The pipeline change defers Plotly imports to the dashboard function; its analysis logic is unchanged. Candidate `tests/test_presentation.py` references the English validation table instead of a local Swedish UX report.

## Final candidate recheck

The publication candidate was rechecked using the existing isolated clean-test environment: **37 pytest tests passed** and the 192-value export reconciliation passed under its documented conditional BLANK policy. The sanitized placeholder remains intact; no virtual environments, `.pbi` caches or settings, TSV exports, logs or bytecode are present. Limited path/token pattern scans returned no hits. Local Markdown links and the read-only manifest comparison were checked; scans are not proof that the candidate is free of every secret.

## User-reported Desktop verification

The user reports that the configured test-copy PBIP opened correctly, both report pages loaded with expected visuals and KPI cards, and refresh completed without errors. The following checks from `QA_Desktop_Check.dax` were run against the actual Power BI model and reported as **6 of 6 PASS**:

1. December KPI.
2. January and previous month.
3. Multiple months not summed.
4. Four buckets and total.
5. Bucket share.
6. Segment and product.

This is user-reported Desktop evidence, not an independently executed tool result. The local test query and machine-specific parameter are not part of the sanitized candidate. A post-test file comparison found that the report/model definitions and all other candidate Power BI files matched the test copy, except the data-folder parameter. The test copy contained generated `.platform` files and the three prepared QA query files in addition to the candidate. Locally generated `.pbi` cache/settings were excluded from that comparison and are not part of the candidate.

## Review branch and pull request checklist

1. Review `PUBLICATION_MANIFEST.md` against the current GitHub main and review the staged diff; do not change learning/progression material. The most recent read-only comparison found 3 modified, 74 new and 15 unchanged files, with no missing existing files.
2. On the review branch or before merge, validate setting `DataFolderPath` from the placeholder in a fresh clone and refreshing; the test copy used a preconfigured local path. Check any remaining formatting, tooltips and broader filter combinations as appropriate.
3. Review the included Power BI screenshots and the final diff. The opening `assets/dashboard_preview.png` is an HTML dashboard image, not a Power BI screenshot.
4. Exclude environments, caches, local settings, TSV exports and sensitive files; review screenshots and the final diff.
5. Create a branch, commit, push or open a PR only after separate explicit authorization. This audit performed no GitHub changes.

## Power BI screenshot follow-up

User-provided screenshots were found already present at `assets/powerbi-executive-overview.png` and `assets/powerbi-delinquency-analysis.png`. Both show the intended report pages and synthetic-data labels; the files were visually reviewed and included in README. Dimensions: 1962 × 1058 (108,615 bytes) and 1949 × 1089 (136,051 bytes), respectively. No image processing was necessary. This confirms screenshot content, not a new execution of the Power BI model.
