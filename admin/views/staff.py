"""Admin: who can sign in, and whether they are a designer or an admin."""

import secrets

import streamlit as st

from common import current_user, db

user = current_user()
st.title("Staff")
st.write(
    "**Designers** can create bots and edit their own. **Admins** can also manage every bot and this staff list."
)

staff = db().table("staff").select("*").order("email").execute().data
for member in staff:
    col1, col2, col3 = st.columns([3, 2, 1])
    col1.markdown(f"**{member['email']}**")
    if member["email"] == user["email"]:
        col2.markdown(f"{member['role']} (you)")
        continue
    role = col2.selectbox(
        "Role", ["designer", "admin"], index=["designer", "admin"].index(member["role"]),
        key=f"role-{member['email']}", label_visibility="collapsed",
    )
    if role != member["role"]:
        db().table("staff").update({"role": role}).eq("email", member["email"]).execute()
        st.rerun()
    if col3.button("Remove", key=f"remove-{member['email']}", help="They can no longer sign in to this app. Their bots stay."):
        db().table("staff").delete().eq("email", member["email"]).execute()
        st.rerun()

st.divider()
st.subheader("Add someone")
with st.form("add-staff", clear_on_submit=True):
    email = st.text_input("University email")
    role = st.selectbox("Role", ["designer", "admin"])
    submitted = st.form_submit_button("Add", type="primary")

if submitted:
    email = email.strip().lower()
    if "@" not in email:
        st.error("Enter an email address.")
    elif any(m["email"] == email for m in staff):
        st.error("They're already on the list.")
    else:
        # Create their sign-in account. If one already exists, keep it and its password.
        password = secrets.token_urlsafe(9)
        try:
            db().auth.admin.create_user({"email": email, "password": password, "email_confirm": True})
            new_account = True
        except Exception:
            new_account = False
        db().table("staff").insert({"email": email, "role": role}).execute()
        if new_account:
            st.success(
                f"Added {email}. Send them this temporary password and ask them to change it after signing in "
                "(sidebar → Change password):"
            )
            st.code(password, language=None)
        else:
            st.success(f"Added {email}. They already had an account, so they sign in with their existing password.")
