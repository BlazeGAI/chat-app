"""Shared helpers for the admin app: Supabase access, sign-in, and the bot form.

The app uses two Supabase clients:
  - a per-visitor client with the public key, used only to sign in and change passwords;
  - one shared client with the secret key, used for all table reads and writes.
The secret key never reaches the browser; Streamlit runs this code on the server.
"""

import io
import re
import secrets
import string
from pathlib import Path

import streamlit as st
from supabase import Client, create_client

# Must match MAX_DOCUMENT_CHARS in api/chat.js.
MAX_DOCUMENT_CHARS = 400_000
REASONING_EFFORTS = ["minimal", "low", "medium", "high"]
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")
BOTS_FOLDER = Path(__file__).resolve().parent.parent / "bots"


# --- Supabase -----------------------------------------------------------------


@st.cache_resource
def db() -> Client:
    """The shared client with the secret key. Reads and writes every table."""
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_ROLE_KEY"])


def auth_client() -> Client:
    """This visitor's own client with the public key, kept for the length of their session."""
    if "auth_client" not in st.session_state:
        st.session_state.auth_client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
    return st.session_state.auth_client


def chat_site_url() -> str:
    return st.secrets.get("CHAT_SITE_URL", "https://YOUR-SITE.vercel.app").rstrip("/")


# --- Signing in ---------------------------------------------------------------


def current_user():
    """{"email", "role"} for the signed-in staff member, or None."""
    return st.session_state.get("user")


def sign_in(email: str, password: str) -> str | None:
    """Signs in and checks the staff list. Returns an error message, or None on success."""
    email = email.strip().lower()
    try:
        auth_client().auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        return "That email and password didn't match."
    row = db().table("staff").select("role").eq("email", email).maybe_single().execute()
    if not row or not row.data:
        auth_client().auth.sign_out()
        return "Your account isn't on the staff list yet. Ask an admin to add you."
    st.session_state.user = {"email": email, "role": row.data["role"]}
    return None


def sign_out():
    try:
        auth_client().auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("user", None)
    st.session_state.pop("auth_client", None)


def change_password(new_password: str) -> str | None:
    try:
        auth_client().auth.update_user({"password": new_password})
    except Exception as err:
        return f"The password couldn't be changed: {err}"
    return None


# --- Bots ---------------------------------------------------------------------


def make_slug(course_code: str, short_name: str) -> str:
    """course code + short name + four random characters, e.g. psy101-interview-q7k2.

    The random ending makes the bot's address hard to guess.
    """
    words = re.sub(r"[^a-z0-9]+", "-", f"{course_code} {short_name}".lower()).strip("-")
    words = words[:60].strip("-") or "bot"
    ending = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
    return f"{words}-{ending}"


def slug_taken(slug: str) -> bool:
    if (BOTS_FOLDER / slug).is_dir():
        return True
    return bool(db().table("bots").select("slug").eq("slug", slug).execute().data)


def list_bots(created_by: str | None = None) -> list[dict]:
    query = db().table("bots").select(
        "slug, course_code, title, bot_name, is_active, created_by, updated_by, created_at, updated_at"
    )
    if created_by:
        query = query.eq("created_by", created_by)
    return query.order("updated_at", desc=True).execute().data


def get_bot(slug: str) -> dict | None:
    rows = db().table("bots").select("*").eq("slug", slug).execute().data
    return rows[0] if rows else None


def list_documents(slug: str) -> list[dict]:
    return (
        db().table("bot_documents").select("id, name, content").eq("bot_slug", slug).order("name").execute().data
    )


def documents_size(slug: str) -> int:
    return sum(len(doc["content"]) for doc in list_documents(slug))


def can_edit(bot: dict) -> bool:
    user = current_user()
    return bool(user) and (user["role"] == "admin" or bot.get("created_by") == user["email"])


def extract_text(uploaded) -> str:
    """Text from an uploaded .txt, .md, .pdf or .docx file."""
    name = uploaded.name.lower()
    data = uploaded.getvalue()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        return "\n\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(data)).pages).strip()
    if name.endswith(".docx"):
        from docx import Document

        return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs).strip()
    return data.decode("utf-8", errors="replace").strip()


def embed_code(slug: str, title: str) -> str:
    safe_title = title.replace('"', "&quot;")
    return (
        "<iframe\n"
        f'  src="{chat_site_url()}/?bot={slug}"\n'
        f'  title="{safe_title}"\n'
        '  width="100%" height="650"\n'
        '  style="border: 1px solid #ccc; border-radius: 8px;"\n'
        '  allow="clipboard-write">\n'
        "</iframe>"
    )


def show_links(slug: str, title: str):
    st.markdown(f"**Test link:** [{chat_site_url()}/?bot={slug}]({chat_site_url()}/?bot={slug})")
    st.caption("Moodle embed code (paste into a Page, Label or Book in HTML view):")
    st.code(embed_code(slug, title), language="html")


# --- The bot form (used by both sections) ------------------------------------


