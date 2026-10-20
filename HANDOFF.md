# Course Chatbots: Guide for Instructional Designers

This tool replaces custom GPTs with chatbots that students use inside Moodle. Students don't need an extra login, because the bot sits on a Moodle page they can already see. Nothing a student types is saved. The conversation is gone when they close the page.

Each chatbot is a **folder of plain text files**. You never need to edit code to make, change or remove a bot.

---

## 1. Make a new chatbot

You can do all of this in the GitHub website. You don't need any software on your computer.

1. Open the repository on GitHub and go into the `bots` folder.
2. Open `_template` and look at its four files. A new bot needs the same files.
3. Create the new bot's folder by adding its first file:
   - Click **Add file → Create new file**.
   - In the name box, type the folder name, a slash, then the file name, like this: `bots/psy101-interview-q7k2/instructions.md`. Typing the slash creates the folder.
4. **Name the folder:** course code, a short name, then four random letters and numbers, all lowercase with dashes. For example, `psy101-interview-q7k2`. The folder name becomes part of the bot's web address. The random ending makes the address hard to guess, so only people with the link (your Moodle students) can find the bot.
5. Paste the GPT's instructions into `instructions.md` and click **Commit changes**.
6. Add `welcome.md` and `settings.txt` the same way, copying from `_template` and changing the text. (See the table below.)
7. The bot is live about one minute after you commit. Test it at
   `https://YOUR-SITE.vercel.app/?bot=psy101-interview-q7k2`

### The files in a bot folder

| File | Required? | What it is | In a custom GPT, this was… |
|---|---|---|---|
| `instructions.md` | **Yes** | The bot's instructions. Paste them as they are. | The **Instructions** box |
| `welcome.md` | No | The bot's first message, shown as soon as the page opens. Leave it out if the student should speak first. | The greeting or conversation starter |
| `settings.txt` | No | Title, labels and a few options (see below) | The **Name** and **Description** boxes |
| `documents/` | No | Reference files the bot reads before every answer | **Knowledge** files |

### settings.txt options

Each line is `name: value`. Lines starting with `#` are notes and are ignored. Leave out any line you don't need.

| Setting | Example | What it does |
|---|---|---|
| `title` | `title: CEP505 Activity 2.1: Pre-Exercise Screening` | Heading at the top of the chat window |
| `bot_name` | `bot_name: Alex Morgan (client)` | Label over the bot's messages. Use the persona's name. |
| `description` | `description: Ask the client anything…` | Instructions for students, shown under the title |
| `notice` | `notice: This is an AI simulation…` | Small print under the message box |
| `reasoning_effort` | `reasoning_effort: low` | How long the bot thinks before answering: `minimal`, `low`, `medium` or `high`. `low` is fast and suits role-plays. If a bot skips steps in its instructions, try `medium`. |
| `max_turns` | `max_turns: 40` | The most messages a student can send before they must click **Start over**. The default is 40. |
| `model` | `model: gpt-5-mini` | A different OpenAI model for this bot only. Usually leave this out. |

### Adding documents (the "Knowledge" files)

- Put them in the bot's `documents` folder as **.txt or .md** files. PDF and Word files are not read.
- To convert a Word file: in Word, **File → Save As → Plain Text (.txt)**. For a PDF, copy the text into Word first.
- The bot reads **every** document before **every** answer. That's what makes its answers reliable, but it also means large documents cost more per message. Keep only what the bot needs. The limit is about 400,000 characters per bot (around 150 pages). If you go over, the bot shows "not set up correctly."
- Files whose names start with `_` are ignored.

### Changing or removing a bot

- **Change:** edit its files on GitHub and commit. The change is live in about a minute. Students who are mid-conversation should click **Start over** to get the new version.
- **Remove:** delete the folder. Its link will then show "This chatbot could not be found."

---

## 2. Put a bot in Moodle

Add this to a Moodle Page, Label or Book. In the text editor, switch to the HTML or code view, then paste it and change the two marked parts:

```html
<iframe
  src="https://YOUR-SITE.vercel.app/?bot=FOLDER-NAME"
  title="CHATBOT NAME"
  width="100%" height="650"
  style="border: 1px solid #ccc; border-radius: 8px;"
  allow="clipboard-write">
</iframe>
```

- `title` is read aloud by screen readers. Use the bot's name, for example `title="Jordan Ellis role-play chatbot"`.
- `allow="clipboard-write"` lets the **Copy conversation** button work. That's useful when students paste a transcript into an assignment.
- If Moodle removes the iframe when you save, your account needs the "trust content" permission. Ask a Moodle administrator.

---

## 3. What students see

