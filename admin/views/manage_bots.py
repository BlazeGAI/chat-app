"""Admin: every bot, turning bots on and off, deleting, and importing the older folder bots."""

import streamlit as st

from common import BOTS_FOLDER, current_user, db, edit_bot, list_bots

user = current_user()
st.title("All bots")

bots = list_bots()
search = st.text_input("Search by title, course, address or creator", placeholder="PSY101")
if search:
    needle = search.lower()
    bots = [b for b in bots if any(needle in str(b[field] or "").lower() for field in ("title", "course_code", "slug", "created_by"))]

live = sum(1 for b in bots if b["is_active"])
st.caption(f"{len(bots)} bots · {live} live · {len(bots) - live} turned off")
st.dataframe(
    [
        {
            "Live": b["is_active"],
            "Course": b["course_code"],
            "Title": b["title"],
            "Address": b["slug"],
            "Created by": b["created_by"],
            "Last edited": (b["updated_at"] or "")[:16].replace("T", " "),
            "Edited by": b["updated_by"],
        }
        for b in bots
    ],
    hide_index=True,
    width="stretch",
    column_config={"Live": st.column_config.CheckboxColumn()},
)

if bots:
    st.divider()
    labels = {b["slug"]: f"{b['title']} ({b['slug']})" for b in bots}
    slug = st.selectbox("Choose a bot to manage", list(labels), format_func=labels.get, key="admin-select")
    bot = next(b for b in bots if b["slug"] == slug)

    col1, col2, _ = st.columns([1, 1, 3])
    if bot["is_active"]:
        if col1.button("⏸️ Turn off", help="Students see 'This chatbot could not be found' until it is turned back on."):
            db().table("bots").update({"is_active": False, "updated_by": user["email"]}).eq("slug", slug).execute()
            st.rerun()
    elif col1.button("▶️ Turn on", type="primary"):
        db().table("bots").update({"is_active": True, "updated_by": user["email"]}).eq("slug", slug).execute()
        st.rerun()

    with col2.popover("🗑️ Delete"):
        st.write("This deletes the bot and its documents for good. Its Moodle link will stop working.")
        confirm = st.text_input("Type the bot's address to confirm", placeholder=slug, key=f"confirm-{slug}")
        if st.button("Delete for good", type="primary", disabled=confirm != slug):
            db().table("bots").delete().eq("slug", slug).execute()
            st.session_state.pop("admin-select", None)
            st.rerun()

    edit_bot(slug, key="admin")

# The bots made before this app live as folders in the repository's bots/ folder.
# Importing copies one into Supabase; from then on the Supabase copy is the one students get.
st.divider()
st.subheader("Bots stored as folders")
imported = {b["slug"] for b in list_bots()}
folders = sorted(
    p for p in BOTS_FOLDER.iterdir() if p.is_dir() and not p.name.startswith("_") and p.name not in imported
) if BOTS_FOLDER.is_dir() else []
if not folders:
    st.caption("None left to import.")
else:
    st.write(
        "These bots were made as folders on GitHub. Import one to manage it here. "
        "Its address stays the same, so Moodle links keep working."
    )
    for folder in folders:
        col1, col2 = st.columns([5, 1])
        col1.markdown(f"📁 `{folder.name}`")
        if col2.button("Import", key=f"import-{folder.name}"):
            def read(name):
                path = folder / name
                return path.read_text(encoding="utf-8").strip() if path.is_file() else ""

            settings = {}
            for line in read("settings.txt").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and ":" in line:
                    k, v = line.split(":", 1)
                    if v.strip():
                        settings[k.strip().lower()] = v.strip()
            max_turns = settings.get("max_turns", "")
            db().table("bots").insert(
                {
                    "slug": folder.name,
                    "course_code": folder.name.split("-")[0].upper(),
                    "title": settings.get("title", folder.name),
                    "bot_name": settings.get("bot_name", "Assistant"),
                    "description": settings.get("description", ""),
                    "notice": settings.get("notice", ""),
                    "welcome_message": read("welcome.md"),
                    "instructions": read("instructions.md"),
                    "reasoning_effort": settings.get("reasoning_effort"),
                    "max_turns": int(max_turns) if max_turns.isdigit() else None,
                    "model": settings.get("model"),
                    "created_by": user["email"],
                    "updated_by": user["email"],
                }
            ).execute()
            docs_folder = folder / "documents"
            if docs_folder.is_dir():
                for doc in sorted(docs_folder.iterdir()):
                    if doc.suffix.lower() in (".md", ".txt") and not doc.name.startswith("_"):
                        text = doc.read_text(encoding="utf-8").strip()
                        if text:
                            db().table("bot_documents").insert(
                                {"bot_slug": folder.name, "name": doc.name, "content": text}
                            ).execute()
            st.rerun()
