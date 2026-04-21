# Service Deployment Info: Ghost Pipe

## Target Platform: Google Cloud Run
This service has been fully refactored and adapted to run securely and natively on Google Cloud Run.

### What Was Done:
1. **Refactored to HTTP Server (`engine.js`)**: 
   - Previously, the service ran as a background process using `chokidar` to monitor a local text file (`ghost_queue.txt`) for Mega links.
   - For Cloud Run compatibility, we removed the local-file watcher and added `express` to run an HTTP server. Cloud Run triggers workloads purely via HTTP.
   - The service now exposes a **POST `/drop`** endpoint over HTTP.
   - We added a `/` health-check endpoint so Cloud Run considers the container successfully spun up when it binds to its default `$PORT`.

2. **Added Doppler Integration (`Dockerfile`)**:
   - The Dockerfile was updated to install `curl`, `gnupg`, and the official Doppler CLI (`doppler`) at build time.
   - The container startup command (`CMD`) was updated to prepend `doppler run --`. When the container spins up on Cloud Run, Doppler automatically pulls and injects all secrets to the Node environment at runtime before executing `engine.js`.
   - Ensure the container runtime is assigned a Doppler Service Token environment variable (`DOPPLER_TOKEN`) on Cloud Run.

3. **Required Software (`Dockerfile`)**:
   - Installed `rclone` directly within the Alpine image since `engine.js` expects the `rclone` binary to be available to stream file uploads to Google Drive.

### How it Works Now:
To trigger Ghost Pipe to rip an incoming Mega link, whatever currently manages links (such as your Telegram Bot) should send an HTTP POST request to the Cloud Run URL URL:

```bash
curl -X POST https://<ghost-pipe-cloud-run-url>/drop \
     -H "Content-Type: application/json" \
     -d '{"link": "https://mega.nz/folder/..."}'
```

### Important deployment notes for Google Cloud Run:
- **Timeouts**: Mega link ripping via Real-Debrid and Rclone can take several minutes. You **must** increase the request timeout in Cloud Run from the default 5 minutes to a higher threshold (like 60 minutes) so the connection does not prematurely terminate before processing is done.
- **Doppler Injection**: Don't forget that Doppler requires the `DOPPLER_TOKEN` environment variable assigned to the Cloud Run service upon creation.
- **Rclone Configuration**: Rclone still needs to securely authenticate with your `gdrive:` remote. If this configuration is not completely provided via Doppler environment variables (e.g. `RCLONE_CONFIG_GDRIVE_...`), you will still need to mount your `rclone.conf` secret as a Volume in Cloud Run pointing to `/root/.config/rclone/rclone.conf`.
