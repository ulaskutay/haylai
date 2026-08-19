insert into public.instrumentals (slug, title, genre, bpm, key, storage_path, preview_path)
values
  ('slow-ember', 'Gece Slow', 'slow', 68, 'D minor', 'slow-ember.wav', 'slow-ember.wav')
on conflict (slug) do nothing;
