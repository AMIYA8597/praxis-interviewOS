insert into storage.buckets (id, name, public, file_size_limit)
values 
  ('documents', 'documents', false, 5242880)
on conflict (id) do nothing;
