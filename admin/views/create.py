"""Create bots: make a new bot, then edit the bots you made."""

import streamlit as st

from common import bot_form, current_user, db, edit_bot, list_bots, make_slug, show_links, slug_taken

user = current_user()
st.title("Create a bot")

new_tab, mine_tab = st.tabs(["New bot", "My bots"])

with new_tab:
    st.write(
        "Fill in the form with the custom GPT's details. The bot goes live as soon as you create it, "
        "then you can add documents and copy the Moodle embed code."
    )
    values = bot_form(None, key="new-bot")
    if values:
        short_name = values.pop("short_name")
        slug = make_slug(values["course_code"], short_name)
        while slug_taken(slug):
            slug = make_slug(values["course_code"], short_name)
        db().table("bots").insert(
            {**values, "slug": slug, "created_by": user["email"], "updated_by": user["email"]}
        ).execute()
        st.session_state.just_created = (slug, values["title"])

    if "just_created" in st.session_state:
        slug, title = st.session_state.just_created
        st.success(f"Created **{title}** at `{slug}`. Add documents to it under **My bots**.")
        show_links(slug, title)

with mine_tab:
    bots = list_bots(created_by=user["email"])
    if not bots:
        st.info("You haven't made any bots yet.")
    else:
        labels = {bot["slug"]: f"{bot['title']} ({bot['slug']}){'' if bot['is_active'] else ' · turned off'}" for bot in bots}
        slug = st.selectbox("Choose a bot to edit", list(labels), format_func=labels.get, key="mine-select")
        edit_bot(slug, key="mine")
