"""Admin app for the course chatbots.

    streamlit run admin/app.py

Two sections:
  - Create bots: any staff member (designer or admin) makes bots and edits their own.
  - Admin: admins manage every bot, turn bots on and off, and manage staff.

The app is public on Streamlit Community Cloud, so its title is deliberately generic, and
visitors must enter the shared ACCESS_CODE (from Streamlit Secrets) before they see the sign-in.
"""

import hmac
import time

import streamlit as st

from common import change_password, current_user, sign_in, sign_out

st.set_page_config(page_title="Staff Tools", page_icon="🔒", layout="wide")


def access_code_page():
    st.title("Staff Tools")
    with st.form("access-code"):
        code = st.text_input("Access code", type="password")
        if st.form_submit_button("Continue", type="primary"):
            if hmac.compare_digest(code.strip().encode(), str(st.secrets["ACCESS_CODE"]).strip().encode()):
                st.session_state.access_ok = True
                st.rerun()
            else:
                time.sleep(2)  # slows down guessing
                st.error("That code isn't right.")


def login_page():
    st.title("Staff Tools")
    st.write("Sign in with your staff account.")
    with st.form("sign-in"):
        email = st.text_input("Email", autocomplete="email")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        if st.form_submit_button("Sign in", type="primary"):
            error = sign_in(email, password)
            if error:
                st.error(error)
            else:
                st.rerun()


# Without an ACCESS_CODE secret (for example when testing on your own computer) this step is skipped.
if st.secrets.get("ACCESS_CODE") and not st.session_state.get("access_ok"):
    st.navigation([st.Page(access_code_page, title="Staff Tools", icon="🔒")]).run()
    st.stop()

user = current_user()
if not user:
    st.navigation([st.Page(login_page, title="Sign in", icon="🔑")]).run()
    st.stop()

pages = {"Create bots": [st.Page("views/create.py", title="Create a bot", icon="✨", default=True)]}
if user["role"] == "admin":
    pages["Admin"] = [
        st.Page("views/manage_bots.py", title="All bots", icon="🗂️"),
        st.Page("views/staff.py", title="Staff", icon="👥"),
    ]

with st.sidebar:
    st.caption(f"Signed in as **{user['email']}** ({user['role']})")
    with st.popover("Change password"):
        with st.form("change-password", clear_on_submit=True):
            new_password = st.text_input("New password", type="password", autocomplete="new-password")
            if st.form_submit_button("Change"):
                if len(new_password) < 8:
                    st.error("Use at least 8 characters.")
                else:
                    error = change_password(new_password)
                    if error:
                        st.error(error)
                    else:
                        st.success("Password changed.")
    if st.button("Sign out"):
        sign_out()
        st.rerun()

st.navigation(pages).run()
