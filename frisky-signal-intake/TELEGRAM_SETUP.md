# Telegram Bot Setup Guide

This guide will help you set up Telegram webhook notifications for the Frisky Developments Signal Intake System.

## Prerequisites

- A Telegram account
- Access to the Operator Console

## Step 1: Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Start a chat and send the command: `/newbot`
3. Follow the prompts to choose a name and username for your bot
4. BotFather will provide you with a **Bot Token** - save this securely
   - Format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

## Step 2: Set Up Your Channel or Group

### For a Channel:
1. Create a new channel in Telegram (or use an existing one)
2. Add your bot as an administrator:
   - Go to channel settings → Administrators → Add Administrator
   - Search for your bot by username
   - Grant posting permissions

### For a Group:
1. Create a new group in Telegram (or use an existing one)
2. Add your bot to the group as a member

## Step 3: Get Your Chat ID

1. Send a test message in your channel or group
2. Open your browser and visit:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
   Replace `<YOUR_BOT_TOKEN>` with your actual bot token

3. Look for the `chat` object in the JSON response:
   ```json
   {
     "chat": {
       "id": -1001234567890,
       "title": "Your Channel Name"
     }
   }
   ```

4. Copy the `id` value (it usually starts with `-100` for channels and supergroups)

## Step 4: Configure in the Operator Console

1. Navigate to the Operator Console: `/console`
2. Click the **Settings** button (⚙️ icon)
3. Scroll to the **Telegram Bot Configuration** section
4. Enter your **Bot Token**
5. Enter your **Chat ID**
6. Click **Save Settings**

## Step 5: Test the Integration

1. Submit a test signal through the public intake form
2. Check your Telegram channel/group for the notification
3. The message should include:
   - Ticket ID
   - Request type
   - Submitter name and contact
   - Project (if provided)
   - Message snippet
   - Timestamp

## Troubleshooting

### No messages appearing in Telegram?

1. **Check bot permissions**: Ensure the bot has posting permissions in channels
2. **Verify Chat ID**: Make sure the Chat ID is correct and includes the negative sign
3. **Check bot token**: Ensure the token is copied completely without extra spaces
4. **Test the bot**: Send a message directly to your bot on Telegram - if it doesn't work, recreate the bot

### Getting "Unauthorized" errors?

- The bot token may be invalid
- Try creating a new bot and using the new token

### Messages not formatting correctly?

- The system uses Telegram's Markdown format
- Special characters in signal content are automatically escaped

## Message Format

New signal notifications appear in this format:

```
🚨 New Signal Received

Ticket ID: FRK-1234-X
Type: Technical Support
From: John Doe
Contact: @johndoe
Project: Example Project

Message:
This is the signal message content...

Frisky Signal Intake System
```

## Security Notes

- Keep your bot token private - treat it like a password
- Never commit bot tokens to version control
- Bot tokens are stored securely in Spark KV storage
- Only operators with console access can configure webhooks

## Additional Resources

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [BotFather Commands](https://core.telegram.org/bots#6-botfather)
- [Getting Updates](https://core.telegram.org/bots/api#getupdates)
