alter table applications
  add column if not exists company text,
  add column if not exists role text,
  add column if not exists source text,
  add column if not exists recruiter text,
  add column if not exists interview_round text,
  add column if not exists next_action text,
  add column if not exists notes text;
