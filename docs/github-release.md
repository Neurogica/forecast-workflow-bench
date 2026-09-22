# GitHub source release

The source is prepared on `release/objective-main-1251-v3`. Review and merge the
pull request after CI passes. Keep the repository private until the owner chooses
to publish it. Observation histories and reproduction targets are distributed on
Hugging Face, separately from the source repository.

Run `uv run --extra dev bash scripts/check.sh` before submitting changes. Submit
subsequent changes through pull requests; do not force-push over unrelated history.
