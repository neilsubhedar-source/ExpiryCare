# Frontend Integrity Notes

The original visual structure and styling have been preserved as far as practical. Two frontend files were intentionally updated to fix the chatbot messaging and configure the API URL for same-origin Flask serving or common local static-server ports:

- `frontend/js/app.js`
- `frontend/healthcare-guidance.html`

The ZIP did not contain the `baseline_hashes.json` file expected by the previous hash test, so the old 27-file cryptographic verification claim was not reproducible. The test now checks that required frontend pages/assets exist and that chatbot/API configuration is present. This is a basic integrity check, not proof that every original file is byte-for-byte unchanged.
