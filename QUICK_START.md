# Quick Start - Fix YouTube Bot Detection

## ⚠️ Problem
YouTube is blocking video downloads with "Sign in to confirm you're not a bot" error.

## ✅ Solution (3 Easy Steps)

### 1. Install Browser Extension

Install "Get cookies.txt LOCALLY":
- **Chrome**: https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
- **Firefox**: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/

### 2. Export Cookies

1. Login to YouTube in your browser (https://youtube.com)
2. Click the extension icon
3. Click "Export" → save as `cookies.txt`
4. Move to project directory:

```bash
mv ~/Downloads/cookies.txt /home/ivan/dev/voice_compare/cookies.txt
```

### 3. Restart Service

```bash
cd /home/ivan/dev/voice_compare
docker-compose restart voice-compare
```

## ✅ Done!

Your application will now use your YouTube authentication to bypass bot detection.

## Test It

Try your video comparison again - it should work now!

## Need More Help?

See detailed instructions in `COOKIES_SETUP.md`

---

**Security Note**: cookies.txt is already in .gitignore and won't be committed to git.
