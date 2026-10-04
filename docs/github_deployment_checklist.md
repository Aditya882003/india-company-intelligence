# GitHub + Live Deployment Checklist

## GitHub

- [ ] Create a public GitHub repository named `india-company-intelligence`.
- [ ] Upload all repository files, including `.github/workflows/`.
- [ ] Confirm the default branch is `main`.
- [ ] Open **Actions** and confirm workflows are enabled.
- [ ] Run **Refresh company intelligence** manually once.
- [ ] Open the workflow run and confirm the validation step passes.
- [ ] Confirm `data/raw/price_daily.csv` and `data/processed/company_intelligence.db` changed after a successful refresh.

## Streamlit Community Cloud

- [ ] Sign in at https://share.streamlit.io/ with GitHub.
- [ ] Create a new app from your GitHub repository.
- [ ] Branch: `main`.
- [ ] Main file: `streamlit_app.py`.
- [ ] Python: 3.12.
- [ ] Deploy.
- [ ] Open the generated `*.streamlit.app` URL in an incognito browser to verify public access.

## First live-refresh test

After the app is live:

1. Go to GitHub → Actions.
2. Run `Refresh company intelligence` manually.
3. Wait for the workflow to finish.
4. Confirm the commit appears in the repository.
5. Refresh the Streamlit URL and verify the demo-data warning is gone when live financial data were returned.

## No secrets needed

The repository does not require an API key for its default pipeline. If you later add a paid provider, store credentials in GitHub Actions Secrets and/or Streamlit Secrets, never in source files.
