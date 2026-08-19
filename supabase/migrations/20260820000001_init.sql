-- HAYL AI Voice-to-Song schema

create extension if not exists "pgcrypto";

create type public.song_status as enum (
  'pending',
  'processing',
  'completed',
  'failed'
);

create table public.users (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  credits_remaining integer not null default 2 check (credits_remaining >= 0),
  created_at timestamptz not null default now()
);

create table public.instrumentals (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null,
  genre text not null,
  bpm integer,
  key text,
  storage_path text not null,
  preview_path text,
  is_active boolean not null default true
);

create table public.songs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  original_audio_url text,
  original_path text,
  processed_audio_url text,
  processed_path text,
  genre text,
  instrumental_id uuid references public.instrumentals (id),
  duration_seconds numeric,
  credits_charged integer not null default 0,
  status public.song_status not null default 'pending',
  pipeline_step text,
  error_message text,
  runpod_job_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.payments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users (id) on delete cascade,
  iyzico_token text,
  conversation_id text unique,
  status text not null default 'pending',
  credits integer not null,
  amount_try numeric(10, 2) not null,
  raw_payload jsonb,
  created_at timestamptz not null default now()
);

create index songs_user_id_idx on public.songs (user_id, created_at desc);
create index payments_user_id_idx on public.payments (user_id);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger songs_set_updated_at
before update on public.songs
for each row
execute function public.set_updated_at();

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id, email, credits_remaining)
  values (new.id, new.email, 2)
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_user();

create or replace function public.credits_for_duration(duration_seconds numeric)
returns integer
language sql
immutable
as $$
  select case
    when duration_seconds is null or duration_seconds <= 30 then 1
    when duration_seconds <= 60 then 2
    when duration_seconds <= 90 then 3
    else 4
  end;
$$;

create or replace function public.consume_credits(p_user_id uuid, p_amount integer)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  remaining integer;
begin
  if p_amount is null or p_amount < 1 then
    raise exception 'invalid credit amount';
  end if;

  update public.users
  set credits_remaining = credits_remaining - p_amount
  where id = p_user_id
    and credits_remaining >= p_amount
  returning credits_remaining into remaining;

  if remaining is null then
    raise exception 'INSUFFICIENT_CREDITS';
  end if;

  return remaining;
end;
$$;

create or replace function public.add_credits(p_user_id uuid, p_amount integer)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  remaining integer;
begin
  if p_amount is null or p_amount < 1 then
    raise exception 'invalid credit amount';
  end if;

  update public.users
  set credits_remaining = credits_remaining + p_amount
  where id = p_user_id
  returning credits_remaining into remaining;

  if remaining is null then
    raise exception 'user not found';
  end if;

  return remaining;
end;
$$;

alter table public.users enable row level security;
alter table public.songs enable row level security;
alter table public.instrumentals enable row level security;
alter table public.payments enable row level security;

create policy "users read own"
  on public.users for select
  using (auth.uid() = id);

create policy "users update own"
  on public.users for update
  using (auth.uid() = id);

create policy "songs select own"
  on public.songs for select
  using (auth.uid() = user_id);

create policy "songs insert own"
  on public.songs for insert
  with check (auth.uid() = user_id);

create policy "songs update own"
  on public.songs for update
  using (auth.uid() = user_id);

create policy "instrumentals public read"
  on public.instrumentals for select
  using (is_active = true);

create policy "payments select own"
  on public.payments for select
  using (auth.uid() = user_id);

insert into public.instrumentals (slug, title, genre, bpm, key, storage_path, preview_path)
values
  ('pop-night', 'Gece Pop', 'pop', 102, 'A minor', 'pop-night.wav', 'pop-night.wav'),
  ('trap-pulse', 'Trap Pulse', 'trap', 140, 'F minor', 'trap-pulse.wav', 'trap-pulse.wav'),
  ('rock-drive', 'Rock Drive', 'rock', 118, 'E minor', 'rock-drive.wav', 'rock-drive.wav'),
  ('lofi-dusk', 'Lo-Fi Dusk', 'lofi', 84, 'C major', 'lofi-dusk.wav', 'lofi-dusk.wav');

alter publication supabase_realtime add table public.songs;

grant execute on function public.consume_credits(uuid, integer) to service_role;
grant execute on function public.add_credits(uuid, integer) to service_role;
grant execute on function public.credits_for_duration(numeric) to anon, authenticated, service_role;
