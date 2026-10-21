-- Tables for the course chatbots, used by the admin app (admin/) and the chat endpoint (api/chat.js).
--
-- Run this once in Supabase: Project -> SQL Editor -> New query -> paste -> Run.
-- It is safe to run again; it only creates what is missing.
--
-- Row Level Security is on and there are no policies, so the public (anon) key can read nothing.
-- Only the secret (service role) key can, and that key lives only in Vercel and Streamlit secrets.

-- Who may sign in to the admin app. Designers can create bots and edit their own;
-- admins can manage every bot and every staff member.
create table if not exists public.staff (
  email      text primary key check (email = lower(email)),
  role       text not null check (role in ('designer', 'admin')),
  created_at timestamptz not null default now()
);

create table if not exists public.bots (
  slug             text primary key check (slug ~ '^[a-z0-9][a-z0-9-]{0,99}$'),
  course_code      text not null default '',
  title            text not null,
  bot_name         text not null default 'Assistant',
  description      text not null default '',
  notice           text not null default '',
  welcome_message  text not null default '',
  instructions     text not null check (length(btrim(instructions)) > 0),
  reasoning_effort text check (reasoning_effort in ('minimal', 'low', 'medium', 'high')),
  max_turns        integer check (max_turns > 0),
  model            text,
  is_active        boolean not null default true,
  created_by       text,
  updated_by       text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

-- The bot's "Knowledge" files, stored as plain text.
create table if not exists public.bot_documents (
  id         bigint generated always as identity primary key,
  bot_slug   text not null references public.bots (slug) on delete cascade,
  name       text not null,
  content    text not null,
  created_at timestamptz not null default now(),
  unique (bot_slug, name)
);

create or replace function public.touch_updated_at() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists bots_touch_updated_at on public.bots;
create trigger bots_touch_updated_at before update on public.bots
  for each row execute function public.touch_updated_at();

alter table public.staff         enable row level security;
alter table public.bots          enable row level security;
alter table public.bot_documents enable row level security;

revoke all on public.staff, public.bots, public.bot_documents from anon, authenticated;

-- The first admin. Change the email to yours, then create the same user under
-- Authentication -> Users -> Add user in the Supabase dashboard.
-- insert into public.staff (email, role) values ('someone@tiffin.edu', 'admin');
