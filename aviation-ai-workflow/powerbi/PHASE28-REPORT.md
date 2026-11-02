# AeroCIE Phase 28 | StrategicRisk Partners

Branded four-page PBIR reporting implementation, built against the synthetic-only model.

## Pages
- Executive Overview | dynamic advisory KPI cards, classification mix, low/base/high severity
- Underwriting Risk Analysis | evidence, exposure, aircraft, advisory slicers and review table
- MRO & Severity Intelligence | repair wait, parts cost, synthetic scenario analysis, observed MRO table
- Evidence Quality & Source Integrity | issue code and source-registry tables, demo-only disclosure

## Images and licenses
Three aviation illustrations were retrieved from the owner's Adobe Creative Cloud Firefly-generated assets and embedded in `StaticResources/RegisteredResources/` as JPEG. Their provenance is Adobe Creative Cloud **generated images**, not verified purchased Adobe Stock licenses. They must not be represented as licensed stock originals. Original purchased Adobe Stock photos may replace these assets after source file and license confirmation. Source references (Creative Cloud names): `787 COVERED IN DATA 55261 85s.ffgenimg`, `ge90 engine 53330 Met.ffgenimg`, `jet engine safety 43375 fLH.ffgenimg`.

## Windows review steps
1. Keep all existing databases and CSVs. Close Power BI before pulling this feature branch.
2. Pull this branch into a separate worktree or only after preserving any unsaved local report edits; opening the same PBIP in two processes is unsupported.
3. Open `aviation-ai-workflow/powerbi/AeroCIE-Underwriting.pbip` in Windows Power BI Desktop.
4. Edit `AeroCIEDataFolder` to point to the validated `powerbi-import\\` folder and refresh all tables.
5. Verify 7 total, Quote 2, Refer 4, Decline 1, 2 missing inputs, requested hull $34,045,000 (not insured), synthetic low/base/high $46,243/$104,080/$208,159.
6. Verify all four page tabs, visual titles, tables, images, slicers and no blank DAX values where evidence exists. Run full automated tests locally.

## Important limitations
- Static PBIR format and visual references prepared; **not tested for rendering in Power BI Desktop** from this environment.
- Visuals consume existing model measures and tables; no automatic quote/bind or underwriting authorization.
- No live insurer, Cirium, or commercial MRO source license is claimed.
- Image previews in this draft are 1200px Adobe Creative Cloud renditions, not stock originals.
- All data is synthetic; `release_authorized=false`. No client publication allowed.
