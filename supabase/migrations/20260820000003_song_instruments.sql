alter table public.songs
  add column if not exists instruments text;
