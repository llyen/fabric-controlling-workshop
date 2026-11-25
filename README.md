# Microsoft Fabric workshop for controlling and finance teams

[Wersja polska](README.pl.md)

This repository contains a complete, reproducible 90-minute workshop showing how a corporate controlling and finance team can use Microsoft Fabric. It covers three areas:

* Plan in Fabric IQ (Planning): spreading a sales target, a cost budget in PowerTable, simulation and forecast, comments, approval and writeback to Fabric SQL database,
* Fabric data agents: the same agent on a model prepared for AI and on a raw model, measured against a fixed set of test questions,
* Direct Lake semantic models on a lakehouse, with DAX checks of every measure.

The workshop is built around Fabrikam Fashion, a fictional apparel retailer with four fictional brands (Aurea, Vento, Lumi, Kroko) operating in six European countries. Its fiscal year runs from April to March and the data is frozen on 9 December 2026. All documentation except this file is in Polish.

> **Disclaimer.** All data in this repository is synthetic and was produced by the generator in `generator/`. Fabrikam Fashion and its brands are fictional; only country and city names are real. Stores, cost centres, amounts and business events are invented and do not describe the results of any real company. Any resemblance to real brands or companies is coincidental.

## Contents

```text
dane/                   14 tables in CSV and Parquet, 5 Excel files, data dictionary, answer key for 14 test questions
generator/              synthetic data generator and validation (generator/README.md, generator/SPEC.md)
fabric/semantic_model/  TMDL for SM_Kontroling, SM_Kontroling_surowy and SM_Planowanie, AI instructions
fabric/data_agent/      data agent instructions
fabric/plan/            2027/28 sales target allocation key, fallback Excel source for Plan
fabric/deploy/          deployment to Fabric via REST API, DAX checks, agent test over MCP
dokumentacja/           workshop scenario (Markdown and docx), test results, docx export script
```

The main document is `dokumentacja/Scenariusz_warsztatu.md`. Chapter 4 is a click-by-click script where every step lists the path in the UI and a control figure the screen should show. Other chapters cover licensing and capacity costs, pilot options, open questions and gaps in the documentation. Appendices hold the agent test results, environment reproduction steps and Microsoft Learn sources. `dokumentacja/docx/Scenariusz_warsztatu.docx` is a Word export of the same document.

## Requirements

* Python 3.13 (tested on Windows) with the packages from `generator/requirements.txt` (pandas, numpy, pyarrow, openpyxl),
* `requests` for deployment and `mcp` for the agent test,
* Azure CLI, signed in with `az login` to an account that can create workspaces in the target Fabric tenant,
* a paid Fabric capacity (F2 or larger) for data agents and Copilot,
* pandoc, only if you want to rebuild the docx files.

## Reproducing the workshop

Data, TMDL definitions and the allocation key are already committed, so deployment alone needs only the second block. The first block rebuilds those files from scratch and is fully deterministic.

```powershell
python generator\generate_data.py
python generator\validate.py --determinism
python fabric\semantic_model\build_tmdl.py
python fabric\plan\klucz_alokacji_2027_28.py
python fabric\plan\excel_awaryjny_planu.py
```

```powershell
$env:FABRIC_WORKSPACE = "Fabrikam Kontroling Warsztat"
$env:FABRIC_CAPACITY_ID = "<CAPACITY_ID>"
python fabric\deploy\deploy.py
python fabric\deploy\weryfikuj_model.py
python fabric\deploy\testuj_agenta.py
```

`FABRIC_CAPACITY_ID` is the capacity ID from the Fabric API, not the Azure resource ID. It is needed only when the workspace has to be created or moved to another capacity. `deploy.py` runs nine steps (obszar, lakehouse, pliki, tabele, sql, modele, odswiez, sqldb, agenci); `--kroki` runs a subset. IDs of created items are stored in `fabric/deploy/.stan_wdrozenia.json`, which is git-ignored.

To rebuild the docx files run `python dokumentacja\eksport_docx.py`. Set the `PANDOC` environment variable if pandoc is not on PATH.

## Results of tenant runs

The synthetic data was regenerated for this public release. The DAX check results and the data agent answers from the original tenant run no longer match the data, so `dokumentacja/wyniki_weryfikacji_dax.md` and `dokumentacja/wyniki_testu_agentow.md` are placeholders. Run `weryfikuj_model.py` and `testuj_agenta.py` after deployment to fill them in. The expected values are in `dane/oczekiwane_odpowiedzi.md`.

## Manual steps

The scripts do not create the Plan item or the Power BI report. Plan_Kontroling is built by hand following step P0 of the scenario. Before that, SM_Planowanie must be mapped to a shareable cloud connection with a fixed identity (OAuth 2.0, service principal or workspace identity, SSO off). With the default SSO the plan does not connect to a Direct Lake model. The `modele` step of `deploy.py` warns when such a connection is missing. Tenant and capacity settings, verified answers and the Approved for Copilot flag are also manual; appendix B of the scenario lists all of them.

## Notes on identifiers

The repository contains no passwords, keys, or tenant, subscription, capacity, workspace or item IDs. The GUIDs in the TMDL files and in the Copilot folder (lineageTag and related) are not taken from any tenant: `build_tmdl.py` derives them deterministically as UUIDv5 values from model object names.

## License

MIT, see [LICENSE](LICENSE).