- The title, the description, and the bot's welcome message.
- A message box. **Enter** sends, and **Shift+Enter** starts a new line.
- **Start over** clears the conversation.
- **Copy conversation** copies the full transcript.
- The chat works with a keyboard and screen readers, follows the device's light or dark setting, and fits on a phone.
- Refreshing or leaving the page clears the conversation. Tell students this if an activity asks them to submit a transcript.

---

## 4. When something goes wrong

| What students see | Likely cause | What to do |
|---|---|---|
| "This chatbot could not be found" | The folder name in the link doesn't match the folder in `bots`, or it starts with `_` | Check the spelling. Folder names must be lowercase letters, numbers and dashes. |
| "This chatbot is not set up correctly" | `instructions.md` is missing or empty, or the documents are too large | Check the files. Vercel's logs give the exact reason (see below). |
| "The chatbot service is not set up yet" | The OpenAI key is missing in Vercel | See section 6. |
| "The chatbot is busy right now" | OpenAI is rate-limiting, **or the OpenAI account is out of credit or has hit its budget** | Check billing and limits in the OpenAI dashboard. |
| "The chatbot had a problem answering" (every bot) | Most often the model has been retired or renamed | See section 5. |
| The bot ignores part of its instructions | The instructions, not the tool | Edit `instructions.md`, or try `reasoning_effort: medium`. |

**Reading the logs:** in Vercel, open the project, then **Logs**. Each error is written there in plain language, including OpenAI's own explanation.

---

## 5. The one routine maintenance task: model retirement

The code uses no add-on libraries, so there are no updates to install. What **will** happen every year or two is that OpenAI retires a model and sends an email naming the replacement. When that happens:

1. In Vercel: **Project → Settings → Environment Variables**.
2. Set `OPENAI_MODEL` to the new model name (for example `gpt-5-mini` or its replacement).
3. Go to **Deployments**, open the menu on the latest one and choose **Redeploy**.
4. Open one bot and send a test message.

If a bot's `settings.txt` has its own `model:` line, update that line too.

---

## 6. Costs, accounts and limits

- **OpenAI** bills per message. Cost depends on the length of the instructions, the documents and the conversation. Repeated instructions are cached automatically and cost less.
  - Use a separate **OpenAI project** and API key for this tool, so its spending is easy to see.
  - Set a **monthly budget** on that project in the OpenAI dashboard. If it's reached, bots show "busy" rather than running up a bill.
- **Vercel** hosts the site. ⚠️ Vercel's free **Hobby** plan is limited to personal, non-commercial use. Using it for university courses probably requires the **Pro** plan. Check with Vercel or the university before using it with students.
- **Message limits:** students can send up to 4,000 characters per message and 40 messages per conversation (changeable per bot with `max_turns`).

---

## 7. Privacy

- Nothing is stored by this tool: no accounts, no transcripts, no logs of what students type.
- Messages are sent to OpenAI to generate replies. The tool asks OpenAI not to store them (`store: false`). OpenAI may still keep API data for a limited time for abuse monitoring under its API data terms. Confirm that this fits university policy.
- Tell students not to enter real personal, patient or case information. The `notice` setting is a good place for this.

---

## 8. One-time setup (whoever deploys it)

1. In **OpenAI**: create a project for course chatbots, create an API key in it, and set a monthly budget.
2. In **Vercel**: **Add New → Project**, then import this GitHub repository. Keep the default settings.
3. Before deploying, add the environment variable `OPENAI_API_KEY` with the key from step 1. Optionally add `OPENAI_MODEL`.
4. Deploy. The site address appears on the project page, for example `https://course-chatbots.vercel.app`. Replace `YOUR-SITE` in this guide with it.
5. **Optional, recommended:** allow the bots to be embedded only in your Moodle. In `vercel.json`, add this to the existing `headers` list, using your Moodle address:
   ```json
   { "key": "Content-Security-Policy", "value": "frame-ancestors 'self' https://moodle.example.edu" }
   ```

**Never paste the API key into a bot file, a Moodle page or anywhere in this repository.** It belongs only in Vercel's environment variables.

---

## How it works (for whoever comes next)

- `public/` holds the chat window: one HTML page, one script, one stylesheet.
- `api/chat.js` is the only server code. It reads the bot's folder, adds the documents to the instructions, sends the conversation to OpenAI and streams the reply back. It holds the API key, so students never see it.
- `bots/` holds one folder per chatbot.
- There are no packages to install or update. To test on your own computer: `OPENAI_API_KEY=sk-... node scripts/local-preview.js`, then open `http://localhost:3000/?bot=FOLDER-NAME`.
