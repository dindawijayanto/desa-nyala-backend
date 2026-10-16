# Source, licensing, and reproducibility

Upstream project: https://github.com/rl-institut/offgridders

The upstream project is distributed under GPL-3.0 according to its repository metadata. The source import script copies the user's local checkout, its actual license file, and records the Git commit/remote. Preserve all upstream copyright and license notices. Before publishing a combined/modified backend, review GPL-3.0's distribution requirements with the actual code layout and dependencies.

DesaNyala-authored code lives under `app/`, `scripts/`, `docs/`, and `tests/`. Any adaptations made inside `engine/offgridders/` should be documented in a change log. Do not claim upstream code as newly authored.

The source checkout was not included in the generated archive because it was not available in the artifact workspace. Run `scripts/import_offgridders.ps1` from the backend folder to populate `engine/offgridders` from the user's already-cloned repo.
