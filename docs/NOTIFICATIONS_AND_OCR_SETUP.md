# Expiry notifications and scanner deployment checklist

## What this adds
- Email delivery through SMTP (Gmail SMTP is the default host).
- SMS delivery through Twilio.
- A daily job that checks live Firestore inventory and sends only to users who explicitly enable each channel.
- A per-product/date/channel notification log to avoid repeat sends during the same day.
- A portable OCR service that tries OpenAI Vision, then Gemini Vision, then local Tesseract if installed. It never hardcodes a developer's Windows path.

## Required setup (Render)
1. In Firebase, enable Cloud Firestore and create a service account. Store the JSON contents as a secret environment variable or use Render's secret file feature; do not commit the JSON file.
2. Configure the existing web service environment:
   - `FIRESTORE_ENABLED=true`
   - `FIREBASE_PROJECT_ID=<your-project-id>`
   - `GOOGLE_APPLICATION_CREDENTIALS=<path-to-secret-json-file>` (if using a Render secret file)
   - `SECRET_KEY=<long-random-secret>`
   - `OPENAI_API_KEY=<server-side-key>` (recommended for vision) OR `GEMINI_API_KEY=<server-side-key>`
3. For Gmail SMTP:
   - `SMTP_HOST=smtp.gmail.com`
   - `SMTP_PORT=587`
   - `SMTP_USERNAME=<sender-gmail-address>`
   - `SMTP_PASSWORD=<Google App Password>` (requires Google 2-Step Verification; never use your regular Gmail password)
   - `SMTP_FROM=<sender-gmail-address>`
4. For SMS:
   - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
   - Recipients must store a phone number in international E.164 format in `settings.phoneNumber` or `phoneNumber`.
5. In account settings, set `emailNotifications: true` and/or `smsNotifications: true` for explicit opt-in. Default is off. Add `phoneNumber` to settings for SMS.
6. Add a Render Cron Job using the same repository, same build/install command, same environment variables, and run command:
   `python -m backend.jobs.send_expiry_notifications`
   Schedule it once daily. Ensure it uses the repository root as its working directory.

## Important verification
- A provider API accepting a message is not the same as delivery to an inbox/handset. Test with a real opted-in recipient and inspect provider delivery status.
- Gmail may require an App Password and may apply sending limits. Twilio may require a paid account, verified recipient, country permissions, and sufficient balance. SMS delivery cannot be guaranteed "at any cost" by code alone.
- Live Firestore is mandatory for the scheduled job. It intentionally refuses to run against the in-memory fallback.
- The OCR endpoint extracts candidates only. User confirmation is required; an image may be blurry, cropped, rotated, or show manufacturing dates rather than expiry dates.
- Camera access requires HTTPS (the current Render URL uses HTTPS) and browser permission. If camera permission fails, use the file upload fallback.