def bot_form(bot: dict | None, key: str) -> dict | None:
    """Shows the settings form. Returns the values when submitted and valid, otherwise None.

    `bot` is None for a new bot, or the existing row to edit.
    """
    bot = bot or {}
    with st.form(key):
        col1, col2 = st.columns(2)
        course_code = col1.text_input(
            "Course code", value=bot.get("course_code", ""), placeholder="PSY101", help="Used in the bot's address and for sorting."
        )
        short_name = ""
        if not bot:
            short_name = col2.text_input(
                "Short name for the address *", placeholder="interview", help="One or two words. Students see it in the link."
            )
        title = st.text_input(
            "Title *", value=bot.get("title", ""), placeholder="PSY101: Interview Practice", help="Heading at the top of the chat window."
        )
        bot_name = st.text_input(
            "Bot name",
            value=bot.get("bot_name", "Assistant"),
            help="The label over the bot's messages. Use the persona's name for role-plays.",
        )
        description = st.text_area(
            "Description for students",
            value=bot.get("description", ""),
            height=80,
            help="Shown under the title, like a custom GPT's description.",
        )
        instructions = st.text_area(
            "Instructions *",
            value=bot.get("instructions", ""),
            height=320,
            help="Paste the text from the custom GPT's Instructions box.",
        )
        welcome_message = st.text_area(
            "Welcome message",
            value=bot.get("welcome_message", ""),
            height=120,
            help="The bot's first message. Leave empty if the student should speak first.",
        )
        notice = st.text_input(
            "Notice",
            value=bot.get("notice", "This is an AI tool for practice. Do not enter personal information."),
            help="Small print under the message box.",
        )

        with st.expander("Advanced options"):
            effort = bot.get("reasoning_effort") or "low"
            reasoning_effort = st.selectbox(
                "Reasoning effort",
                REASONING_EFFORTS,
                index=REASONING_EFFORTS.index(effort),
                help="Low is fast and suits role-plays. Try medium if the bot skips steps in its instructions.",
            )
            max_turns = st.number_input(
                "Most messages per conversation",
                min_value=1,
                max_value=200,
                value=int(bot.get("max_turns") or 40),
                help="Students must click Start over after this many messages.",
            )
            model = st.text_input(
                "Model (usually leave empty)",
                value=bot.get("model") or "",
                help="A different OpenAI model for this bot only.",
            )

        submitted = st.form_submit_button("Create bot" if not bot else "Save changes", type="primary")

    if not submitted:
        return None
    problems = []
    if not bot and not short_name.strip():
        problems.append("Add a short name for the address.")
    if not title.strip():
        problems.append("Add a title.")
    if not instructions.strip():
        problems.append("Add the instructions.")
    for problem in problems:
        st.error(problem)
    if problems:
        return None

    values = {
        "course_code": course_code.strip().upper(),
        "title": title.strip(),
        "bot_name": bot_name.strip() or "Assistant",
        "description": description.strip(),
        "notice": notice.strip(),
        "welcome_message": welcome_message.strip(),
        "instructions": instructions.strip(),
        "reasoning_effort": reasoning_effort,
        "max_turns": int(max_turns),
        "model": model.strip() or None,
    }
    if not bot:
        values["short_name"] = short_name.strip()
    return values


def documents_editor(slug: str, key: str):
    """Lists a bot's documents, with upload and remove."""
    docs = list_documents(slug)
    used = sum(len(doc["content"]) for doc in docs)
    st.caption(
        f"The bot reads every document before every answer. Using {used:,} of {MAX_DOCUMENT_CHARS:,} characters "
        f"(about {used // 2700} of 150 pages)."
    )
    for doc in docs:
        col1, col2 = st.columns([5, 1])
        col1.markdown(f"📄 **{doc['name']}** · {len(doc['content']):,} characters")
        if col2.button("Remove", key=f"{key}-remove-{doc['id']}"):
            db().table("bot_documents").delete().eq("id", doc["id"]).execute()
            st.rerun()

    uploads = st.file_uploader(
        "Add documents (.txt, .md, .pdf, .docx)",
        type=["txt", "md", "pdf", "docx"],
        accept_multiple_files=True,
        key=f"{key}-upload",
    )
    if uploads and st.button("Upload", key=f"{key}-upload-button"):
        existing = {doc["name"] for doc in docs}
        for uploaded in uploads:
            try:
                text = extract_text(uploaded)
            except Exception as err:
                st.error(f"{uploaded.name} couldn't be read: {err}")
                continue
            if not text:
                st.error(f"{uploaded.name} has no text the bot can read. Scanned PDFs need to be converted to text first.")
                continue
            if used + len(text) > MAX_DOCUMENT_CHARS:
                st.error(f"{uploaded.name} would take this bot over the {MAX_DOCUMENT_CHARS:,}-character limit.")
                continue
            if uploaded.name in existing:
                db().table("bot_documents").update({"content": text}).eq("bot_slug", slug).eq("name", uploaded.name).execute()
            else:
                db().table("bot_documents").insert({"bot_slug": slug, "name": uploaded.name, "content": text}).execute()
            used += len(text)
            st.success(f"Added {uploaded.name} ({len(text):,} characters).")
        st.rerun()


def edit_bot(slug: str, key: str):
    """The full editor for one existing bot: settings, documents and links."""
    bot = get_bot(slug)
    if not bot:
        st.warning("That bot no longer exists.")
        return
    if not can_edit(bot):
        st.warning("Only the bot's creator or an admin can edit it.")
        return

    status = "🟢 Live" if bot["is_active"] else "⏸️ Turned off"
    st.markdown(f"**{bot['title']}** · `{slug}` · {status}")
    settings_tab, docs_tab, links_tab = st.tabs(["Settings", "Documents", "Links and embed code"])
    with settings_tab:
        values = bot_form(bot, key=f"{key}-form-{slug}")
        if values:
            values["updated_by"] = current_user()["email"]
            db().table("bots").update(values).eq("slug", slug).execute()
            st.success("Saved. Students who are mid-conversation should click Start over to get the new version.")
    with docs_tab:
        documents_editor(slug, key=f"{key}-docs-{slug}")
    with links_tab:
        show_links(slug, bot["title"])
