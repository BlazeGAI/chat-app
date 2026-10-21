# Admin app

A Streamlit website where learning designers and admins make and manage chatbots without touching GitHub. Bots made here are stored in Supabase, and the chat site reads them from there. The older bots in the `bots/` folder keep working.

It has two sections:

| Section | Who sees it | What it does |
|---|---|---|
| **Create bots** | Everyone on the staff list | **New bot:** fill in the form (the same boxes as a custom GPT) and the bot is live. **My bots:** edit your own bots, add documents, copy the test link and Moodle embed code. |
| **Admin** | Admins only | **All bots:** search every bot, turn bots off and on, delete them, edit any bot, and import the older folder bots. **Staff:** add people, make them designers or admins, and remove them. |

Documents can be uploaded as `.txt`, `.md`, `.pdf` or `.docx`. The app keeps only the text. Scanned PDFs have no text, so they need converting first.

Changes are live for students within about a minute. Students who are mid-conversation should click **Start over** to get the new version.

---

## One-time setup

### 1. Supabase

1. In your Supabase project, open **SQL Editor → New query**, paste in [`supabase/schema.sql`](../supabase/schema.sql) and click **Run**.
2. Add yourself as the first admin. In the SQL Editor, run (with your email, in lowercase):
   ```sql
   insert into public.staff (email, role) values ('you@tiffin.edu', 'admin');
   ```
3. Create your sign-in: **Authentication → Users → Add user → Create new user**, with the same email, a password, and **Auto Confirm User** ticked.
4. From **Project Settings → API Keys**, note the project URL, the public key (**anon** or **publishable**) and the secret key (**service_role** or **secret**).

After this, admins add everyone else from the **Staff** page in the app. It creates their sign-in and shows a temporary password to pass on.

### 2. The chat site (Vercel)

In Vercel, **Project → Settings → Environment Variables**, add:

| Name | Value |
|---|---|
| `SUPABASE_URL` | The project URL, e.g. `https://abcd1234.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | The **secret** key |

Then **Deployments → ⋯ → Redeploy**. Without these two variables the site works as before, using only the `bots/` folder.

### 3. The admin app (Streamlit Community Cloud)

1. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub and click **Create app**.
2. Choose this repository, the `main` branch, and set **Main file path** to `admin/app.py`.
3. Under **Advanced settings → Secrets**, paste the contents of [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) and fill in the values.
4. Click **Deploy**. Bookmark the address it gives you; that's the admin site.

### Keeping the admin site out of view

The app can be **public** on Streamlit and still be protected. Visitors pass two locks before they see anything:

1. **Access code.** The `ACCESS_CODE` secret is a shared code you give only to staff. It's asked for once per visit, before the sign-in page. To change it, edit it in **App settings → Secrets**; everyone then needs the new code.
2. **Staff sign-in.** Each person's own Supabase email and password, and their email must be on the **Staff** list.

Streamlit lists every public app in search engines, so the app's title is a neutral "Staff Tools" and a search result shows nothing about chatbots. Also:

- In **App settings → General**, you can give the app a neutral address, such as `tu-staff-tools.streamlit.app`.
- Anyone with write access to this GitHub repository can see the app's secrets. Keep that list short (**GitHub → Settings → Collaborators**).
- In Supabase, **Authentication → Sign In / Providers**: turn off **Allow new users to sign up**, and set a minimum password length of 12 or more. Admins can still add people from the **Staff** page.

Streamlit Community Cloud is free. Any host that runs Python works too (for example Render or an internal server): install `admin/requirements.txt` and run `streamlit run admin/app.py` with the same secrets.

**The secret key can read and change every bot. Keep it only in Vercel's environment variables and Streamlit's secrets, never in a file in this repository.**

---

## Moving the older folder bots

In **Admin → All bots**, scroll to **Bots stored as folders** and click **Import**. The bot keeps its address, so Moodle links keep working, and from then on the Supabase copy is the one students get. You can then delete the folder on GitHub, or leave it as a backup.

## Run it on your own computer

```bash
cd admin
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then fill it in
streamlit run app.py
```

## How it works (for whoever comes next)

- `app.py` asks for the access code, signs people in with Supabase Auth, checks the `staff` table for their role, and shows the pages that role may see.
- `views/create.py` is the **Create bots** section; `views/manage_bots.py` and `views/staff.py` are the **Admin** section.
- `common.py` holds the Supabase calls, the bot form and the document uploader, shared by both sections.
- All reads and writes use the secret key on the Streamlit server. Row Level Security is on with no policies, so the public key can't read the tables at all; it is used only to sign in.
- `api/chat.js` looks a bot up in Supabase first, then in `bots/`. A bot turned off in Supabase stays off even if a folder of the same name exists. If Supabase can't be reached, folder bots still work.
