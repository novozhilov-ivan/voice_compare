# YouTube Cookies Setup Guide

YouTube requires authentication to prevent bot detection. Follow these steps to export your YouTube cookies.

## Quick Setup (Recommended)

### Option 1: Using Browser Extension (Easiest)

1. **Install "Get cookies.txt LOCALLY" extension:**
   - **Chrome/Edge**: https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
   - **Firefox**: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/

2. **Login to YouTube:**
   - Go to https://www.youtube.com
   - Sign in to your Google account

3. **Export cookies:**
   - Click the extension icon
   - Click "Export" on the youtube.com page
   - Save the file as `cookies.txt`

4. **Place cookies file:**
   ```bash
   # Move the downloaded cookies.txt to your project directory
   mv ~/Downloads/cookies.txt /home/ivan/dev/voice_compare/cookies.txt
   ```

### Option 2: Using yt-dlp Command Line

```bash
# This will attempt to extract cookies from your browser
yt-dlp --cookies-from-browser chrome --cookies cookies.txt \
  --skip-download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Replace `chrome` with your browser: `firefox`, `edge`, `safari`, `brave`, `chromium`, `opera`, `vivaldi`

## Verify Cookies Work

Test if cookies are working:

```bash
# From your project directory
docker-compose exec voice-compare yt-dlp \
  --cookies /app/cookies.txt \
  --skip-download \
  "https://www.youtube.com/watch?v=WeSyE1Zyjts"
```

If successful, you'll see video information without errors.

## Update Docker Configuration

The `docker-compose.yml` already mounts cookies if the file exists:

```yaml
volumes:
  - ./cookies.txt:/app/cookies.txt:ro  # Read-only cookies
```

## Restart Service

After placing cookies.txt:

```bash
docker-compose restart voice-compare
```

## Troubleshooting

### "Sign in to confirm you're not a bot" Error

- **Cause**: No cookies or expired cookies
- **Solution**: Re-export cookies from your browser after logging into YouTube

### "cookiefile not found" Warning

- **Cause**: cookies.txt file is not in the correct location
- **Solution**: Make sure `cookies.txt` is in `/home/ivan/dev/voice_compare/cookies.txt`

### Cookies Expire

- **Frequency**: YouTube cookies expire periodically (usually 30-90 days)
- **Solution**: Re-export cookies when you see authentication errors

### Permission Denied

```bash
# Make sure cookies file is readable
chmod 644 /home/ivan/dev/voice_compare/cookies.txt
```

## Security Notes

⚠️ **IMPORTANT**:
- **Never commit cookies.txt to git** (already in .gitignore)
- Cookies contain your authentication tokens
- Keep cookies.txt private and secure
- Regenerate if exposed

## Cookie File Format

The cookies.txt file should be in Netscape format:

```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1234567890	CONSENT	YES+
.youtube.com	TRUE	/	FALSE	1234567890	VISITOR_INFO1_LIVE	xxxxx
```

## Alternative: Use API Key (Future)

For production use, consider:
- YouTube Data API v3
- OAuth2 authentication
- Service account credentials

But for personal use, cookies are the simplest solution.
